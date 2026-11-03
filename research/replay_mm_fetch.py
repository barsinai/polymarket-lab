"""Fetch all taker trades since the live recording began for every market that has (or had) a
reward pool, so market-making rules can be replayed offline against real books + real trades.
Data API v2, cursor pages, newest first; stops at START_TS. Incremental: keeps what it has and
fetches only newer trades per market. Output: data/replay_mm/trades/<cid>.json.gz
  [[ts, side(1=BUY), outcome_index, price, size], ...] sorted by time.
"""
import glob, gzip, json, os, sys, time
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import collect  # noqa: E402

START_TS = 1793476800  # 2026-10-31 20:00 UTC, first wide live snapshot
OUT = "data/replay_mm/trades"
os.makedirs(OUT, exist_ok=True)
cids = set()
for f in glob.glob("data/live/rewards/*.jsonl.gz"):
    for m in collect.read_jsonl_gz(f):
        r = m.get("rewards") or {}
        if sum(x.get("rewards_daily_rate") or 0 for x in r.get("rates") or []) > 0:
            cids.add(m["condition_id"])
cids = sorted(cids)
budget = time.time() + float(os.environ.get("BUDGET_MIN", "300")) * 60
print(f"{len(cids)} reward markets", flush=True)


def fetch(cid):
    if time.time() > budget:
        return 0
    p = f"{OUT}/{cid}.json.gz"
    old = json.load(gzip.open(p, "rt")) if os.path.exists(p) else []
    since = max([START_TS] + [t[0] for t in old])
    new = collect.trades_since(cid, since, max_rows=20000)
    rows = sorted({(int(t["timestamp"]), 1 if t["side"] == "BUY" else 0, int(t["outcomeIndex"] or 0), float(t["price"]), float(t["size"]))
                   for t in new} | {tuple(t) for t in old})
    if rows != [tuple(t) for t in old]:
        with gzip.open(p, "wt") as fh:
            json.dump(rows, fh, separators=(",", ":"))
    return len(new)


done = n = 0
with ThreadPoolExecutor(8) as ex:
    for k in ex.map(fetch, cids):
        done += 1; n += k
        if done % 1000 == 0:
            print(f"{done} markets, {n} new trades", flush=True)
print(f"finished: {done} markets, {n} new trades")
