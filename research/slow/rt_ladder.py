"""Cycle 44, N95 (adjacent, spawned by N94): Rotten Tomatoes score ladders, NO side, split test.
Rules fixed BEFORE looking (from IDEAS N95): tape group a only (b / c have no RT markets; no older period exists), finished markets whose
question names the Tomatometer. Entry = first taker entry per market and side anywhere in the market's life, follower fill a300 (next print
the same way >= 300 s later), 0.05-0.95, fee = rate * p(1-p). Unit = film (event slug), bootstrap 1,000; halves by end date.
Splits: hours before end at the follower's entry (> 7 d, 1-7 d, < 1 d); threshold rank inside the film's ladder (top rung vs the rest;
also bottom rung); entry price band (< 0.30, 0.30-0.60, > 0.60 for NO).
DECISION (fixed): DEAD if the older half NO <= +3 pts or < 30 films. Otherwise a split survives only if it is >= +5 pts, CI low > 0,
>= 15 films and positive in both halves -> paper arm. Exposed to 24, 13, 26, 5/6, 22."""
import json, gzip, struct, collections, random, re, datetime as dt
ROW = struct.Struct("<IIIhfffHHHIB")
B = "data/research/"
random.seed(95)
meta = json.load(gzip.open(f"{B}entries_a_meta.json.gz")); MK = meta["markets"]
at = dt.datetime.strptime(meta["at"], "%Y-%m-%d %H:%M").replace(tzinfo=dt.timezone.utc).timestamp()
TH = re.compile(r"at least (\d+)", re.I)
sel = {}
for mi, m in enumerate(MK):
    if "tomato" in m[3].lower() and m[4] < at:
        t = TH.search(m[3])
        if t: sel[mi] = int(t[1])
lad = collections.defaultdict(list)
for mi, v in sel.items(): lad[MK[mi][1]].append(v)
blob = gzip.open(f"{B}entries_a.bin.gz").read()
first = {}
for t, mi, wi, hb, S, C, F, a, a60, a300, lag, fl in ROW.iter_unpack(blob):
    if mi not in sel or S <= 0 or C <= 0: continue
    p = a300 / 1e4
    if not 0.05 <= p <= 0.95: continue
    side = "YES" if fl & 1 else "NO"; m = MK[mi]
    k = (mi, side)
    if k in first and first[k]["t"] <= t: continue
    vs = sorted(lad[m[1]]); v = sel[mi]
    first[k] = dict(t=t, e=m[1], side=side, end=m[4], p=p, h=(m[4] - t) / 3600, thr=v,
                    rung="top" if v == vs[-1] and len(vs) > 1 else ("bottom" if v == vs[0] and len(vs) > 1 else "middle"),
                    f=(1 if fl & 2 else 0) - p - m[7] * p * (1 - p))
del blob
R = list(first.values())


def stat(rr):
    ev = collections.defaultdict(lambda: [0.0, 0])
    for r in rr: ev[r["e"]][0] += r["f"]; ev[r["e"]][1] += 1
    v = list(ev.values()); n = sum(y[1] for y in v)
    if not n: return {"n": 0, "films": 0}
    o = {"n": n, "films": len(v), "pts": round(100 * sum(y[0] for y in v) / n, 2), "avg_p": round(sum(r["p"] for r in rr) / n, 3)}
    if len(v) >= 5:
        bs = sorted(sum(y[0] for y in s) / max(1, sum(y[1] for y in s)) for s in ([v[int(random.random() * len(v))] for _ in v] for _ in range(1000)))
        o["ci"] = [round(100 * bs[25], 1), round(100 * bs[974], 1)]
    return o


ends = sorted({MK[mi][4] for mi in sel}); mid = sorted(r["end"] for r in R)[len(R) // 2]
NO = [r for r in R if r["side"] == "NO"]
half = lambda rr: {"older": stat([r for r in rr if r["end"] < mid]), "newer": stat([r for r in rr if r["end"] >= mid])}
out = {"markets": len(sel), "films": len(lad), "rows": len(R), "split_at": str(dt.datetime.fromtimestamp(mid, dt.timezone.utc)),
       "NO": stat(NO), "NO halves": half(NO), "YES": stat([r for r in R if r["side"] == "YES"])}
splits = {
    "h>168": lambda r: r["h"] > 168, "h24-168": lambda r: 24 <= r["h"] <= 168, "h<24": lambda r: r["h"] < 24,
    "top": lambda r: r["rung"] == "top", "middle": lambda r: r["rung"] == "middle", "bottom": lambda r: r["rung"] == "bottom",
    "p<0.30": lambda r: r["p"] < 0.30, "p0.30-0.60": lambda r: 0.30 <= r["p"] <= 0.60, "p>0.60": lambda r: r["p"] > 0.60,
}
surv = []
for name, fn in splits.items():
    rr = [r for r in NO if fn(r)]
    s = stat(rr); h = half(rr); out[f"NO {name}"] = {**s, **{k: (v.get("pts"), v.get("films")) for k, v in h.items()}}
    if s.get("pts", -1) >= 5 and s.get("ci", [-1])[0] > 0 and s["films"] >= 15 and (h["older"].get("pts") or -1) > 0 and (h["newer"].get("pts") or -1) > 0:
        surv.append(name)
o = out["NO halves"]["older"]
dead = (o.get("pts", -9) <= 3) or out["NO"]["films"] < 30
out["surviving splits"] = surv
out["verdict"] = "DEAD (older half <= +3 or < 30 films)" if dead else ("PASS -> paper arm: " + ",".join(surv) if surv else "DEAD (no split passes)")
print(json.dumps(out, indent=1))
json.dump(out, open(f"{B}rt_ladder_report.json", "w"), indent=1)
