"""Cycle 41, N91 (outside the box): twin markets - the same question listed twice in different events (a stand-alone market and an
outcome of a multi-outcome event, or two copies of one series). If nobody arbitrages across events, buying YES in the cheaper copy and
NO in the dearer one locks 1 - cost. Rules fixed BEFORE looking.
Twins: tape groups a + c, full question text shown (< 69 chars, so the 70-char cut cannot merge different questions), normalised text
equal, different event slugs, scheduled ends within 24 h, and NOT a 'another / again' relist (those restart the clock, different
questions). Executable prices: for each pair, every taker entry in A (direction d) gives the follower price a300 (next print the same
way >= 300 s later); pair it with an entry in B of the OPPOSITE token direction whose a300 print time is within 600 s; lock = 1 - pA - pB
- fees (fee rate * p(1-p) each). Count pairs and events with lock >= 2c, before the end. Resolution check: did twins resolve the same?
DEAD if < 30 events with a >= 2c lock (lesson 8: riskless structures are cents and tiny size)."""
import json, gzip, struct, collections, re
ROW = struct.Struct("<IIIhfffHHHIB")
B = "data/research/"
out = {}
for g in "ac":
    meta = json.load(gzip.open(f"{B}entries_{g}_meta.json.gz")); MK = meta["markets"]
    by = collections.defaultdict(list)
    for i, m in enumerate(MK):
        q = re.sub(r"\W+", " ", m[3].lower()).strip()
        if len(m[3]) >= 69 or re.search(r"\b(another|again)\b", q):
            continue
        by[q].append(i)
    pairs = []
    for q, v in by.items():
        for a in range(len(v)):
            for b in range(a + 1, len(v)):
                A, Bm = MK[v[a]], MK[v[b]]
                if A[1] != Bm[1] and A[0] != Bm[0] and abs(A[4] - Bm[4]) <= 86400:
                    pairs.append((v[a], v[b], q))
    need = {i for p in pairs for i in p[:2]}
    pr = collections.defaultdict(list)   # mi -> [(t_print_approx, dir, price)]
    for t, mi, wi, hb, S, C, F, a, a60, a300, lag, fl in ROW.iter_unpack(gzip.open(f"{B}entries_{g}.bin.gz").read()):
        if mi in need and a300 and t < MK[mi][4]:
            pr[mi].append((t + 300, fl & 1, a300 / 1e4))
    res = []
    for a, b, q in pairs:
        same = MK[a][6] == MK[b][6]
        best = None
        for (ta, da, pa) in pr[a]:
            for (tb, db, pb) in pr[b]:
                if da != db and abs(ta - tb) <= 600:
                    f = MK[a][7] * pa * (1 - pa) + MK[b][7] * pb * (1 - pb)
                    lk = 1 - pa - pb - f
                    if best is None or lk > best:
                        best = lk
        res.append(dict(q=q[:60], ea=MK[a][1][:40], eb=MK[b][1][:40], same=same, best_lock=None if best is None else round(best, 3)))
    ev = {r["q"] for r in res if r["best_lock"] is not None and r["best_lock"] >= 0.02}
    out[g] = dict(pairs=len(res), resolved_same=sum(r["same"] for r in res), with_overlapping_prints=sum(r["best_lock"] is not None for r in res),
                  lock_ge_2c=sum((r["best_lock"] or -1) >= 0.02 for r in res), events_lock_ge_2c=len(ev), rows=res)
    print(g, {k: v for k, v in out[g].items() if k != "rows"})
    for r in res:
        print("  ", r)
json.dump(out, open(f"{B}twin_report.json", "w"), indent=1)
