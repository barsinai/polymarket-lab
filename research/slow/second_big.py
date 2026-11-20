"""Cycle 49, N105 (adjacent to COPY-1 / lesson 17 / lesson 30): a SECOND independent big taker agreeing with the first.
Why the crowd could be wrong: one big taker is often a single noisy view (big takers are only +1.2 pts on average, lesson 17); a second,
different wallet putting >= $200 the same way soon after is independent agreement - two people who looked and reached the same answer.
If information is what makes big takers win, agreement should concentrate it, and the book (thin, slow categories) may not re-price
until the third. Exposed to 22 (forking paths), 24 (halves), 23 (simulate the follower's fill), 30 (urgency != information), 5/6.
Rules fixed BEFORE looking (written here first): tapes a + b + c, finished markets only. Big entry = first-entry row with cost >= $200
and own fill 0.05-0.95. Per market + direction, FIRST = the earliest big entry; AGREE = the earliest big entry by a DIFFERENT wallet in
the same direction within 48 h of FIRST; CONFLICT = the earliest big entry the other way by a different wallet within 48 h of FIRST
(printed only). >= 1 h left to the end at the signal. Follower fill a300 (next same-way print >= 300 s later) in 0.05-0.95, fee
rate * p(1-p) paid; one row per market + direction per arm. Unit = event (event slug), bootstrap 1,000, halves by end date.
DECISION: paper arm in COPY-1 only if AGREE >= +3 pts, CI low > 0, >= 50 events, both halves >= +1.5 and AGREE - FIRST >= +1.5.
Also printed: AGREE at the second wallet's own fill, gap <= 6 h vs 6-48 h, per group."""
import json, gzip, struct, collections, random, datetime as dt
ROW = struct.Struct("<IIIhfffHHHIB")
B = "data/research/"
random.seed(105)
R = []
for g in "abc":
    meta = json.load(gzip.open(f"{B}entries_{g}_meta.json.gz")); MK = meta["markets"]
    at = dt.datetime.strptime(meta["at"], "%Y-%m-%d %H:%M").replace(tzinfo=dt.timezone.utc).timestamp()
    big = collections.defaultdict(list)
    for t, mi, wi, hb, S, C, F, a, a60, a300, lag, fl in ROW.iter_unpack(gzip.open(f"{B}entries_{g}.bin.gz").read()):
        m = MK[mi]
        if m[4] >= at or C < 200 or not 500 <= a <= 9500: continue
        big[(mi, fl & 1)].append((t, wi, a, a300, fl))
    for (mi, d), E in big.items():
        m = MK[mi]; E.sort(); t1, w1, *_ = E[0]
        cands = {"FIRST": E[0]}
        ag = [e for e in E[1:] if e[1] != w1 and e[0] - t1 <= 48 * 3600]
        if ag: cands["AGREE"] = ag[0]
        op = [e for e in sorted(big.get((mi, 1 - d), [])) if e[1] != w1 and 0 <= e[0] - t1 <= 48 * 3600]
        if op: cands["CONFLICT"] = op[0]
        for arm, (t, wi, a, a300, fl) in cands.items():
            if m[4] - t < 3600 or not 500 <= a300 <= 9500: continue
            p = a300 / 1e4; q = a / 1e4; won = 1 if fl & 2 else 0
            R.append(dict(e=f"{g}:{m[1]}", g=g, end=m[4], arm=arm, gap=(t - t1) / 3600, yes=fl & 1,
                          f=won - p - m[7] * p * (1 - p), own=won - q - m[7] * q * (1 - q)))


def stat(rr, key="f"):
    ev = collections.defaultdict(lambda: [0.0, 0])
    for r in rr:
        ev[r["e"]][0] += r[key]; ev[r["e"]][1] += 1
    E = list(ev.values())
    if len(E) < 3: return dict(n=len(rr), events=len(E))
    tot = lambda S: 100 * sum(s for s, _ in S) / sum(n for _, n in S)
    bs = sorted(tot([random.choice(E) for _ in E]) for _ in range(1000))
    return dict(n=len(rr), events=len(E), pts=round(tot(E), 2), ci=[round(bs[25], 2), round(bs[975], 2)])


out = {}
for arm in ("FIRST", "AGREE", "CONFLICT"):
    rr = [r for r in R if r["arm"] == arm]
    if not rr: continue
    med = sorted(r["end"] for r in rr)[len(rr) // 2]
    out[arm] = dict(all=stat(rr), older=stat([r for r in rr if r["end"] < med]), newer=stat([r for r in rr if r["end"] >= med]),
                    own_fill=stat(rr, "own"), **{f"group_{g}": stat([r for r in rr if r["g"] == g]) for g in "abc"})
ag = [r for r in R if r["arm"] == "AGREE"]
out["AGREE gap <= 6 h"] = stat([r for r in ag if r["gap"] <= 6])
out["AGREE gap 6-48 h"] = stat([r for r in ag if r["gap"] > 6])
A, F = out.get("AGREE", {}), out.get("FIRST", {})
ok = (A and A["all"].get("events", 0) >= 50 and A["all"]["pts"] >= 3 and A["all"]["ci"][0] > 0
      and A["older"].get("pts", -9) >= 1.5 and A["newer"].get("pts", -9) >= 1.5 and A["all"]["pts"] - F["all"]["pts"] >= 1.5)
out["verdict"] = "PAPER" if ok else "DEAD"
json.dump(out, open("data/research/second_big_report.json", "w"), indent=1)
print(json.dumps(out, indent=1))
