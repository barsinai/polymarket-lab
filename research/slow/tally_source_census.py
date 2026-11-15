"""N41 (cycle 16, outside the box): markets that resolve on a slow public data release we could read earlier - never tested before.
Families (fixed before looking at any outcome): ship transits through Hormuz / Bab el-Mandeb (resolve on published daily transit counts),
US Drought Monitor (state D4 / ag-commodity drought share, weekly Thursday map), and measles / flu-hospitalisation counts (CDC weekly).
Why the crowd could be wrong: the counts are released with a lag and in a format few traders read; the books are thin.
Rule (same as N39, pre-registered): taker entries on the favourite side 0.60-0.97, by hours before end (1-6, 6-24, 24-168, 168-720);
points per share = win - price - fee; the follower at the print 60 s later (a60) + fee; event-clustered bootstrap; older / newer 6 weeks.
Data: 12-week public trade tape (entries_b weather group, entries_c economy/geopolitics), real fills with fees."""
import json, gzip, struct, collections, random, re, datetime as dt
ROW = struct.Struct("<IIIhfffHHHIB")
B = "data/research/"
random.seed(41)
FAM = {"ships": re.compile(r"ships-transit|transit-the-strait|bab-el-mandeb"),
       "drought": re.compile(r"drought"),
       "cdc_counts": re.compile(r"measles|flu-hospital")}
R = []
for g in "abc":
    meta = json.load(gzip.open(f"{B}entries_{g}_meta.json.gz")); MK = meta["markets"]
    fam = {}
    for i, m in enumerate(MK):
        for k, p in FAM.items():
            if p.search(m[1]):
                fam[i] = k
    if not fam:
        continue
    at = dt.datetime.strptime(meta["at"], "%Y-%m-%d %H:%M").replace(tzinfo=dt.timezone.utc).timestamp(); cut = at - 42 * 86400
    blob = gzip.open(f"{B}entries_{g}.bin.gz").read()
    for t, mi, wi, hb, S, C, F, a, a60, a300, lag, fl in ROW.iter_unpack(blob):
        if mi not in fam or S <= 0 or C <= 0:
            continue
        m = MK[mi]
        R.append(dict(f=fam[mi], e=m[1], q=m[3], hb=hb, p=C / S, fee_ps=F / S, a60=a60 / 1e4, win=1 if fl & 2 else 0, fr=m[7],
                      new=m[4] >= cut, usd=C))
print("entries", len(R), {k: (sum(1 for r in R if r["f"] == k), len({r["e"] for r in R if r["f"] == k})) for k in FAM})


def stat(rows, follower=False):
    ev = collections.defaultdict(lambda: [0.0, 0])
    for r in rows:
        if follower:
            p = r["a60"]
            if not (0.03 <= p <= 0.99):
                continue
            x = r["win"] - p - r["fr"] * p * (1 - p)
        else:
            x = r["win"] - r["p"] - r["fee_ps"]
        ev[r["e"]][0] += x; ev[r["e"]][1] += 1
    v = list(ev.values()); n = sum(y[1] for y in v)
    if len(v) < 5:
        return {"n": n, "events": len(v)}
    bs = []
    for _ in range(1000):
        s = [v[int(random.random() * len(v))] for _i in v]
        bs.append(sum(y[0] for y in s) / max(1, sum(y[1] for y in s)))
    bs.sort()
    return {"n": n, "events": len(v), "pts": round(100 * sum(y[0] for y in v) / n, 2), "ci": [round(100 * bs[25], 1), round(100 * bs[974], 1)],
            "pts_per_event_eq": round(100 * sum(y[0] / y[1] for y in v) / len(v), 2), "events_pos": sum(1 for y in v if y[0] > 0)}


out = {}
for fam in list(FAM) + ["ALL"]:
    F_ = [r for r in R if fam == "ALL" or r["f"] == fam]
    for lo, hi in ((1, 6), (6, 24), (24, 168), (168, 720)):
        fav = [r for r in F_ if lo <= r["hb"] < hi and 0.60 <= r["p"] <= 0.97]
        out[f"{fam} FAV {lo}-{hi}h"] = stat(fav)
        out[f"{fam} FAV {lo}-{hi}h follower"] = stat(fav, True)
    fav = [r for r in F_ if 6 <= r["hb"] < 168 and 0.60 <= r["p"] <= 0.97]
    out[f"{fam} FAV 6-168h older6w"] = stat([r for r in fav if not r["new"]])
    out[f"{fam} FAV 6-168h newer6w"] = stat([r for r in fav if r["new"]])
    for lo, hi in ((0.03, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 0.97), (0.97, 1.0)):
        rows = [r for r in F_ if 1 <= r["hb"] < 168 and lo <= r["p"] < hi]
        out[f"{fam} band {lo}-{hi} 1-168h"] = dict(stat(rows), avg_p=round(sum(r["p"] for r in rows) / len(rows), 3) if rows else None,
                                                   won=round(sum(r["win"] for r in rows) / len(rows), 3) if rows else None)
for k, v in out.items():
    print(f"{k:42} {v}")
json.dump(out, open(B + "tally_source_report.json", "w"), indent=1)
