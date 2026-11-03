"""Hourly price histories for Polymarket soccer moneyline/draw markets (8 leagues, since Aug 2025),
to compare pre-kickoff prices with Pinnacle closing odds (data/external/football/).
Input:  data/external/soccer/markets.jsonl.gz  (built offline from the listing)
Output: data/external/soccer/prices/<div>.jsonl.gz  {id, token, history: [[ts, p], ...]}  (incremental)
"""
import glob, gzip, json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import collect  # noqa: E402

OUT = "data/external/soccer/prices"
os.makedirs(OUT, exist_ok=True)
budget = time.time() + float(os.environ.get("BUDGET_MIN", "300")) * 60
mk = list(collect.read_jsonl_gz("data/external/soccer/markets.jsonl.gz"))
done = {}
for f in glob.glob(f"{OUT}/*.jsonl.gz"):
    for r in collect.read_jsonl_gz(f):
        done[r["id"]] = True
print(f"{len(mk)} markets, {len(done)} already fetched", flush=True)
by_div = {}
for m in mk:
    if m["id"] in done or not m.get("closed"):
        continue
    by_div.setdefault(m["div"], []).append(m)
for div, ms in by_div.items():
    rows = []
    for m in ms:
        if time.time() > budget:
            break
        gst = collect.parse_ts(m["gameStartTime"])
        st = collect.parse_ts(m.get("startDate")) or (gst - 14 * 86400)
        h = collect.history(m["token"], st, gst + 4 * 3600)
        rows.append({"id": m["id"], "token": m["token"], "history": h})
        if len(rows) % 200 == 0:
            print(div, len(rows), flush=True)
    if rows:
        p = f"{OUT}/{div}.jsonl.gz"
        old = list(collect.read_jsonl_gz(p)) if os.path.exists(p) else []
        collect.write_jsonl_gz(p, old + rows)
        print(f"{div}: +{len(rows)} (total {len(old) + len(rows)})", flush=True)
print("finished")
