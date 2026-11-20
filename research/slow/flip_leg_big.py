"""Cycle 46, N100 follow-up, POST-HOC (defined after flip_leg.py printed 'D2 big (>= $200) +4.0 [2.7, 5.3]'): can only kill or point to a
forward paper arm. Checks: by group, by price band, big flips vs (i) the same wallets' big FIRST legs, (ii) all big first entries of any
wallet that never flipped in that market (lesson 17 base rate +1.2), with the identical unit and fill."""
import json, gzip, struct, collections, random, datetime as dt
src = open("research/slow/flip_leg.py").read()
exec(src.split("R, P = [], []")[0])
exec("def stat" + src.split("def stat")[1].split("mid =")[0])
R, P, C = [], [], []
for g in "abc":
    meta = json.load(gzip.open(f"{B}entries_{g}_meta.json.gz")); MK = meta["markets"]
    at = dt.datetime.strptime(meta["at"], "%Y-%m-%d %H:%M").replace(tzinfo=dt.timezone.utc).timestamp()
    blob = gzip.open(f"{B}entries_{g}.bin.gz").read()
    legs = collections.defaultdict(dict)
    for t, mi, wi, hb, S, Cc, F, a, a60, a300, lag, fl in ROW.iter_unpack(blob):
        m = MK[mi]
        if m[4] >= at or m[2] == "mention" or S <= 0 or Cc <= 0: continue
        d = fl & 1; o = legs[(mi, wi)].get(d)
        if o is None or t < o[0]: legs[(mi, wi)][d] = (t, Cc, a300, fl)
    del blob
    st = {"flip": {}, "d1": {}, "ctrl": {}}
    for (mi, wi), L in legs.items():
        m = MK[mi]
        if len(L) == 1:
            (d, l), = L.items()
            if l[1] >= 200 and m[4] - l[0] >= 3600: cand = [("ctrl", l, d)]
            else: continue
        else:
            (d1, l1), (d2, l2) = sorted(L.items(), key=lambda x: x[1][0])
            if l1[1] < 20 or l2[0] - l1[0] > 7 * 86400 or m[4] - l2[0] < 3600: continue
            cand = [(n, l, d) for n, l, d in (("flip", l2, d2), ("d1", l1, d1)) if l[1] >= 200]
        for n, l, d in cand:
            p = l[2] / 1e4
            if not 0.05 <= p <= 0.95: continue
            k = (mi, d); s = st[n]
            if k in s and s[k]["t"] <= l[0]: continue
            s[k] = dict(t=l[0], e=f"{g}:{m[1]}", g=g, end=m[4], p=p, f=(1 if l[3] & 2 else 0) - p - m[7] * p * (1 - p))
    R += st["flip"].values(); P += st["d1"].values(); C += st["ctrl"].values(); del legs
mid = sorted(r["end"] for r in R)[len(R) // 2]
half = lambda rr: {"older": stat([r for r in rr if r["end"] < mid]).get("pts"), "newer": stat([r for r in rr if r["end"] >= mid]).get("pts")}
out = {}
for name, rr in (("big flip", R), ("big first leg, same wallets", P), ("big first entry, never flipped", C)):
    out[name] = {**stat(rr), **half(rr)}
    for g in "abc": out[f"{name} | {g}"] = stat([r for r in rr if r["g"] == g])
    for lo, hi in ((0.05, 0.4), (0.4, 0.7), (0.7, 0.95)): out[f"{name} | p {lo}-{hi}"] = stat([r for r in rr if lo <= r["p"] < hi])
print(json.dumps(out, indent=1)); json.dump(out, open(f"{B}flip_leg_big_report.json", "w"), indent=1)
