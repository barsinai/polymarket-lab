"""Cycle 49, N106 (outside the box): fade a one-sided crowd - the market where almost every new trader buys the same way.
Why the crowd could be wrong: every earlier tape study scored WHO trades (size, skill, freshness, urgency). This one scores the SHAPE of
the crowd: when >= 80% of the dollars of the first 30 distinct entrants went one way, the price was pushed by a herd of small, correlated
views (fans, one headline), and the few who took the other side are the informed ones (lesson 17 says the passive side pays the informed
side; here the 'other side' are takers too). Exposed to 2 (a herd can be right: the news really happened), 13, 22, 24, 11 (path
questions: YES herds on 'hit X' are early-resolution biased -> finished markets only), 5/6.
Rules fixed BEFORE looking (written here first): tapes a + b + c, finished markets, >= 30 first-entry rows. TRIGGER = the time of the
30th first entry; share = YES-direction cost / all cost over those 30. HERD market: share >= 0.80 or <= 0.20. CONTRA = the first entry
in the minority direction after the trigger, scored at its a300 (a price a follower could have had >= 300 s after a real trade that
way); HERD-FOLLOW = the first entry in the majority direction after the trigger, at its a300. BALANCED control (share 0.40-0.60): the
first entry each way after the trigger. >= 1 h left at the scored entry, fill 0.05-0.95, fee rate * p(1-p) paid. One row per market per
arm. Unit = event, bootstrap 1,000, halves by end date.
DECISION: paper only if CONTRA >= +3 pts, CI low > 0, >= 50 events, halves >= +1.5, CONTRA - HERD-FOLLOW >= +3.
Caveat: whether a minority-side trade arrives at all is not known at the trigger; the scored price is real but the timing is not ours."""
import json, gzip, struct, collections, random, datetime as dt
ROW = struct.Struct("<IIIhfffHHHIB")
B = "data/research/"
random.seed(106)
R = []
for g in "abc":
    meta = json.load(gzip.open(f"{B}entries_{g}_meta.json.gz")); MK = meta["markets"]
    at = dt.datetime.strptime(meta["at"], "%Y-%m-%d %H:%M").replace(tzinfo=dt.timezone.utc).timestamp()
    ent = collections.defaultdict(list)
    for t, mi, wi, hb, S, C, F, a, a60, a300, lag, fl in ROW.iter_unpack(gzip.open(f"{B}entries_{g}.bin.gz").read()):
        if MK[mi][4] < at: ent[mi].append((t, C, a300, fl))
    for mi, E in ent.items():
        if len(E) < 31: continue
        m = MK[mi]; E.sort(); head = E[:30]; t0 = head[-1][0]
        tot = sum(e[1] for e in head)
        if tot <= 0: continue
        share = sum(e[1] for e in head if e[3] & 1) / tot
        if share >= 0.8 or share <= 0.2:
            maj = 1 if share >= 0.8 else 0; arms = {"CONTRA": 1 - maj, "HERD": maj}
        elif 0.4 <= share <= 0.6:
            arms = {"BAL_YES": 1, "BAL_NO": 0}
        else:
            continue
        for arm, d in arms.items():
            nxt = next((e for e in E[30:] if (e[3] & 1) == d and e[2] > 0), None)
            if nxt is None: continue
            t, C, a300, fl = nxt
            if m[4] - t < 3600 or not 500 <= a300 <= 9500: continue
            p = a300 / 1e4; won = 1 if fl & 2 else 0
            R.append(dict(e=f"{g}:{m[1]}", g=g, end=m[4], arm=arm, yes=d, share=share, p=p, f=won - p - m[7] * p * (1 - p)))


def stat(rr):
    ev = collections.defaultdict(lambda: [0.0, 0])
    for r in rr:
        ev[r["e"]][0] += r["f"]; ev[r["e"]][1] += 1
    E = list(ev.values())
    if len(E) < 3: return dict(n=len(rr), events=len(E))
    tot = lambda S: 100 * sum(s for s, _ in S) / sum(n for _, n in S)
    bs = sorted(tot([random.choice(E) for _ in E]) for _ in range(1000))
    return dict(n=len(rr), events=len(E), pts=round(tot(E), 2), ci=[round(bs[25], 2), round(bs[975], 2)],
                avg_p=round(sum(r["p"] for r in rr) / len(rr), 3))


out = {}
for arm in ("CONTRA", "HERD", "BAL_YES", "BAL_NO"):
    rr = [r for r in R if r["arm"] == arm]
    if not rr: continue
    med = sorted(r["end"] for r in rr)[len(rr) // 2]
    out[arm] = dict(all=stat(rr), older=stat([r for r in rr if r["end"] < med]), newer=stat([r for r in rr if r["end"] >= med]),
                    yes_side=stat([r for r in rr if r["yes"]]), no_side=stat([r for r in rr if not r["yes"]]),
                    **{f"group_{g}": stat([r for r in rr if r["g"] == g]) for g in "abc"})
C, H = out.get("CONTRA", {}), out.get("HERD", {})
ok = (C and C["all"].get("events", 0) >= 50 and C["all"]["pts"] >= 3 and C["all"]["ci"][0] > 0
      and C["older"].get("pts", -9) >= 1.5 and C["newer"].get("pts", -9) >= 1.5 and C["all"]["pts"] - H["all"]["pts"] >= 3)
out["verdict"] = "PAPER" if ok else "DEAD"
json.dump(out, open("data/research/herd_contra_report.json", "w"), indent=1)
for k, v in out.items():
    print(k, json.dumps(v) if not isinstance(v, dict) else json.dumps({kk: (vv.get("pts"), vv.get("events"), vv.get("ci"), vv.get("avg_p")) for kk, vv in v.items()}))
