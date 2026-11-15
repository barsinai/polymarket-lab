"""N39 (cycle 15, outside the box): central-bank decision markets vs the economists' consensus.
Polymarket lists 'Bank of X decision in <month>' (no change / cut 25 / cut 50+ / hike) for ~15 central banks. Outside the Fed/ECB the books
are thin, while the outcome is usually telegraphed (forward guidance, Reuters/Bloomberg polls are right ~85-90% of the time). If the crowd
leaves the consensus bucket under-priced 1-7 days out, buying it at the real ask should pay. Rule fixed before looking: favourite side
priced 0.60-0.97 by real taker fills 24-168 h before the scheduled end; also the follower at the print 60 s later (a60) + fee.
Unit = equal weight per entry, points per share; independent events = meetings (event slug); event-clustered bootstrap; split
majors (Fed / ECB / BoE / BoJ) vs the rest and older / newer 6 weeks. Data: 12-week public trade tape (entries_c, real fills, fees)."""
import json, gzip, struct, collections, random, re, datetime as dt
ROW = struct.Struct("<IIIhfffHHHIB")
B = "data/research/"
random.seed(39)
pat = re.compile(r"-decision-in-|ecb-interest-rates|fed-decisions")
major = re.compile(r"fed-decisions|ecb-|bank-of-england|bank-of-japan")
R = []
for g in "abc":
    meta = json.load(gzip.open(f"{B}entries_{g}_meta.json.gz")); MK = meta["markets"]
    idx = {i for i, m in enumerate(MK) if pat.search(m[1])}
    if not idx:
        continue
    at = dt.datetime.strptime(meta["at"], "%Y-%m-%d %H:%M").replace(tzinfo=dt.timezone.utc).timestamp(); cut = at - 45 * 86400
    blob = gzip.open(f"{B}entries_{g}.bin.gz").read()
    for t, mi, wi, hb, S, C, F, a, a60, a300, lag, fl in ROW.iter_unpack(blob):
        if mi not in idx or S <= 0 or C <= 0:
            continue
        m = MK[mi]
        R.append(dict(e=m[1], q=m[3], hb=hb, p=C / S, fee_ps=F / S, a60=a60 / 1e4, win=1 if fl & 2 else 0, fr=m[7],
                      new=m[4] >= cut, maj=bool(major.search(m[1]))))
print("entries", len(R), "events", len({r["e"] for r in R}), "markets", len({r["q"] for r in R}))


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
    # equal weight per EVENT as a robustness check
    pe = sum(y[0] / y[1] for y in v) / len(v)
    return {"n": n, "events": len(v), "pts": round(100 * sum(y[0] for y in v) / n, 2), "ci": [round(100 * bs[25], 1), round(100 * bs[974], 1)],
            "pts_per_event_eq": round(100 * pe, 2), "events_pos": sum(1 for y in v if y[0] > 0)}


out = {}
W = [r for r in R if 24 <= r["hb"] <= 168]
fav = [r for r in W if 0.60 <= r["p"] <= 0.97]
for name, f in (("all", lambda r: True), ("majors", lambda r: r["maj"]), ("others", lambda r: not r["maj"]),
                ("older6w", lambda r: not r["new"]), ("newer6w", lambda r: r["new"])):
    out[f"FAV 0.60-0.97 24-168h | {name}"] = stat([r for r in fav if f(r)])
    out[f"FAV 0.60-0.97 24-168h | {name} | follower a60"] = stat([r for r in fav if f(r)], True)
for lo, hi in ((0.03, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 0.9), (0.9, 0.97), (0.97, 1.0)):
    rows = [r for r in W if lo <= r["p"] < hi]
    out[f"band {lo}-{hi} 24-168h (taker pts)"] = dict(stat(rows), avg_p=round(sum(r["p"] for r in rows) / len(rows), 3) if rows else None,
                                                     won=round(sum(r["win"] for r in rows) / len(rows), 3) if rows else None)
for lo, hi in ((168, 720), (6, 24), (1, 6)):
    out[f"FAV 0.60-0.97 {lo}-{hi}h"] = stat([r for r in R if lo <= r["hb"] < hi and 0.60 <= r["p"] <= 0.97])
for k, v in out.items():
    print(f"{k:52} {v}")
json.dump(out, open(B + "cb_decision_report.json", "w"), indent=1)
