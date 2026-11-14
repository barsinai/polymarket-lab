"""N21 read-out: all lock_* paper signals, first signal per window (slug), split BTC/ETH vs alts, using recorded pnl and fee.
Forward sample starts at FWD (11-14 01:00 UTC, the cycle that proposed it); before that is the in-sample split that suggested it."""
import json, collections, datetime
FWD = 1794618000
first = {}
for l in open("data/fast/trades.jsonl"):
    t = json.loads(l)
    if t.get("result") is None or not str(t.get("strat", "")).startswith("lock"):
        continue
    if t["slug"] not in first or t["ts"] < first[t["slug"]]["ts"]:
        first[t["slug"]] = t
out = {}
for per in ("in_sample", "forward"):
    for g in ("btc_eth", "alts"):
        v = [t for t in first.values() if (t["ts"] >= FWD) == (per == "forward") and (t["asset"] in ("btc", "eth")) == (g == "btc_eth")]
        cost = sum(t["price"] * t["shares"] + t.get("fee", 0) for t in v)
        out[f"{per}_{g}"] = {"windows": len(v), "won": sum(t["result"] for t in v),
                             "ret_per_usd": round(sum(t["pnl"] for t in v) / cost, 4) if cost else None,
                             "days": len({t["end"] // 86400 for t in v})}
print(json.dumps(out, indent=1))
