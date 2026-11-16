"""Cycle 22, two pre-registered tests on the 12-week public trade tape (rules fixed here before looking at outcomes).

N52 (outside the box): service-status / running-count markets on AI and dev services - 'ChatGPT outage by <date>', 'exactly N
  ChatGPT outages in <month>', 'Claude go down N times in <month>', 'GitHub longest critical incident', 'Codex weekly limit resets',
  'SpaceX launches in <month>'. Never touched. They resolve on public status pages / launch logs that anyone can read live (a
  running count), but the traders are AI fans who may over-price drama ('it will go down again', 'they will reset limits').
  If the count is mostly fixed and readable, the count-bucket favourite should be under-priced 6-168 h out.
N53 (adjacent to N43 gas / N45 leaderboards): Ornn GPU rental price index month-end buckets (H100 / H200 / B200 / A100 / RTX 5090).
  A slow, published index, priced by few traders; buckets are 25-50c wide while the index moves a few % a month.
Rules (both): taker entries on the side priced 0.60-0.97 by hours before end (6-24, 24-168, 6-168); points per share = win - price
  - fee; follower = the print 60 s later + fee; long shots (< 0.20) separately; older / newer 6 weeks by end date.
  Units: event = slug; also clustered by END DAY (one month-end or one week-end = one bet, lesson 6). Bootstrap 1,000 draws.
  Dead if the favourite at 6-168 h is <= +1 pt or the end-day-clustered interval reaches below -2, or < 6 end days.
  Data: entries_c (ai/tech group), real taker fills with fees, tape order = receive order."""
import json, gzip, struct, collections, random, re, datetime as dt
ROW = struct.Struct("<IIIhfffHHHIB")
B = "data/research/"
random.seed(52)
ST = re.compile(r"outage|go-down|codex-reset|resets-codex|github-critical|spacex-launches")
GPU = re.compile(r"gpu-rental")
meta = json.load(gzip.open(f"{B}entries_c_meta.json.gz")); MK = meta["markets"]
fam = {}
for i, m in enumerate(MK):
    if GPU.search(m[1]):
        fam[i] = "gpu"
    elif ST.search(m[1]):
        fam[i] = "status"
at = dt.datetime.strptime(meta["at"], "%Y-%m-%d %H:%M").replace(tzinfo=dt.timezone.utc).timestamp(); cut = at - 42 * 86400
R = []
blob = gzip.open(f"{B}entries_c.bin.gz").read()
for t, mi, wi, hb, S, C, F, a, a60, a300, lag, fl in ROW.iter_unpack(blob):
    if mi not in fam or S <= 0 or C <= 0:
        continue
    m = MK[mi]
    sub = re.sub(r"-(in|on|by|week|end|of)-.*$", "", m[1]) if fam[mi] == "status" else m[1].split("-end")[0]
    R.append(dict(f=fam[mi], e=m[1], sub=sub, day=int(m[4] // 86400), hb=hb, p=C / S, c=C, fee_ps=F / S, a60=a60 / 1e4,
                  win=1 if fl & 2 else 0, fr=m[7], new=m[4] >= cut))
del blob
print("entries", {k: (sum(1 for r in R if r["f"] == k), len({r["e"] for r in R if r["f"] == k}),
                      len({r["day"] for r in R if r["f"] == k})) for k in ("status", "gpu")})
print("status subfamilies", collections.Counter(r["sub"] for r in R if r["f"] == "status").most_common(20))


def stat(rows, follower=False, key="e"):
    ev = collections.defaultdict(lambda: [0.0, 0])
    for r in rows:
        if follower:
            p = r["a60"]
            if not (0.03 <= p <= 0.99):
                continue
            x = r["win"] - p - r["fr"] * p * (1 - p)
        else:
            x = r["win"] - r["p"] - r["fee_ps"]
        ev[r[key]][0] += x; ev[r[key]][1] += 1
    v = list(ev.values()); n = sum(y[1] for y in v)
    if len(v) < 5:
        return {"n": n, "units": len(v), "pts": round(100 * sum(y[0] for y in v) / n, 2) if n else None}
    bs = []
    for _ in range(1000):
        s = [v[int(random.random() * len(v))] for _i in v]
        bs.append(sum(y[0] for y in s) / max(1, sum(y[1] for y in s)))
    bs.sort()
    return {"n": n, "units": len(v), "pts": round(100 * sum(y[0] for y in v) / n, 2), "ci": [round(100 * bs[25], 1), round(100 * bs[974], 1)],
            "units_pos": sum(1 for y in v if y[0] > 0)}


out = {}
for f_ in ("status", "gpu"):
    F_ = [r for r in R if r["f"] == f_]
    for lo, hi in ((6, 24), (24, 168), (6, 168)):
        fav = [r for r in F_ if lo <= r["hb"] < hi and 0.60 <= r["p"] <= 0.97]
        out[f"{f_} FAV {lo}-{hi}h"] = stat(fav)
        out[f"{f_} FAV {lo}-{hi}h by end-day"] = stat(fav, key="day")
        out[f"{f_} FAV {lo}-{hi}h follower"] = stat(fav, True)
    fav = [r for r in F_ if 6 <= r["hb"] < 168 and 0.60 <= r["p"] <= 0.97]
    out[f"{f_} FAV 6-168h older6w"] = stat([r for r in fav if not r["new"]])
    out[f"{f_} FAV 6-168h newer6w"] = stat([r for r in fav if r["new"]])
    if f_ == "status":
        for s_ in sorted({r["sub"] for r in fav}):
            out[f"status FAV 6-168h sub {s_}"] = stat([r for r in fav if r["sub"] == s_])
    out[f"{f_} long shots < 0.20 (>= 6 h)"] = stat([r for r in F_ if r["p"] < 0.20 and r["hb"] >= 6])
    out[f"{f_} long shots < 0.20 by end-day"] = stat([r for r in F_ if r["p"] < 0.20 and r["hb"] >= 6], key="day")
    out[f"{f_} BIG >= $200"] = stat([r for r in F_ if r["c"] >= 200 and 0.05 <= r["p"] <= 0.95 and r["hb"] >= 1])
    out[f"{f_} SMALL < $10"] = stat([r for r in F_ if r["c"] < 10 and 0.05 <= r["p"] <= 0.95 and r["hb"] >= 1])
print(json.dumps(out, indent=1))
json.dump(out, open(f"{B}statuspage_report.json", "w"), indent=1)
