"""Replay the paper-trading strategies over every recorded live hour (real order books),
then look up which markets have resolved and score them. Gives real-price evidence now
instead of waiting for new bets. Needs Gamma access (runs in GitHub Actions).

Each hour's books only keep sell offers within 5c of the best, so a $10 fill that needs more
depth is skipped (conservative). Same v2 rules as live paper trading.
Output: data/replay/<day>/<HHMM>.jsonl.gz (signals), data/replay/resolutions.jsonl.gz,
results/replay.json (scoreboard, also broken down by market type and size).
"""
import glob, gzip, json, os, sys
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import collect, paper  # noqa: E402
from costs import kind, tier  # noqa: E402

OUT = "data/replay"
meta = {}
for f in sorted(glob.glob("data/live/meta/*.jsonl.gz")):
    for m in collect.read_jsonl_gz(f):
        meta[m["id"]] = m
done = {os.path.basename(os.path.dirname(f)) + "/" + os.path.basename(f) for f in glob.glob(f"{OUT}/20*/*.jsonl.gz")}
for f in sorted(glob.glob("data/live/20*/*.json.gz")):
    key = os.path.basename(os.path.dirname(f)) + "/" + os.path.basename(f).replace(".json.gz", ".jsonl.gz")
    if key in done:
        continue
    d = json.load(gzip.open(f))
    if "market_columns" not in d:
        continue
    cols = d["market_columns"]
    mk, raw = [], {}
    for mid, r in d["markets"].items():
        if mid not in meta:
            continue
        m = {**meta[mid], **dict(zip(cols, r))}
        mk.append(m)
        for j, t in enumerate(collect.as_list(m.get("clobTokenIds"))):
            b = d["books"].get(f"{mid}:{j}")
            if b:
                raw[str(t)] = {"asks": [{"price": p, "size": s} for p, s in b[3]]}
    n = paper.run(mk, raw, d["ts"], out_dir=OUT)
    print(f"{f}: {len(mk)} markets, {n} signals", flush=True)

resolved, signalled = paper.score(OUT)
print(f"resolved {resolved}/{signalled} signalled markets", flush=True)

# scoreboard with breakdowns
res = {r["id"]: r for r in collect.read_jsonl_gz(f"{OUT}/resolutions.jsonl.gz")}
first = {}
for f in sorted(glob.glob(f"{OUT}/20*/*.jsonl.gz")):
    for r in collect.read_jsonl_gz(f):
        first.setdefault((r["strategy"], r["market_id"]), r)
agg = defaultdict(lambda: {"bets": 0, "stake": 0.0, "pnl": 0.0, "wins": 0})
bets = []
for (strat, mid), r in first.items():
    z = res.get(mid)
    if not z or not z.get("resolved"):
        continue
    won = z["winner"] == r["side"]
    pnl = r["filled_usd"] * ((1 / r["avg_fill"] - 1) if won else -1)
    bets.append({**r, "won": won, "pnl": pnl})
    for key in (strat, f"{strat} | {kind((r['question'] or '').lower())}", f"{strat} | {tier(r['volume'])}"):
        a = agg[key]
        a["bets"] += 1; a["stake"] += r["filled_usd"]; a["pnl"] += pnl; a["wins"] += won
for a in agg.values():
    a["profit_per_$"] = round(a["pnl"] / a["stake"], 4)
out = {"hours_replayed": len({os.path.dirname(f) + os.path.basename(f) for f in glob.glob(f"{OUT}/20*/*.jsonl.gz")}),
       "resolved_markets": resolved, "signalled_markets": signalled, "scoreboard": dict(sorted(agg.items()))}
os.makedirs("results", exist_ok=True)
json.dump(out, open("results/replay.json", "w"), indent=1)
collect.write_jsonl_gz(f"{OUT}/scored_bets.jsonl.gz", bets)
print(json.dumps(out["scoreboard"], indent=1))
