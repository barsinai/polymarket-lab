"""Cycle 45, N97 follow-up (lesson 10, defined AFTER the fixed rule came back underpowered: box office / views events carry ONE
'at least' market each - the open top bracket next to 'between' brackets - so the >= 3-rung rule saw none of them). Same entry rules as
fan_ladder.py: single-threshold markets, NO and YES, by kind, halves. Post-hoc -> can only kill or point to a forward paper, never pass."""
import json, gzip, collections, random, datetime as dt
src = open("research/slow/fan_ladder.py").read()
exec(src.split("q = {}")[0])
single = {mi for mi, v in thr.items() if len(set(lad[MK[mi][1]])) == 1}
blob = gzip.open(f"{B}entries_a.bin.gz").read()
first = {}
for t, mi, wi, hb, S, C, F, a, a60, a300, lag, fl in ROW.iter_unpack(blob):
    if mi not in single or S <= 0 or C <= 0: continue
    p = a300 / 1e4
    if not 0.05 <= p <= 0.95: continue
    side = "YES" if fl & 1 else "NO"; m = MK[mi]; k = (mi, side)
    if k in first and first[k]["t"] <= t: continue
    first[k] = dict(t=t, e=m[1], side=side, end=m[4], p=p, h=(m[4] - t) / 3600, kind=kind(m[3]), f=(1 if fl & 2 else 0) - p - m[7] * p * (1 - p))
del blob
R = list(first.values())
exec("def stat" + src.split("def stat")[1].split("mid =")[0])
mid = sorted(r["end"] for r in R)[len(R) // 2]
half = lambda rr: {"older": stat([r for r in rr if r["end"] < mid]).get("pts"), "newer": stat([r for r in rr if r["end"] >= mid]).get("pts")}
out = {"single_markets": len(single), "rows": len(R), "split_at": str(dt.datetime.fromtimestamp(mid, dt.timezone.utc))}
for side in ["NO", "YES"]:
    for kd in [None, "box office", "views", "netflix", "other"]:
        rr = [r for r in R if r["side"] == side and (kd is None or r["kind"] == kd)]
        out[f"{side} {kd or 'all'}"] = {**stat(rr), **half(rr)}
print(json.dumps(out, indent=1)); json.dump(out, open(f"{B}fan_ladder_single_report.json", "w"), indent=1)
