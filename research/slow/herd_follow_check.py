"""Cycle 49, post-hoc KILL-ONLY check of N106's HERD-follow control (+3.5 pts): is it the herd, or just buying the 0.7-0.9 favourite
after the 30th entrant in any market? Same rules as herd_contra.py; BASE = in every market (any share), the first entry after the 30th
whose a300 is 0.70-0.92, scored on its own direction. HERD_B = HERD rows with a300 0.70-0.92. Also by week and share >= 0.9."""
import json, gzip, struct, collections, random, datetime as dt
ROW = struct.Struct("<IIIhfffHHHIB"); B = "data/research/"; random.seed(1061); R = []
for g in "abc":
    meta = json.load(gzip.open(f"{B}entries_{g}_meta.json.gz")); MK = meta["markets"]
    at = dt.datetime.strptime(meta["at"], "%Y-%m-%d %H:%M").replace(tzinfo=dt.timezone.utc).timestamp()
    ent = collections.defaultdict(list)
    for t, mi, wi, hb, S, C, F, a, a60, a300, lag, fl in ROW.iter_unpack(gzip.open(f"{B}entries_{g}.bin.gz").read()):
        if MK[mi][4] < at: ent[mi].append((t, C, a300, fl))
    for mi, E in ent.items():
        if len(E) < 31: continue
        m = MK[mi]; E.sort(); head = E[:30]; tot = sum(e[1] for e in head)
        if tot <= 0: continue
        share = sum(e[1] for e in head if e[3] & 1) / tot
        herd = share >= 0.8 or share <= 0.2; maj = 1 if share >= 0.5 else 0
        def add(arm, e):
            t, C, a300, fl = e; p = a300 / 1e4
            if m[4] - t < 3600: return
            won = 1 if fl & 2 else 0
            R.append(dict(e=f"{g}:{m[1]}", end=m[4], arm=arm, wk=dt.datetime.utcfromtimestamp(m[4]).strftime("%m-%d")[:4],
                          s=max(share, 1 - share), f=won - p - m[7] * p * (1 - p)))
        b = next((e for e in E[30:] if 7000 <= e[2] <= 9200), None)
        if b: add("BASE", b)
        if herd:
            h = next((e for e in E[30:] if (e[3] & 1) == maj and e[2] > 0), None)
            if h and 7000 <= h[2] <= 9200: add("HERD_B", h)
def stat(rr):
    ev = collections.defaultdict(lambda: [0.0, 0])
    for r in rr: ev[r["e"]][0] += r["f"]; ev[r["e"]][1] += 1
    E = list(ev.values())
    if len(E) < 3: return (len(E),)
    tot = lambda S: 100 * sum(s for s, _ in S) / sum(n for _, n in S)
    bs = sorted(tot([random.choice(E) for _ in E]) for _ in range(1000))
    return (round(tot(E), 2), len(E), [round(bs[25], 2), round(bs[975], 2)])
out = {a: stat([r for r in R if r["arm"] == a]) for a in ("BASE", "HERD_B")}
out["HERD_B share>=0.9"] = stat([r for r in R if r["arm"] == "HERD_B" and r["s"] >= 0.9])
out["BASE non-herd"] = stat([r for r in R if r["arm"] == "BASE" and r["s"] < 0.8])
for w in sorted({r["end"] // (14 * 86400) for r in R}):
    out[f"HERD_B fortnight {dt.datetime.utcfromtimestamp(w * 14 * 86400):%m-%d}"] = stat([r for r in R if r["arm"] == "HERD_B" and r["end"] // (14 * 86400) == w])
json.dump(out, open("data/research/herd_follow_check_report.json", "w"), indent=1)
for k, v in out.items(): print(k, v)
