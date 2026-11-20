"""Cycle 46, N100 (outside the box): forced exits. Who is forced to trade? A taker who bought one way and later trades the OTHER way in
the same market is mostly exiting (tape direction -1 = buy NO or SELL YES). Exits are driven by the trader's own book (stop-loss, capital
needed elsewhere, profit-taking, end-of-day risk) more than by news, so the flip leg could be uninformed -> fade it; or a reversal by a
taker who was in the market is the strongest signal on the tape -> follow it. Never tested: every earlier tape study used FIRST entries.
Rules fixed BEFORE looking (written here first):
Tapes a (ex-mention), b (weather), c; finished markets (end < tape time). Flip = a wallet's entry in direction D2 whose first trade t2 is
after its first trade the other way t1 in the same market, t2 - t1 <= 7 d, t2 >= 1 h before the end, wallet's cost in the first leg >= $20.
Follower buys D2 at a300 (next print the same way by someone else >= 300 s later), 0.05-0.95, fee rate * p(1-p). One row per market and
direction (the first flip). Unit = event, bootstrap 1,000, halves by end date; also by group and by flip size (D2 cost >= $200).
DECISION (fixed): FOLLOW arm if D2 >= +3 pts, CI low > 0, >= 100 events, both halves >= +2. FADE worth a book replay only if D2 <= -4 pts,
CI high < 0, >= 100 events, both halves <= -2 (the opposite side's real ask is not in the tape: spread eats ~2-5 pts). Else DEAD.
Placebo: the same wallets' FIRST-leg entries (D1) at a300 on the same markets. Exposed to 22, 24, 23 (unit), 17, 5/6."""
import json, gzip, struct, collections, random, datetime as dt
ROW = struct.Struct("<IIIhfffHHHIB")
B = "data/research/"
random.seed(100)
R, P = [], []
for g in "abc":
    meta = json.load(gzip.open(f"{B}entries_{g}_meta.json.gz")); MK = meta["markets"]
    at = dt.datetime.strptime(meta["at"], "%Y-%m-%d %H:%M").replace(tzinfo=dt.timezone.utc).timestamp()
    blob = gzip.open(f"{B}entries_{g}.bin.gz").read()
    legs = collections.defaultdict(dict)          # (mi, wi) -> {dir: (t, C, a300, fl)}
    for t, mi, wi, hb, S, C, F, a, a60, a300, lag, fl in ROW.iter_unpack(blob):
        m = MK[mi]
        if m[4] >= at or m[2] == "mention" or S <= 0 or C <= 0: continue
        d = fl & 1
        o = legs[(mi, wi)].get(d)
        if o is None or t < o[0]: legs[(mi, wi)][d] = (t, C, a300, fl)
    del blob
    flip, first = {}, {}
    for (mi, wi), L in legs.items():
        if len(L) < 2: continue
        (d1, l1), (d2, l2) = sorted(L.items(), key=lambda x: x[1][0])
        m = MK[mi]
        if l1[1] < 20 or l2[0] - l1[0] > 7 * 86400 or m[4] - l2[0] < 3600: continue
        for store, l, d, big in ((flip, l2, d2, l2[1] >= 200), (first, l1, d1, l1[1] >= 200)):
            p = l[2] / 1e4
            if not 0.05 <= p <= 0.95: continue
            k = (mi, d)
            if k in store and store[k]["t"] <= l[0]: continue
            store[k] = dict(t=l[0], e=f"{g}:{m[1]}", g=g, end=m[4], p=p, big=big, gap=(l2[0] - l1[0]) / 3600,
                            f=(1 if l[3] & 2 else 0) - p - m[7] * p * (1 - p))
    R += flip.values(); P += first.values()
    del legs
def stat(rr):
    ev = collections.defaultdict(lambda: [0.0, 0])
    for r in rr: ev[r["e"]][0] += r["f"]; ev[r["e"]][1] += 1
    v = list(ev.values()); n = sum(y[1] for y in v)
    if not n: return {"n": 0, "events": 0}
    o = {"n": n, "events": len(v), "pts": round(100 * sum(y[0] for y in v) / n, 2), "avg_p": round(sum(r["p"] for r in rr) / n, 3)}
    if len(v) >= 5:
        bs = sorted(sum(y[0] for y in s) / max(1, sum(y[1] for y in s)) for s in ([v[int(random.random() * len(v))] for _ in v] for _ in range(1000)))
        o["ci"] = [round(100 * bs[25], 1), round(100 * bs[974], 1)]
    return o
mid = sorted(r["end"] for r in R)[len(R) // 2]
half = lambda rr: {"older": stat([r for r in rr if r["end"] < mid]).get("pts"), "newer": stat([r for r in rr if r["end"] >= mid]).get("pts")}
out = {"split_at": str(dt.datetime.fromtimestamp(mid, dt.timezone.utc)), "flip D2": {**stat(R), **half(R)},
       "placebo first leg D1": {**stat(P), **half(P)}}
for g in "abc": out[f"D2 group {g}"] = {**stat([r for r in R if r["g"] == g]), **half([r for r in R if r["g"] == g])}
out["D2 big (>= $200)"] = {**stat([r for r in R if r["big"]]), **half([r for r in R if r["big"]])}
out["D2 gap < 1 h"] = stat([r for r in R if r["gap"] < 1]); out["D2 gap >= 24 h"] = stat([r for r in R if r["gap"] >= 24])
s = out["flip D2"]; ci = s.get("ci", [0, 0]); hs = (s["older"] or 0, s["newer"] or 0)
if s["pts"] >= 3 and ci[0] > 0 and s["events"] >= 100 and min(hs) >= 2: v = "FOLLOW -> paper arm"
elif s["pts"] <= -4 and ci[1] < 0 and s["events"] >= 100 and max(hs) <= -2: v = "FADE -> book replay of the opposite ask"
else: v = "DEAD (fails the fixed rule)"
out["verdict"] = v
print(json.dumps(out, indent=1)); json.dump(out, open(f"{B}flip_leg_report.json", "w"), indent=1)
