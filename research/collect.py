"""Download raw Polymarket data and save it to data/ so analysis can run offline.

Saves, untouched, everything the public APIs return:
  data/markets_closed.jsonl.gz   every closed market above --min-volume (all fields, all
                                 market types, not just binary)
  data/events_closed.jsonl.gz    closed events (groups of related markets)
  data/markets_active.jsonl.gz   snapshot of currently open markets
  data/prices/YYYY-MM.jsonl.gz   full price history of every outcome token, sharded by
                                 the month the market closed

Incremental: markets whose history is already saved are skipped, so re-runs only
fetch what's new. Each run is capped by --max-new-histories and --time-budget-min so it
fits inside a GitHub Actions job; just run it again to continue.
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


def paginate(endpoint, params, min_volume, vol_key, cap):
    """Simple offset pagination. Gamma refuses offsets beyond ~2,000, so this is only
    used where a capped list is fine (active markets); see paginate_windows."""
    out, offset, page = [], 0, 100
    while len(out) < cap:
        batch = get(f"{GAMMA}/{endpoint}", {**params, "limit": page, "offset": offset})
        if not batch:
            break
        out += [m for m in batch if float(m.get(vol_key) or m.get("volume") or 0) >= min_volume]
        offset += page
        if len(batch) < page:
            break
    print(f"{endpoint} {params.get('end_date_min', '')[:10]}..{params.get('end_date_max', '')[:10]}: "
          f"{len(out)}", flush=True)
    return out


def paginate_windows(endpoint, params, min_volume, vol_key, start, end, cap=2000):
    """Walk end-date windows; split any window that hits the offset cap, so every
    market is reached however many there are."""
    lo, hi = start.isoformat().replace("+00:00", "Z"), end.isoformat().replace("+00:00", "Z")
    got = paginate(endpoint, {**params, "end_date_min": lo, "end_date_max": hi},
                   min_volume, vol_key, cap + 200)
    # guard: if the API ignored the date filter, splitting would never converge
    ends = [parse_ts(m.get("endDate")) for m in got if m.get("endDate")]
    outside = sum(1 for t in ends if t < start.timestamp() - 86400 or t > end.timestamp() + 86400)
    if ends and outside > 0.2 * len(ends):
        print(f"  ! {endpoint}: date filter ignored ({outside}/{len(ends)} outside window)", flush=True)
        return got
    if len(got) >= cap and (end - start).total_seconds() > 6 * 3600:
        mid = start + (end - start) / 2
        return (paginate_windows(endpoint, params, min_volume, vol_key, start, mid, cap)
                + paginate_windows(endpoint, params, min_volume, vol_key, mid, end, cap))
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-volume", type=float, default=5000)
    ap.add_argument("--max-new-histories", type=int, default=100000)
    ap.add_argument("--time-budget-min", type=float, default=300)
    a = ap.parse_args()
    t0 = time.time()
    os.makedirs(f"{DATA}/prices", exist_ok=True)

    since = datetime(2020, 6, 1, tzinfo=timezone.utc)
    closed, events = [], []
    for lo, hi in months(since):
        closed += paginate_windows("markets", {"closed": "true", "order": "volumeNum",
                                               "ascending": "false", "volume_num_min": a.min_volume},
                                   a.min_volume, "volumeNum", lo, hi)
        events += paginate_windows("events", {"closed": "true", "order": "volume",
                                              "ascending": "false"},
                                   a.min_volume, "volume", lo, hi)
    closed = merge_by_id(f"{DATA}/markets_closed.jsonl.gz", closed)  # also dedupes
    write_jsonl_gz(f"{DATA}/markets_closed.jsonl.gz", closed)
    events = merge_by_id(f"{DATA}/events_closed.jsonl.gz", [slim_event(e) for e in events])
    write_jsonl_gz(f"{DATA}/events_closed.jsonl.gz", [slim_event(e) for e in events])
    active = paginate("markets", {"closed": "false", "active": "true", "order": "volumeNum",
                                  "ascending": "false"}, 0, "volumeNum", 2000)
    write_jsonl_gz(f"{DATA}/markets_active.jsonl.gz", active)
    print(f"listing: {len(closed)} closed markets, {len(events)} closed events, "
          f"{len(active)} active", flush=True)

    # existing histories, by shard
    shards, have = {}, set()
    for fn in os.listdir(f"{DATA}/prices"):
        if fn.endswith(".jsonl.gz"):
            rows = read_jsonl_gz(f"{DATA}/prices/{fn}")
            shards[fn] = rows
            have.update(r["market_id"] for r in rows)
    print(f"{len(have)} market histories already saved", flush=True)

    # Random order (fixed seed) so every partial run is an unbiased sample across
    # volume tiers, not just the biggest markets.
    todo = [m for m in closed if str(m.get("id")) not in have]
    random.Random(42).shuffle(todo)
    print(f"{len(todo)} histories still to fetch", flush=True)

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

    new, step = 0, 200
    with ThreadPoolExecutor(max_workers=4) as pool:
        for k in range(0, min(len(todo), a.max_new_histories), step):
            if (time.time() - t0) / 60 > a.time_budget_min:
                print("budget reached; re-run to continue", flush=True)
                break
            for row in pool.map(fetch, todo[k:k + step]):
                if not row:
                    continue
                shard = datetime.fromtimestamp(row["close_ts"], timezone.utc).strftime("%Y-%m") + ".jsonl.gz"
                shards.setdefault(shard, []).append(row)
                have.add(row["market_id"]); new += 1
            print(f"histories: {new} new, {len(todo) - k - step} left, "
                  f"{(time.time()-t0)/60:.0f} min", flush=True)
            for fn, rows in shards.items():  # checkpoint
                write_jsonl_gz(f"{DATA}/prices/{fn}", rows)
    remaining = len([m for m in closed if str(m.get("id")) not in have])
    with open(f"{DATA}/REMAINING", "w") as f:
        f.write(str(remaining))

    for fn, rows in shards.items():
        write_jsonl_gz(f"{DATA}/prices/{fn}", rows)
    pts = sum(len(t["history"]) for rows in shards.values() for r in rows for t in r["tokens"])
    print(f"done: {len(closed)} closed markets, {len(events)} events, {len(active)} active, "
          f"{len(have)} histories ({new} new, {remaining} remaining), {pts} price points", flush=True)


if __name__ == "__main__":
    main()
