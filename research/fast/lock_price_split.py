"""Cycle 11 read-out: where does lock_p / lock_x P&L come from? Split settled paper trades by entry price (< 0.80 vs >= 0.80)
and by whether the $20 order was filled in full (book depth) - first signal per window for the all-lock_* view."""
import json, collections
T = [json.loads(l) for l in open("data/fast/trades.jsonl")]
T = [t for t in T if t.get("result") is not None and str(t.get("strat", "")).startswith("lock")]
def summ(v):
    c = sum(t["price"] * t["shares"] + t.get("fee", 0) for t in v)
    return {"n": len(v), "won": sum(t["result"] for t in v), "pnl": round(sum(t["pnl"] for t in v), 2),
            "ret_per_usd": round(sum(t["pnl"] for t in v) / c, 4) if c else None, "end_times": len({t["end"] for t in v})}
out = {}
for s in ("lock_p", "lock_x", "lock_p_majors"):
    v = [t for t in T if t["strat"] == s]
    out[s] = {"price<0.80": summ([t for t in v if t["price"] < 0.8]), "price>=0.80": summ([t for t in v if t["price"] >= 0.8])}
first = {}
for t in T:
    if t["slug"] not in first or t["ts"] < first[t["slug"]]["ts"]:
        first[t["slug"]] = t
cap = collections.defaultdict(float)
for t in T:
    cap[t["strat"]] = max(cap[t["strat"]], t["price"] * t["shares"])
V = list(first.values())
out["all_first_signal"] = {"full_size": summ([t for t in V if t["price"] * t["shares"] >= 0.95 * cap[t["strat"]]]),
                           "size_capped_by_book": summ([t for t in V if t["price"] * t["shares"] < 0.95 * cap[t["strat"]]])}
for lo, hi in ((0, .8), (.8, .9), (.9, .95), (.95, 1.01)):
    out["all_first_signal"][f"price {lo}-{hi}"] = summ([t for t in V if lo <= t["price"] < hi])
FWD = 1794646800  # N25 forward read-out starts 11-14 09:00 UTC (the split was chosen after looking)
fw = [t for t in V if t["ts"] >= FWD]
out["N25_forward"] = {"price<0.80": summ([t for t in fw if t["price"] < 0.8]), "price>=0.80": summ([t for t in fw if t["price"] >= 0.8])}
print(json.dumps(out, indent=1))
