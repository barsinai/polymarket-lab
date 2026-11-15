"""Cycle 20, N49 (outside the box, never touched): 2026 US midterm race markets AFTER election night.
Why the crowd could be wrong: once polls close, the answer is a public running count (county / SoS updates) plus known late-ballot
patterns (CA/WA/OR mail ballots late, AZ/NV late earlies); a race that is still open is priced by people anchored on the current margin.
Rules fixed before looking (12-week tape, resolved markets only): fills 0.03-0.97, points per share = win - price - fee, cluster = event
(race). Windows by fill time vs 2026-11-04 12:00 UTC (= after election night): pre (before 11-03 12 UTC), night (11-03 12 -> 11-04 12),
after (>= 11-04 12). Favourite 0.60-0.97 and long shot 0.03-0.20 in each. Dead if 'after' favourite on 10+ races is <= +1 pt or its
interval reaches below -2. CAVEAT: the tape ends 11-14 09:45, so only races resolved by then are in it (selection toward early calls)."""
import json, gzip, struct, collections, random, re, datetime as dt
ROW = struct.Struct("<IIIhfffHHHIB")
B = "data/research/"
random.seed(49)
P = re.compile(r"(house|senate|governor)-election-winner|-(house|senate|governor)-race|district")
T_NIGHT = dt.datetime(2026, 11, 3, 12, tzinfo=dt.timezone.utc).timestamp()
T_AFTER = dt.datetime(2026, 11, 4, 12, tzinfo=dt.timezone.utc).timestamp()
R = []; seen = set(); ev_end = {}
for g in "abc":
    meta = json.load(gzip.open(f"{B}entries_{g}_meta.json.gz")); MK = meta["markets"]
    idx = {i: m for i, m in enumerate(MK) if P.search(m[1]) and m[2] == "politics"}
    if not idx:
        continue
    blob = gzip.open(f"{B}entries_{g}.bin.gz").read()
    for t, mi, wi, hb, S, C, F, a, a60, a300, lag, fl in ROW.iter_unpack(blob):
        if mi not in idx or S <= 0 or C <= 0:
            continue
        m = idx[mi]; key = (m[0], t, wi, S, C)
        if key in seen:
            continue
        seen.add(key)
        R.append(dict(e=m[1], t=t, hb=hb, p=C / S, fee=F / S, win=1 if fl & 2 else 0, end=m[5]))
        ev_end[m[1]] = max(ev_end.get(m[1], 0), m[5])
    del blob
print("fills", len(R), "events", len(ev_end))
late = sorted(e for e, x in ev_end.items() if x >= T_AFTER + 86400)
print("events resolved >= 11-05 12 UTC:", len(late), late[:20])


def stat(rows):
    ev = collections.defaultdict(lambda: [0.0, 0])
    for r in rows:
        ev[r["e"]][0] += r["win"] - r["p"] - r["fee"]; ev[r["e"]][1] += 1
    v = list(ev.values()); n = sum(y[1] for y in v)
    o = {"n": n, "races": len(v), "pts": round(100 * sum(y[0] for y in v) / n, 2) if n else None,
         "avg_p": round(sum(r["p"] for r in rows) / n, 3) if n else None, "races_pos": sum(1 for y in v if y[0] > 0)}
    if len(v) >= 5:
        bs = []
        for _ in range(1000):
            s = [v[int(random.random() * len(v))] for _i in v]
            bs.append(sum(y[0] for y in s) / max(1, sum(y[1] for y in s)))
        bs.sort(); o["ci"] = [round(100 * bs[25], 1), round(100 * bs[974], 1)]
        o["pts_eq_per_race"] = round(100 * sum(y[0] / y[1] for y in v) / len(v), 2)
    return o


out = {}
for name, lo, hi in (("pre", 0, T_NIGHT), ("night", T_NIGHT, T_AFTER), ("after", T_AFTER, 2e9)):
    w = [r for r in R if lo <= r["t"] < hi]
    out[f"{name} fav 0.60-0.97"] = stat([r for r in w if 0.60 <= r["p"] <= 0.97])
    out[f"{name} mid 0.20-0.60"] = stat([r for r in w if 0.20 <= r["p"] < 0.60])
    out[f"{name} long 0.03-0.20"] = stat([r for r in w if 0.03 <= r["p"] < 0.20])
w = [r for r in R if r["t"] >= T_AFTER and 0.60 <= r["p"] <= 0.97]
out["after fav, races resolved >= 11-05 12 UTC"] = stat([r for r in w if ev_end[r["e"]] >= T_AFTER + 86400])
out["after fav 0.60-0.85"] = stat([r for r in w if r["p"] < 0.85])
out["after fav 0.85-0.97"] = stat([r for r in w if r["p"] >= 0.85])
print(json.dumps(out, indent=1))
json.dump(out, open(f"{B}election_late_report.json", "w"), indent=1)
