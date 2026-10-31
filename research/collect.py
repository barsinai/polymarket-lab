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
from datetime import datetime, timezone

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
    out, offset, page = [], 0, 100
    while len(out) < cap:
        batch = get(f"{GAMMA}/{endpoint}", {**params, "limit": page, "offset": offset})
        if not batch:
            break
        below = 0
        for m in batch:
            vol = float(m.get(vol_key) or m.get("volume") or 0)
            if vol >= min_volume:
                out.append(m)
            else:
                below += 1
        print(f"{endpoint}: offset={offset} kept={len(out)}", flush=True)
        offset += page
        # sorted by volume desc: once a whole page is below threshold we're done
        if len(batch) < page or below == len(batch):
            break
    return out



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
    ap.add_argument("--max-markets", type=int, default=20000)
    ap.add_argument("--max-new-histories", type=int, default=6000)
    ap.add_argument("--time-budget-min", type=float, default=150)
    a = ap.parse_args()
    t0 = time.time()
    os.makedirs(f"{DATA}/prices", exist_ok=True)

    closed = paginate("markets", {"closed": "true", "order": "volumeNum", "ascending": "false"},
                      a.min_volume, "volumeNum", a.max_markets)
    write_jsonl_gz(f"{DATA}/markets_closed.jsonl.gz", closed)
    events = paginate("events", {"closed": "true", "order": "volume", "ascending": "false"},
                      a.min_volume, "volume", a.max_markets)
    write_jsonl_gz(f"{DATA}/events_closed.jsonl.gz", events)
    active = paginate("markets", {"closed": "false", "active": "true", "order": "volumeNum",
                                  "ascending": "false"}, 0, "volumeNum", a.max_markets)
    write_jsonl_gz(f"{DATA}/markets_active.jsonl.gz", active)

    # existing histories, by shard
    shards, have = {}, set()
    for fn in os.listdir(f"{DATA}/prices"):
        if fn.endswith(".jsonl.gz"):
            rows = read_jsonl_gz(f"{DATA}/prices/{fn}")
            shards[fn] = rows
            have.update(r["market_id"] for r in rows)
    print(f"{len(have)} market histories already saved", flush=True)

    new = 0
    for i, m in enumerate(closed):
        mid = str(m.get("id"))
        if mid in have:
            continue
        if new >= a.max_new_histories or (time.time() - t0) / 60 > a.time_budget_min:
            print("budget reached; re-run to continue", flush=True)
            break
        close = parse_ts(m.get("closedTime")) or parse_ts(m.get("endDate"))
        start = parse_ts(m.get("startDate")) or parse_ts(m.get("createdAt"))
        tokens = as_list(m.get("clobTokenIds"))
        if not tokens or not close:
            continue
        outcomes = as_list(m.get("outcomes"))
        row = {"market_id": mid, "close_ts": close, "tokens": []}
        for j, tok in enumerate(tokens):
            row["tokens"].append({"token": tok, "outcome": outcomes[j] if j < len(outcomes) else None,
                                  "history": history(tok, start, close)})
            time.sleep(0.05)
        shard = datetime.fromtimestamp(close, timezone.utc).strftime("%Y-%m") + ".jsonl.gz"
        shards.setdefault(shard, []).append(row)
        have.add(mid); new += 1
        if new % 100 == 0:
            print(f"histories: {new} new ({i}/{len(closed)} scanned, "
                  f"{(time.time()-t0)/60:.0f} min)", flush=True)
            for fn, rows in shards.items():  # checkpoint
                write_jsonl_gz(f"{DATA}/prices/{fn}", rows)

    for fn, rows in shards.items():
        write_jsonl_gz(f"{DATA}/prices/{fn}", rows)
    pts = sum(len(t["history"]) for rows in shards.values() for r in rows for t in r["tokens"])
    print(f"done: {len(closed)} closed markets, {len(events)} events, {len(active)} active, "
          f"{len(have)} histories ({new} new), {pts} price points", flush=True)


if __name__ == "__main__":
    main()
