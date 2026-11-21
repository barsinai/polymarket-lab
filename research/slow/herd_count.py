"""Cycle 52, N112 (adjacent to N107 HERD): count the herd by HEADS, not dollars.
N107's story is 'many independent people saw the same answer', but its share is dollar-weighted: one $2,000 whale among 30 entrants can
make a 'herd' alone. If the story is right, a headcount herd (>= 80% of the first 30 distinct entrants one way, by number) should carry
the edge, and a dollar herd that is NOT a headcount herd (a whale) should not.
Exposed to 22 (a variant of a rule found by looking -> OOS decides), 15, 16, 11, 24, 6.
Rules fixed BEFORE looking: same rows as herd_contra / herd_oos2 (first 30 first-entries, follow = first majority-way entry after the
30th at its a300, 0.05-0.95, >= 1 h left, fee). N_share = YES-direction rows / 30; D_share = YES $ share.
Arms: BOTH (N and D herds, same side), N_ONLY (count herd, dollar share 0.2-0.8), D_ONLY (dollar herd, count share 0.2-0.8).
DECISION: switch N107 to the headcount rule only if N_ONLY >= +2 pts on >= 100 canonical events AND >= +2 OOS (>= 30 events) AND
N_ONLY - D_ONLY >= +2 canonical; else DEAD (N107 keeps its dollar rule).
Also printed, KILL-ONLY (found by looking at copy_burst.py's placebo, lesson 22): SLOW5 = 5 distinct same-way first entries spanning
1-6 h with no 5-in-120 s burst BEFORE the 5th (knowable at the time), >= 1 h after the first row, follow at the 5th row's a300."""
import json, gzip, struct, collections, random, datetime as dt
ROW = struct.Struct("<IIIhfffHHHIB"); B = "data/research/"
random.seed(112)


def load(g, tag, skip=None):
    meta = json.load(gzip.open(f"{B}entries_{g}{tag}_meta.json.gz")); MK = meta["markets"]
    at = dt.datetime.strptime(meta["at"], "%Y-%m-%d %H:%M").replace(tzinfo=dt.timezone.utc).timestamp()
    ent = collections.defaultdict(list)
    for t, mi, wi, hb, S, C, F, a, a60, a300, lag, fl in ROW.iter_unpack(gzip.open(f"{B}entries_{g}{tag}.bin.gz").read()):
        if MK[mi][4] < at and (skip is None or MK[mi][0] not in skip): ent[mi].append((t, wi, C, a300, fl))
    return MK, ent


def score(g, MK, ent, R):
    for mi, E in ent.items():
        m = MK[mi]; E.sort()
        def add(arm, e):
            t, wi, C, a300, fl = e; p = a300 / 1e4
            if m[4] - t < 3600 or not 0.05 <= p <= 0.95: return
            R.append(dict(e=f"{g}:{m[1]}", g=g, end=m[4], arm=arm, p=p, f=(1 if fl & 2 else 0) - p - m[7] * p * (1 - p)))
        if len(E) >= 31:
            head = E[:30]; tot = sum(e[2] for e in head)
            if tot > 0:
                D = sum(e[2] for e in head if e[4] & 1) / tot; N = sum(1 for e in head if e[4] & 1) / 30
                nh, dh = N >= 0.8 or N <= 0.2, D >= 0.8 or D <= 0.2
                arm = None
                if nh and dh and (N >= 0.5) == (D >= 0.5): arm, maj = "BOTH", int(N >= 0.5)
                elif nh and 0.2 < D < 0.8: arm, maj = "N_ONLY", int(N >= 0.5)
                elif dh and 0.2 < N < 0.8: arm, maj = "D_ONLY", int(D >= 0.5)
                if arm:
                    h = next((e for e in E[30:] if (e[4] & 1) == maj and e[3] > 0), None)
                    if h: add(arm, h)
        if len(E) >= 6:
            t0 = E[0][0]; best = None
            for d in (0, 1):
                S = [e for e in E if (e[4] & 1) == d and e[0] >= t0 + 3600]
                burst_t = min((S[i + 4][0] for i in range(len(S) - 4) if S[i + 4][0] - S[i][0] <= 120
                               and len({x[1] for x in S[i:i + 5]}) == 5), default=None)
                for i in range(len(S) - 4):
                    w = S[i:i + 5]
                    if 3600 <= w[-1][0] - w[0][0] <= 6 * 3600 and len({x[1] for x in w}) == 5:
                        if burst_t is None or burst_t > w[-1][0]:
                            if best is None or w[-1][0] < best[0]: best = w[-1]
                        break
            if best: add("SLOW5", best)


def stat(rr):
    ev = collections.defaultdict(lambda: [0.0, 0])
    for r in rr: ev[r["e"]][0] += r["f"]; ev[r["e"]][1] += 1
    E = list(ev.values())
    if len(E) < 3: return dict(events=len(E))
    tot = lambda S: 100 * sum(s for s, _ in S) / sum(n for _, n in S)
    bs = sorted(tot([random.choice(E) for _ in E]) for _ in range(1000))
    return dict(n=len(rr), events=len(E), pts=round(tot(E), 2), ci=[round(bs[25], 2), round(bs[975], 2)],
                avg_p=round(sum(r["p"] for r in rr) / len(rr), 3))


RC, RO = [], []
for g in "abc":
    MK, ent = load(g, ""); score(g, MK, ent, RC); seen = {m[0] for m in MK}
    MK2, ent2 = load(g, "_oos1", seen); score(g, MK2, ent2, RO)
out = {}
for arm in ("BOTH", "N_ONLY", "D_ONLY", "SLOW5"):
    rr = [r for r in RC if r["arm"] == arm]
    if not rr: out[arm] = {}; continue
    med = sorted(r["end"] for r in rr)[len(rr) // 2]
    out[arm] = dict(all=stat(rr), older=stat([r for r in rr if r["end"] < med]), newer=stat([r for r in rr if r["end"] >= med]),
                    oos=stat([r for r in RO if r["arm"] == arm]), **{f"group_{g}": stat([r for r in rr if r["g"] == g]) for g in "abc"})
N, Dd = out["N_ONLY"], out["D_ONLY"]
ok = (N and N["all"].get("events", 0) >= 100 and N["all"]["pts"] >= 2 and N["oos"].get("events", 0) >= 30 and N["oos"]["pts"] >= 2
      and Dd and N["all"]["pts"] - Dd["all"].get("pts", 0) >= 2)
out["verdict"] = "SWITCH" if ok else "DEAD"
json.dump(out, open(f"{B}herd_count_report.json", "w"), indent=1)
for k, v in out.items():
    print(k, json.dumps(v) if k == "verdict" else json.dumps({kk: (vv.get("pts"), vv.get("events"), vv.get("ci"), vv.get("avg_p")) for kk, vv in v.items()}))
