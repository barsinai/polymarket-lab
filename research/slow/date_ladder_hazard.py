"""Cycle 47, N102 (outside the box): date-ladder hazard consistency ('X by Oct 31' / 'by Nov 30' / 'by Dec 31' in one event).
Why the crowd could be wrong: each rung is traded on its own; YES holders of the NEAR rung keep their hope until the last day (nobody sells
a lottery ticket early), so the near rung decays slower than the far rung's own price implies. Under a constant hazard the far rung pins
the near one: P1_fair = 1 - (1 - P2) ** (t1 / t2). A near rung priced well above that is either front-loaded news (lesson 2: right) or
stale hope (our edge). Never tested: lesson 8 used ladders only as riskless sums (P1 <= P2), not as a hazard model.
Rules fixed BEFORE looking (written here first): tapes a + b + c (events once, first tape), finished markets, questions with 'by'/'before',
events with >= 2 distinct end days. At a NO-direction taker entry on market m (follower fill a300, fee rate * p(1-p)): m must be the
NEAREST rung still open at t; the next rung's YES price = its last taker print within 6 h before t (YES side a, NO side 1 - a); 1-14 days
to m's end; NO price 0.50-0.95. gap = (1 - p_NO) - P1_fair. Arms: RICH gap >= +0.05 (the bet), BASE gap < +0.05 (placebo / base rate).
First qualifying entry per market per arm. Unit = event, bootstrap 1,000, halves by end date.
DECISION: paper arm only if RICH >= +3 pts, CI low > 0, >= 30 events, both halves >= +2, and RICH - BASE >= +2. Printed, not used to pass:
gap >= 0.10, 1-3 d vs 3-14 d, category. Exposed to 2 (front-loaded news), 11 (path questions: finished only), 6 (one topic = several
ladders: also clustered by topic word), 13, 22, 24, 8."""
import json, gzip, struct, collections, random, re, bisect, datetime as dt
ROW = struct.Struct("<IIIhfffHHHIB")
B = "data/research/"
random.seed(102)
BY = re.compile(r"\b(by|before)\b", re.I)
R, seen_ev = [], set()
for g in "abc":
    meta = json.load(gzip.open(f"{B}entries_{g}_meta.json.gz")); MK = meta["markets"]
    at = dt.datetime.strptime(meta["at"], "%Y-%m-%d %H:%M").replace(tzinfo=dt.timezone.utc).timestamp()
    ev = collections.defaultdict(list)
    for mi, m in enumerate(MK):
        if m[4] < at and m[1] not in seen_ev and BY.search(m[3]): ev[m[1]].append(mi)
    ev = {e: sorted(v, key=lambda mi: MK[mi][4]) for e, v in ev.items() if len({MK[mi][4] // 86400 for mi in v}) >= 2}
    inl = {mi: e for e, v in ev.items() for mi in v}
    blob = gzip.open(f"{B}entries_{g}.bin.gz").read()
    px = collections.defaultdict(list); cand = collections.defaultdict(list)
    for t, mi, wi, hb, S, C, F, a, a60, a300, lag, fl in ROW.iter_unpack(blob):
        if mi not in inl or S <= 0 or C <= 0 or a <= 0: continue
        yes = fl & 1; pa = a / 1e4
        px[mi].append((t, pa if yes else 1 - pa))
        if not yes and a300 > 0: cand[mi].append((t, a300 / 1e4, fl))
    del blob
    for mi in px: px[mi].sort()
    for e, rungs in ev.items():
        for i, mi in enumerate(rungs):
            m = MK[mi]
            nxt = [mj for mj in rungs[i + 1:] if MK[mj][4] // 86400 > m[4] // 86400]
            if not nxt: continue
            done = set()
            for t, p, fl in sorted(cand.get(mi, [])):
                if any(MK[mk][4] > t and MK[mk][4] < m[4] for mk in rungs[:i]): continue   # an earlier rung still open
                h = (m[4] - t) / 3600
                if not (24 <= h <= 14 * 24 and 0.50 <= p <= 0.95): continue
                mj = nxt[0]; P = px.get(mj, []); ts = [x[0] for x in P]
                k = bisect.bisect_left(ts, t)
                if k == 0 or t - P[k - 1][0] > 6 * 3600: continue
                P2 = min(max(P[k - 1][1], 0.001), 0.999); t1 = m[4] - t; t2 = MK[mj][4] - t
                fair = 1 - (1 - P2) ** (t1 / t2); gap = (1 - p) - fair
                arm = "RICH" if gap >= 0.05 else "BASE"
                if arm in done: continue
                done.add(arm)
                topic = re.sub(r"[^a-z ]", "", m[3].lower()).split(" by ")[0][:40]
                R.append(dict(e=f"{g}:{e}", topic=topic, cat=m[2], end=m[4], p=p, h=h, gap=gap, arm=arm,
                              f=(1 if fl & 2 else 0) - p - m[7] * p * (1 - p)))
    seen_ev |= set(ev)
def stat(rr, key="e"):
    ev = collections.defaultdict(lambda: [0.0, 0])
    for r in rr: ev[r[key]][0] += r["f"]; ev[r[key]][1] += 1
    v = list(ev.values()); n = sum(y[1] for y in v)
    if not n: return {"n": 0, "events": 0}
    o = {"n": n, "events": len(v), "pts": round(100 * sum(y[0] for y in v) / n, 2), "avg_p": round(sum(r["p"] for r in rr) / n, 3)}
    if len(v) >= 5:
        bs = sorted(sum(y[0] for y in s) / max(1, sum(y[1] for y in s)) for s in ([v[int(random.random() * len(v))] for _ in v] for _ in range(1000)))
        o["ci"] = [round(100 * bs[25], 1), round(100 * bs[974], 1)]
    return o
mid = sorted(r["end"] for r in R)[len(R) // 2] if R else 0
half = lambda rr: {"older": stat([r for r in rr if r["end"] < mid]).get("pts"), "newer": stat([r for r in rr if r["end"] >= mid]).get("pts")}
RI = [r for r in R if r["arm"] == "RICH"]; BA = [r for r in R if r["arm"] == "BASE"]
cats = collections.Counter(r["cat"] for r in RI)
out = {"rows": len(R), "RICH": {**stat(RI), **half(RI)}, "BASE": {**stat(BA), **half(BA)},
       "RICH by topic cluster": stat(RI, "topic"), "RICH gap >= 0.10": stat([r for r in RI if r["gap"] >= 0.10]),
       "RICH 1-3 d": stat([r for r in RI if r["h"] < 72]), "RICH 3-14 d": stat([r for r in RI if r["h"] >= 72]),
       "RICH by cat": {c: stat([r for r in RI if r["cat"] == c]) for c, _ in cats.most_common(6)}}
s, b = out["RICH"], out["BASE"]
ok = (s.get("pts", -9) >= 3 and s.get("ci", [-1])[0] > 0 and s.get("events", 0) >= 30
      and min(s.get("older") or -9, s.get("newer") or -9) >= 2 and s.get("pts", -9) - b.get("pts", 9) >= 2)
out["verdict"] = "PASS -> paper arm" if ok else "DEAD (fails the fixed rule)"
print(json.dumps(out, indent=1)); json.dump(out, open(f"{B}date_ladder_hazard_report.json", "w"), indent=1)
