"""Cycle 46, N99 (adjacent to N95 RT ladders / N97 fan ladders): post-count brackets ('Will Elon Musk post 200-219 tweets from ... to ...?').
Why the crowd could be wrong: the count is a running tally with a steady rate, yet fans and bulls keep buying the brackets ABOVE the leading
bracket ('he'll go on a spree') - the same upper-rung overbuying that RT ladders showed. Not tested before: N44 bought the favourite bracket
(-3.1), N31 bid favourites; nobody sold the brackets above the favourite.
Rules fixed BEFORE looking (written here first): tapes a + c, finished events whose questions match 'post N-M tweets/posts' or 'N+ ...';
each event counted once (first tape that has it). Bracket rank by its lower bound. Favourite at time t = the bracket with the highest
YES price among brackets that printed within the previous 6 h (YES price from the taker's own price: YES side a, NO side 1 - a).
Entry = first NO-direction taker entry per market whose bracket ranks ABOVE the favourite at the entry time, follower fill a300, NO price
0.60-0.90 (the 0.90+ near-certain seat is dead, LESSONS), 6-120 h before the end, fee rate * p(1-p). Unit = event, bootstrap 1,000, halves.
DECISION: paper arm only if NO-above >= +3 pts, CI low > 0, >= 30 events, both halves >= +2. Placebo: NO on brackets BELOW the favourite,
same band. Printed, not used to pass: 1 vs 2+ brackets above, hours to end. Exposed to 2, 13 (pace is public), 22, 24, 5/6, 15."""
import json, gzip, struct, collections, random, re, datetime as dt, bisect
ROW = struct.Struct("<IIIhfffHHHIB")
B = "data/research/"
random.seed(99)
BR = re.compile(r"post (\d[\d,]*)\s*(?:-\s*(\d[\d,]*)|\+|or more)\s*(?:tweets|posts)", re.I)
R, seen_ev = [], set()
for g in "ac":
    meta = json.load(gzip.open(f"{B}entries_{g}_meta.json.gz")); MK = meta["markets"]
    at = dt.datetime.strptime(meta["at"], "%Y-%m-%d %H:%M").replace(tzinfo=dt.timezone.utc).timestamp()
    lo = {}
    for mi, m in enumerate(MK):
        if m[4] >= at or m[1] in seen_ev: continue
        x = BR.search(m[3])
        if x: lo[mi] = int(x[1].replace(",", ""))
    evs = {MK[mi][1] for mi in lo}
    rank = {}
    for e in evs:
        ms = sorted((v, mi) for mi, v in lo.items() if MK[mi][1] == e)
        if len(ms) < 4: continue
        for r_, (v, mi) in enumerate(ms): rank[mi] = r_
    blob = gzip.open(f"{B}entries_{g}.bin.gz").read()
    px = collections.defaultdict(list)            # event -> [(t, mi, yes_price)]
    cand = {}
    for t, mi, wi, hb, S, C, F, a, a60, a300, lag, fl in ROW.iter_unpack(blob):
        if mi not in rank or S <= 0 or C <= 0 or a <= 0: continue
        yes = fl & 1; pa = a / 1e4
        px[MK[mi][1]].append((t, mi, pa if yes else 1 - pa))
        if not yes:
            cand.setdefault(mi, []).append((t, a300, fl))
    del blob
    for e in px: px[e].sort()
    for mi, lst in cand.items():
        m = MK[mi]; e = m[1]; P = px[e]; ts = [x[0] for x in P]
        for t, a300, fl in sorted(lst):
            h = (m[4] - t) / 3600; p = a300 / 1e4
            if not (6 <= h <= 120 and 0.60 <= p <= 0.90): continue
            last = {}
            for tt, mj, y in P[bisect.bisect_left(ts, t - 6 * 3600):bisect.bisect_left(ts, t)]: last[mj] = y
            if not last: continue
            fav = max(last, key=last.get)
            d = rank[mi] - rank[fav]
            if d == 0: continue
            R.append(dict(e=f"{g}:{e}", end=m[4], p=p, h=h, d=d, f=(1 if fl & 2 else 0) - p - m[7] * p * (1 - p)))
            break
    seen_ev |= evs
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
mid = sorted(r["end"] for r in R)[len(R) // 2] if R else 0
half = lambda rr: {"older": stat([r for r in rr if r["end"] < mid]).get("pts"), "newer": stat([r for r in rr if r["end"] >= mid]).get("pts")}
A = [r for r in R if r["d"] > 0]; Bl = [r for r in R if r["d"] < 0]
out = {"rows": len(R), "NO above fav": {**stat(A), **half(A)}, "NO below fav (placebo)": {**stat(Bl), **half(Bl)},
       "above, 1 bracket": stat([r for r in A if r["d"] == 1]), "above, 2+": stat([r for r in A if r["d"] >= 2]),
       "above, 6-24 h": stat([r for r in A if r["h"] < 24]), "above, 24-120 h": stat([r for r in A if r["h"] >= 24])}
s = out["NO above fav"]
ok = s.get("pts", -9) >= 3 and s.get("ci", [-1])[0] > 0 and s.get("events", 0) >= 30 and min(s.get("older") or -9, s.get("newer") or -9) >= 2
out["verdict"] = "PASS -> paper arm" if ok else "DEAD (fails the fixed rule)"
print(json.dumps(out, indent=1)); json.dump(out, open(f"{B}count_bracket_upper_report.json", "w"), indent=1)
