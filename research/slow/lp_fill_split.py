"""N33 read-out: LP-1 v2 trade fills split by UTC slot and by market type.
Markout of each fill against the market's latest fair (data/slow/lp_paper_state.json): buy -> (fair_last - price) * size,
sell -> (price - fair_last) * size. Weather = same-day temperature buckets. Read-only, paper data."""
import json, collections, datetime as dt, sys
S = json.load(open(sys.argv[1] if len(sys.argv) > 1 else "data/slow/lp_paper_state.json"))
ms = S["markets"]
def slot(ts):
    t = dt.datetime.fromtimestamp(ts, dt.timezone.utc)
    if t.weekday() >= 5: return "weekend"
    return "wkday 04-12" if 4 <= t.hour < 12 else "wkday 12-04"
agg = collections.defaultdict(lambda: [0, 0.0, 0.0, set()])
for mid, x in ms.items():
    f_last = x.get("fair")
    if f_last is None: continue
    kind = "weather" if "temperature" in x["q"].lower() else "other"
    for ts, side, p, sz, fair_then in x["fills"]:
        mk = (f_last - p) * sz if side == "buy" else (p - f_last) * sz
        h = dt.datetime.fromtimestamp(ts, dt.timezone.utc).hour
        for key in (("slot", slot(ts)), ("kind", kind), ("hour6", f"{h//6*6:02d}-{h//6*6+6:02d}"), ("all", "all")):
            a = agg[key]; a[0] += 1; a[1] += mk; a[2] += p * sz; a[3].add(mid)
out = {f"{k[0]}:{k[1]}": {"fills": a[0], "markets": len(a[3]), "markout_usd": round(a[1], 2),
       "markout_pct_notional": round(100 * a[1] / a[2], 1) if a[2] else None} for k, a in sorted(agg.items())}
first = min((f[0] for x in ms.values() for f in x["fills"]), default=None)
last = max((f[0] for x in ms.values() for f in x["fills"]), default=None)
out["span_utc"] = [str(dt.datetime.fromtimestamp(t, dt.timezone.utc))[:16] if t else None for t in (first, last)]
print(json.dumps(out, indent=1))
