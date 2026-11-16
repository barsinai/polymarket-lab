"""Cycle 26, N60 (adjacent to N58): does culture launch-hour NO survive OUR latency?

N58 (+7.4 pts per market, follower = next NO print by someone else >= 60 s later) was found by looking (LESSONS 22). A forward
tracker that polls new listings every ~10 min cannot act 60 s after a print. Rules fixed here BEFORE looking:
  same rows as launch_census.py (group a culture, entries >= 1 h before end, market lives >= 24 h after its first trade L),
  NO-side taker entries in the launch hour, ONE fill per market (the first qualifying entry), follower price in 0.05-0.90
  (the tracker's ask cap), fee = rate * p(1-p).
  Arms: F60 = next NO print >= 60 s later (N58 as found), F300 = next NO print >= 300 s later (closer to a 10-min poller);
  and by the entry's age since L: 0-10 min, 10-30, 30-60 (a tracker that sees a listing late gets the later rows).
DEAD for the forward tracker if F300 <= +1 pt or its event interval reaches below -1, or the halves of F300 disagree in sign.
Unit = event slug (bootstrap 1,000); halves by L."""
import json, gzip, struct, collections, random, datetime as dt
ROW = struct.Struct("<IIIhfffHHHIB")
B = "data/research/"
random.seed(60)
meta = json.load(gzip.open(f"{B}entries_a_meta.json.gz")); MK = meta["markets"]
at = dt.datetime.strptime(meta["at"], "%Y-%m-%d %H:%M").replace(tzinfo=dt.timezone.utc).timestamp()
blob = gzip.open(f"{B}entries_a.bin.gz").read()
L = {}
for t, mi, *_ in ROW.iter_unpack(blob):
    if mi not in L or t < L[mi]:
        L[mi] = t
rows = sorted(ROW.iter_unpack(blob))
del blob
first = {}
for t, mi, wi, hb, S, C, F, a, a60, a300, lag, fl in rows:
    m = MK[mi]; l0 = L[mi]
    if m[4] >= at or S <= 0 or C <= 0 or hb < 1 or m[4] - l0 < 24 * 3600 or fl & 1:   # fl&1 = YES direction
        continue
    age = t - l0
    if age >= 3600 or mi in first:
        continue
    win = 1 if fl & 2 else 0; fee = m[7]
    def f(p):
        p /= 1e4
        return win - p - fee * p * (1 - p) if 0.05 <= p <= 0.90 else None
    first[mi] = dict(e=m[1], cat=m[2], l0=l0, age=age, f60=f(a60), f300=f(a300), d300=(a300 - a60) / 1e4 if a60 and a300 else None)
R = list(first.values())
mid = sorted(r["l0"] for r in R)[len(R) // 2]


def stat(rr, k):
    ev = collections.defaultdict(lambda: [0.0, 0])
    for r in rr:
        if r[k] is not None:
            ev[r["e"]][0] += r[k]; ev[r["e"]][1] += 1
    v = list(ev.values()); n = sum(y[1] for y in v)
    if len(v) < 5:
        return {"n": n, "events": len(v)}
    bs = []
    for _ in range(1000):
        s = [v[int(random.random() * len(v))] for _i in v]
        bs.append(sum(y[0] for y in s) / max(1, sum(y[1] for y in s)))
    bs.sort()
    return {"n": n, "events": len(v), "pts": round(100 * sum(y[0] for y in v) / n, 2), "ci": [round(100 * bs[25], 1), round(100 * bs[974], 1)]}


out = {"markets": len(R)}
for k in ("f60", "f300"):
    out[k] = stat(R, k)
    out[k + " older"] = stat([r for r in R if r["l0"] < mid], k)
    out[k + " newer"] = stat([r for r in R if r["l0"] >= mid], k)
    out[k + " non-mention"] = stat([r for r in R if r["cat"] != "mention"], k)
    for lo, hi in ((0, 600), (600, 1800), (1800, 3600)):
        out[f"{k} age {lo // 60}-{hi // 60} min"] = stat([r for r in R if lo <= r["age"] < hi], k)
d = [r["d300"] for r in R if r["d300"] is not None]
out["NO price drift 60 s -> 300 s (c, median)"] = round(100 * sorted(d)[len(d) // 2], 2) if d else None
print(json.dumps(out, indent=1))
json.dump(out, open(f"{B}launch_latency_report.json", "w"), indent=1)
