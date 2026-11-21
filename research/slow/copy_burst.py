"""Cycle 52, N113 (outside the box): copy-trade cascades.
Mechanism we never touched: copy-trading bots / Telegram copy groups. When a followed wallet trades, many small wallets enter the
same way within seconds-minutes - first-ever entries of 5+ DIFFERENT wallets the same way inside 120 s. Every earlier tape study
scored who trades or the crowd at the launch; this scores a short-time CASCADE anywhere in a market's life.
Why the crowd could be wrong: copiers pay whatever the book shows after the leader (lesson 30: paying up is not information), so the
price overshoots and the opposite side is cheap for a while -> FADE. Or the cascade is a real piece of news reaching many people at
once -> FOLLOW. The rule decides; both arms are scored, plus a placebo.
Exposed to 1 (if it is news, bots are faster), 2, 17, 22 (two arms -> forking; both need OOS), 24, 30, 5/6.
Rules fixed BEFORE looking (written here first):
- tapes a + b + c canonical (finished markets) for the first read; the same rule on the oos1 tapes, ids unseen in the canonical tape.
- per market: sort first-entry rows; BURST = 5 rows of the same direction, 5 distinct wallets, inside 120 s (t5 - t1 <= 120), with
  t1 >= the market's first row + 3600 s (not the launch hour, N58's ground) and >= 1 h left at the scored entry. First burst per market.
- FOLLOW: the burst's 5th row's a300 (the next same-way print by someone else >= 300 s later - a price a follower could have had).
- FADE: the first opposite-direction row with t >= t5 + 300, scored at its a300.
- PLACEBO: first SLOW cluster per market (5 distinct same-way first entries spanning 1-6 h, no burst in the market), follow at a300.
- fill 0.05-0.95, fee rate * p(1-p), unit = event (event slug), bootstrap 1,000, halves by end date.
DECISION: an arm goes to paper only if canonical >= +3 pts, CI low > 0, >= 100 events, both halves >= +1.5, arm - PLACEBO >= +2,
and OOS >= +2 on >= 50 events. Else DEAD.
Caveat: the FADE entry's existence is not known at the trigger (its price is real, its timing is a tape print)."""
import json, gzip, struct, collections, random, datetime as dt
ROW = struct.Struct("<IIIhfffHHHIB"); B = "data/research/"
random.seed(113)


def load(g, tag, skip=None):
    meta = json.load(gzip.open(f"{B}entries_{g}{tag}_meta.json.gz")); MK = meta["markets"]
    at = dt.datetime.strptime(meta["at"], "%Y-%m-%d %H:%M").replace(tzinfo=dt.timezone.utc).timestamp()
    ent = collections.defaultdict(list)
    for t, mi, wi, hb, S, C, F, a, a60, a300, lag, fl in ROW.iter_unpack(gzip.open(f"{B}entries_{g}{tag}.bin.gz").read()):
        if MK[mi][4] < at and (skip is None or MK[mi][0] not in skip): ent[mi].append((t, wi, C, a300, fl))
    return MK, ent


def score(g, MK, ent, R):
    for mi, E in ent.items():
        if len(E) < 6: continue
        m = MK[mi]; E.sort(); t0 = E[0][0]
        def add(arm, e, extra=None):
            t, wi, C, a300, fl = e; p = a300 / 1e4
            if m[4] - t < 3600 or not 0.05 <= p <= 0.95: return
            R.append(dict(e=f"{g}:{m[1]}", g=g, end=m[4], arm=arm, p=p, cat=m[2],
                          f=(1 if fl & 2 else 0) - p - m[7] * p * (1 - p)))
        burst = None
        for d in (0, 1):
            S = [e for e in E if (e[4] & 1) == d and e[0] >= t0 + 3600]
            for i in range(len(S) - 4):
                w = S[i:i + 5]
                if w[-1][0] - w[0][0] <= 120 and len({x[1] for x in w}) == 5:
                    if burst is None or w[-1][0] < burst[1][0]: burst = (d, w[-1])
                    break
        if burst:
            d, e5 = burst
            add("FOLLOW", e5)
            o = next((e for e in E if (e[4] & 1) != d and e[0] >= e5[0] + 300 and e[3] > 0), None)
            if o: add("FADE", o)
        else:
            for d in (0, 1):
                S = [e for e in E if (e[4] & 1) == d and e[0] >= t0 + 3600]
                for i in range(len(S) - 4):
                    w = S[i:i + 5]
                    if 3600 <= w[-1][0] - w[0][0] <= 6 * 3600 and len({x[1] for x in w}) == 5:
                        add("PLACEBO", w[-1]); break
                else:
                    continue
                break


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
    try:
        MK2, ent2 = load(g, "_oos1", seen); score(g, MK2, ent2, RO)
    except FileNotFoundError:
        print("no oos", g)
out = {}
for arm in ("FOLLOW", "FADE", "PLACEBO"):
    rr = [r for r in RC if r["arm"] == arm]
    if not rr: out[arm] = {}; continue
    med = sorted(r["end"] for r in rr)[len(rr) // 2]
    out[arm] = dict(all=stat(rr), older=stat([r for r in rr if r["end"] < med]), newer=stat([r for r in rr if r["end"] >= med]),
                    oos=stat([r for r in RO if r["arm"] == arm]),
                    **{f"group_{g}": stat([r for r in rr if r["g"] == g]) for g in "abc"})
P = out["PLACEBO"].get("all", {}).get("pts", 0)
def ok(a):
    A = out[a]
    return (A and A["all"].get("events", 0) >= 100 and A["all"]["pts"] >= 3 and A["all"]["ci"][0] > 0 and A["older"].get("pts", -9) >= 1.5
            and A["newer"].get("pts", -9) >= 1.5 and A["all"]["pts"] - P >= 2 and A["oos"].get("events", 0) >= 50 and A["oos"]["pts"] >= 2)
out["verdict"] = {a: ("PAPER" if ok(a) else "DEAD") for a in ("FOLLOW", "FADE")}
json.dump(out, open(f"{B}copy_burst_report.json", "w"), indent=1)
for k, v in out.items():
    print(k, json.dumps(v) if k == "verdict" else json.dumps({kk: (vv.get("pts"), vv.get("events"), vv.get("ci"), vv.get("avg_p")) for kk, vv in v.items()}))
