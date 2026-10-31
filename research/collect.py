"""Download raw Polymarket data and save it to data/ so analysis can run offline.

Saves, untouched, everything the public APIs return:
  data/markets_closed.jsonl.gz   every closed market above --min-volume (all fields, all
                                 market types, not just binary)
  data/events_closed.jsonl.gz    closed events (groups of related markets)
  data/markets_active.jsonl.gz   snapshot of currently open markets
  data/prices/**.jsonl.gz        full price history of every outcome token. New histories
                                 go to new part files (parts/<run>-<n>.jsonl.gz); saved files
                                 are never rewritten, which keeps memory and git history small.

Incremental and crash-safe: markets already saved are skipped; with --git-checkpoint the
run commits and pushes its progress every 30 minutes, so a killed job loses at most that.
"""

import argparse
import gzip
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import random
import resource
import subprocess

import requests

GAMMA = "https://gamma-api.polymarket.com"
CLOB = "https://clob.polymarket.com"
DATA = "data"

ERRS = {"n": 0}
S = requests.Session()
S.headers["User-Agent"] = "polymarket-lab-research/0.2"


def get(url, params=None, tries=5):
    for i in range(tries):
        try:
            r = S.get(url, params=params, timeout=30)
            if r.status_code == 429 or r.status_code >= 500:
                time.sleep(2 ** i)
                continue
            if r.status_code >= 400:
                ERRS["n"] = ERRS.get("n", 0) + 1
                if ERRS["n"] <= 20:
                    print(f"  ! {r.status_code} {params}: {r.text[:200]}", flush=True)
                return None
            return r.json()
        except Exception as e:  # noqa: BLE001
            print(f"  ! {url} {params}: {e}", file=sys.stderr)
            time.sleep(1 + i)
    return None


def as_list(v):
    if isinstance(v, list):
        return v
    if isinstance(v, str):
        try:
            return json.loads(v)
        except json.JSONDecodeError:
            return []
    return []


def parse_ts(s):
    if not s:
        return None
    try:
        return int(datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp())
    except ValueError:
        return None


def write_jsonl_gz(path, rows):
    tmp = path + ".tmp"
    with gzip.open(tmp, "wt") as f:
        for r in rows:
            f.write(json.dumps(r, separators=(",", ":")) + "\n")
    os.replace(tmp, path)


def read_jsonl_gz(path):
    if not os.path.exists(path):
        return []
    with gzip.open(path, "rt") as f:
        return [json.loads(line) for line in f if line.strip()]


def paginate(endpoint, params, min_volume, vol_key, cap, fn=None):
    """Simple offset pagination. Gamma refuses offsets beyond ~2,000, so this is only
    used where a capped list is fine (active markets); see paginate_windows."""
    out, offset, page = [], 0, 100
    while len(out) < cap:
        batch = get(f"{GAMMA}/{endpoint}", {**params, "limit": page, "offset": offset})
        if not batch:
            break
        out += [fn(m) if fn else m for m in batch
                if float(m.get(vol_key) or m.get("volume") or 0) >= min_volume]
        offset += page
        if len(batch) < page:
            break
    print(f"{endpoint} {params.get('end_date_min', '')[:10]}..{params.get('end_date_max', '')[:10]}: "
          f"{len(out)}", flush=True)
    return out


def paginate_windows(endpoint, params, min_volume, vol_key, start, end, cap=2000, fn=None):
    """Walk end-date windows; split any window that hits the offset cap, so every
    market is reached however many there are."""
    lo, hi = start.isoformat().replace("+00:00", "Z"), end.isoformat().replace("+00:00", "Z")
    got = paginate(endpoint, {**params, "end_date_min": lo, "end_date_max": hi},
                   min_volume, vol_key, cap + 200, fn)
    # guard: if the API ignored the date filter, splitting would never converge
    ends = [parse_ts(m.get("endDate")) for m in got if m.get("endDate")]
    outside = sum(1 for t in ends if t < start.timestamp() - 86400 or t > end.timestamp() + 86400)
    if ends and outside > 0.2 * len(ends):
        print(f"  ! {endpoint}: date filter ignored ({outside}/{len(ends)} outside window)", flush=True)
        return got
    if len(got) >= cap and (end - start).total_seconds() > 6 * 3600:
        mid = start + (end - start) / 2
        return (paginate_windows(endpoint, params, min_volume, vol_key, start, mid, cap, fn)
                + paginate_windows(endpoint, params, min_volume, vol_key, mid, end, cap, fn))
    return got


def months(since):
    t = since
    now = datetime.now(timezone.utc)
    while t < now:
        n = (t.replace(day=1) + timedelta(days=32)).replace(day=1)
        yield t, min(n, now + timedelta(days=1))
        t = n


def merge_by_id(path, fresh):
    """Never lose records because one run's listing came back short."""
    old = {str(r.get("id")): r for r in read_jsonl_gz(path)}
    old.update({str(r.get("id")): r for r in fresh})
    return list(old.values())


def slim_event(e):
    e = dict(e)
    e["markets"] = [{k: m.get(k) for k in ("id", "conditionId", "question", "groupItemTitle",
                                           "negRisk", "outcomePrices", "volumeNum")}
                    for m in e.get("markets") or []]
    return e


def history(token, start_ts, end_ts):
    """Full price history. The API rejects long windows for resolved markets, so we
    try interval=max first, then walk the market's lifetime in the largest window
    size the API accepts (14d, 7d, 3d, 1d)."""
    data = get(f"{CLOB}/prices-history", {"market": token, "interval": "max", "fidelity": 60})
    hist = (data or {}).get("history") or []
    if len(hist) < 5 and start_ts and end_ts:
        start_ts = max(start_ts, end_ts - 400 * 86400)
        for days in (14, 7, 3, 1):
            w, hist, t, ok = days * 86400, [], start_ts, True
            while t < end_ts:
                d = get(f"{CLOB}/prices-history", {"market": token, "startTs": t,
                                                   "endTs": min(t + w, end_ts), "fidelity": 60})
                if d is None:
                    ok = False
                    break
                hist += d.get("history") or []
                t += w
            if ok:
                break
    seen, clean = set(), []
    for h in hist:
        if "t" in h and "p" in h and h["t"] not in seen:
            seen.add(h["t"]); clean.append([int(h["t"]), float(h["p"])])
    return sorted(clean)


def mem_mb():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss // 1024


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')} mem={mem_mb()}MB] {msg}", flush=True)


def git_checkpoint(msg):
    cmds = ["git add data logs", f'git commit -qm "{msg}"',
            "git pull -q --rebase origin main", "git push -q"]
    for c in cmds:
        r = subprocess.run(c, shell=True, capture_output=True, text=True)
        if r.returncode and "commit" not in c:
            log(f"checkpoint step failed: {c}: {r.stderr[-300:]}")
            return
    log(f"checkpoint pushed: {msg}")


def saved_ids():
    have = set()
    for root, _, files in os.walk(f"{DATA}/prices"):
        for fn in files:
            if fn.endswith(".jsonl.gz"):
                with gzip.open(os.path.join(root, fn), "rt") as f:
                    for line in f:
                        # market_id is the first key; avoid parsing the whole history
                        i = line.find('"market_id":"')
                        if i >= 0:
                            have.add(line[i + 13:line.index('"', i + 13)])
    return have


def list_markets(a):
    stamp = f"{DATA}/LISTED_AT"
    if os.path.exists(stamp) and time.time() - float(open(stamp).read() or 0) < 20 * 3600:
        log("listing is fresh (<20h), reusing it")
        return read_jsonl_gz(f"{DATA}/markets_closed.jsonl.gz")
    since = datetime(2020, 6, 1, tzinfo=timezone.utc)
    closed, events = [], []
    for lo, hi in months(since):
        closed += paginate_windows("markets", {"closed": "true", "order": "volumeNum",
                                               "ascending": "false", "volume_num_min": a.min_volume},
                                   a.min_volume, "volumeNum", lo, hi)
        events += paginate_windows("events", {"closed": "true", "order": "volume",
                                              "ascending": "false"},
                                   a.min_volume, "volume", lo, hi, fn=slim_event)
        log(f"listed through {lo:%Y-%m}: {len(closed)} markets, {len(events)} events")
    closed = merge_by_id(f"{DATA}/markets_closed.jsonl.gz", closed)  # also dedupes
    write_jsonl_gz(f"{DATA}/markets_closed.jsonl.gz", closed)
    events = merge_by_id(f"{DATA}/events_closed.jsonl.gz", events)
    write_jsonl_gz(f"{DATA}/events_closed.jsonl.gz", [slim_event(e) for e in events])
    n_events = len(events)
    del events
    active = paginate("markets", {"closed": "false", "active": "true", "order": "volumeNum",
                                  "ascending": "false"}, 0, "volumeNum", 2000)
    write_jsonl_gz(f"{DATA}/markets_active.jsonl.gz", active)
    with open(stamp, "w") as f:
        f.write(str(time.time()))
    log(f"listing: {len(closed)} closed markets, {n_events} closed events, {len(active)} active")
    return closed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-volume", type=float, default=5000)
    ap.add_argument("--max-new-histories", type=int, default=100000)
    ap.add_argument("--time-budget-min", type=float, default=300)
    ap.add_argument("--git-checkpoint", action="store_true")
    a = ap.parse_args()
    t0 = time.time()
    os.makedirs(f"{DATA}/prices/parts", exist_ok=True)
    run = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M")

    closed = list_markets(a)
    if a.git_checkpoint:
        git_checkpoint(f"Market listing {run}")

    have = saved_ids()
    log(f"{len(have)} market histories already saved")
    # keep only what fetching needs, in random order (fixed seed) so every partial run
    # is an unbiased sample across volume tiers, not just the biggest markets
    todo = [{k: m.get(k) for k in ("id", "closedTime", "endDate", "startDate", "createdAt",
                                   "clobTokenIds", "outcomes")}
            for m in closed if str(m.get("id")) not in have]
    total = len(closed)
    del closed
    random.Random(42).shuffle(todo)
    log(f"{len(todo)} histories still to fetch")

    def fetch(m):
        close = parse_ts(m.get("closedTime")) or parse_ts(m.get("endDate"))
        start = parse_ts(m.get("startDate")) or parse_ts(m.get("createdAt"))
        tokens, outcomes = as_list(m.get("clobTokenIds")), as_list(m.get("outcomes"))
        if not tokens or not close:
            return None
        # binary: second token is the mirror of the first, so fetch one (halves the time)
        idx = [0] if len(tokens) == 2 else range(len(tokens))
        row = {"market_id": str(m.get("id")), "close_ts": close, "tokens": []}
        for j in idx:
            row["tokens"].append({"token": tokens[j], "outcome": outcomes[j] if j < len(outcomes) else None,
                                  "history": history(tokens[j], start, close)})
        return row

    new, done_idx, step, last_ckpt = 0, 0, 200, time.time()
    with ThreadPoolExecutor(max_workers=4) as pool:
        for k in range(0, min(len(todo), a.max_new_histories), step):
            if (time.time() - t0) / 60 > a.time_budget_min:
                log("time budget reached; the next run continues")
                break
            rows = [r for r in pool.map(fetch, todo[k:k + step]) if r]
            write_jsonl_gz(f"{DATA}/prices/parts/{run}-{k // step:04d}.jsonl.gz", rows)
            new += len(rows); done_idx = k + step
            log(f"histories: {new} new this run, {max(len(todo) - done_idx, 0)} left")
            del rows
            if a.git_checkpoint and time.time() - last_ckpt > 30 * 60:
                with open(f"{DATA}/REMAINING", "w") as f:
                    f.write(str(max(len(todo) - done_idx, 0)))
                git_checkpoint(f"Price histories checkpoint {run} (+{new})")
                last_ckpt = time.time()
    remaining = max(len(todo) - done_idx, 0)
    with open(f"{DATA}/REMAINING", "w") as f:
        f.write(str(remaining))
    log(f"done: {total} closed markets listed, {new} new histories, {remaining} remaining")


if __name__ == "__main__":
    main()
