"""Cycle 19, two pre-registered tests on the 12-week public trade tape (rules fixed here before looking at outcomes).

N46 (adjacent to N45 AI-leaderboard favourites): month-end RANK markets on other continuously public numbers - 'largest / 2nd / 3rd
  largest company end of <month>' (market caps, live), 'best / second / third Chinese AI company end of <month>' (LMArena), 'top Spotify
  artist in <month>' (Spotify charts). Why: the same mechanism as N45 - the ranking is public and rarely flips late, the books are thin.
  Rule (= N45): favourite side 0.60-0.97 taker entries by hours before end; points per share = win - price - fee; follower = print 60 s
  later + fee; halves. Dead if FAV 6-168 h <= +1 pt or its interval reaches below -2.
N47 (outside the box, never touched): daily city weather-EVENT binaries - 'Which cities face tornado risk on <date>' (resolves on the NOAA
  Storm Prediction Center convective outlook, published several times a day and 1-3 days ahead) and 'Where will it rain on <date>'
  (city precipitation). Why the crowd could be wrong: the resolving product (SPC outlook / NWS PoP) is public before the end, the books
  are thin multi-city lists that few people re-price, and YES long shots on dramatic weather may be over-bought.
  Rules: A favourite 0.60-0.97 by hours before end (1-6, 6-24, 24-72); B price bands 1-72 h (calibration); C YES vs NO favourite side.
  Event = date slug (all cities of one date are one weather system, LESSONS 6). Dead if no A bucket with 10+ events is >= +2 pts with
  the interval above 0 AND B shows no band off by >= 5 pts on 10+ events.
Data: entries_a/b/c (real taker fills with fees, tape order = receive order of the prints). Event-clustered bootstrap, 1,000 draws."""
import json, gzip, struct, collections, random, re, datetime as dt
ROW = struct.Struct("<IIIhfffHHHIB")
B = "data/research/"
random.seed(47)
FAM = {"largest_company": re.compile(r"largest-company"),
       "chinese_ai": re.compile(r"best-chinese-ai"),
       "spotify_artist": re.compile(r"top-spotify-artist"),
       "tornado": re.compile(r"tornado-risk"),
       "rain": re.compile(r"where-will-it-rain")}
R = []; seen = set()
for g in "abc":
    meta = json.load(gzip.open(f"{B}entries_{g}_meta.json.gz")); MK = meta["markets"]
    fam = {}
    for i, m in enumerate(MK):
        for k, p in FAM.items():
            if p.search(m[1]):
                fam[i] = k; break
    if not fam:
        continue
    at = dt.datetime.strptime(meta["at"], "%Y-%m-%d %H:%M").replace(tzinfo=dt.timezone.utc).timestamp(); cut = at - 42 * 86400
    blob = gzip.open(f"{B}entries_{g}.bin.gz").read()
    for t, mi, wi, hb, S, C, F, a, a60, a300, lag, fl in ROW.iter_unpack(blob):
        if mi not in fam or S <= 0 or C <= 0:
            continue
        m = MK[mi]
        key = (m[0], t, wi, S, C)
        if key in seen:
            continue
        seen.add(key)
        R.append(dict(f=fam[mi], e=m[1], q=m[3], hb=hb, p=C / S, fee_ps=F / S, a60=a60 / 1e4, win=1 if fl & 2 else 0, fr=m[7],
                      new=m[4] >= cut, yes=bool(fl & 1), t=t))
    del blob
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
        return {"n": n, "events": len(v), "pts": round(100 * sum(y[0] for y in v) / n, 2) if n else None}
    bs = []
    for _ in range(1000):
        s = [v[int(random.random() * len(v))] for _i in v]
        bs.append(sum(y[0] for y in s) / max(1, sum(y[1] for y in s)))
    bs.sort()
    return {"n": n, "events": len(v), "pts": round(100 * sum(y[0] for y in v) / n, 2), "ci": [round(100 * bs[25], 1), round(100 * bs[974], 1)],
            "pts_per_event_eq": round(100 * sum(y[0] / y[1] for y in v) / len(v), 2), "events_pos": sum(1 for y in v if y[0] > 0)}


out = {}
for fam in FAM:
    F_ = [r for r in R if r["f"] == fam]
    hbs = ((1, 6), (6, 24), (24, 72)) if fam in ("tornado", "rain") else ((1, 6), (6, 24), (24, 168), (168, 720))
    for lo, hi in hbs:
        fav = [r for r in F_ if lo <= r["hb"] < hi and 0.60 <= r["p"] <= 0.97]
        out[f"{fam} FAV {lo}-{hi}h"] = stat(fav)
        out[f"{fam} FAV {lo}-{hi}h follower"] = stat(fav, True)
    top = 72 if fam in ("tornado", "rain") else 168
    fav = [r for r in F_ if 6 <= r["hb"] < top and 0.60 <= r["p"] <= 0.97]
    out[f"{fam} FAV 6-{top}h all"] = stat(fav)
    out[f"{fam} FAV 6-{top}h older6w"] = stat([r for r in fav if not r["new"]])
    out[f"{fam} FAV 6-{top}h newer6w"] = stat([r for r in fav if r["new"]])
    if fam in ("tornado", "rain"):
        fv = [r for r in F_ if 1 <= r["hb"] < 72 and 0.60 <= r["p"] <= 0.97]
        out[f"{fam} C FAV 1-72h YES side"] = stat([r for r in fv if r["yes"]])
        out[f"{fam} C FAV 1-72h NO side"] = stat([r for r in fv if not r["yes"]])
    for lo, hi in ((0.03, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 0.97)):
        rows = [r for r in F_ if 1 <= r["hb"] < top and lo <= r["p"] < hi]
        out[f"{fam} band {lo}-{hi} 1-{top}h"] = dict(stat(rows), avg_p=round(sum(r["p"] for r in rows) / len(rows), 3) if rows else None,
                                                    won=round(sum(r["win"] for r in rows) / len(rows), 3) if rows else None)
for k, v in out.items():
    print(f"{k:40} {v}")
json.dump(out, open(B + "riskday_report.json", "w"), indent=1)
