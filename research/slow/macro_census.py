"""Cycle 23, two pre-registered tests on the 12-week public trade tape (rules fixed here before looking at outcomes).

N54 (outside the box): scheduled US macro release buckets - CPI MoM / annual, core CPI YoY, PPI YoY, ISM manufacturing / services
  PMI, unemployment rate, UMich sentiment, price of a dozen eggs. Never touched (backlog item 4 since 11-01). Why the crowd could be
  wrong: the buckets are 0.1-wide, the consensus and the Cleveland Fed nowcast are public and tight, and fans may spread money over
  'surprise' buckets. Exposed to 13 (consensus is public -> already in the price), 5 (one release = one bet; ~3 months), 6.
N55 (adjacent to N17 touch-YES-rich / the options model): 'How high / how low will the N-year Treasury yield go in <month>' touch
  ladders. N17 found touch YES rich on last prices, but the stock-touch NO spread (+13c) ate it; Treasury ladders may have tighter
  books and a deep underlying. Exposed to 6 (all rungs of a month are one bet on the yield path), 11 (path questions settle YES
  early - here we use only finished months), 5.
Rules (both): taker entries; points per share = win - price - fee; follower = the print 60 s later + fee.
  N54: side priced 0.60-0.97 at 6-24 / 24-168 / 6-168 h before end; long shots < 0.20; big >= $200 vs small < $10. Unit = release
  (event slug); dead if FAV 6-168 h <= +1 pt, or its release-clustered interval reaches below -2, or < 8 releases.
  N55: NO side priced 0.60-0.97 (= YES touch 0.03-0.40) at >= 24 h before end, and YES long shots < 0.20; unit = month (all tenors
  and directions of one month = one bet); dead if NO-fav <= +1 pt or < 4 months or its month interval reaches below -2.
  Data: entries_c (economy), real taker fills with fees, tape order = receive order; only markets that ended before the tape cut."""
import json, gzip, struct, collections, random, re, datetime as dt
ROW = struct.Struct("<IIIhfffHHHIB")
B = "data/research/"
random.seed(54)
MAC = re.compile(r"inflation-us|core-cpi|ppi-yoy|ism-(manufacturing|services)-pmi|unemployment-rate|consumer-sentimen|dozen-eggs")
TY = re.compile(r"treasury-yield")
meta = json.load(gzip.open(f"{B}entries_c_meta.json.gz")); MK = meta["markets"]
at = dt.datetime.strptime(meta["at"], "%Y-%m-%d %H:%M").replace(tzinfo=dt.timezone.utc).timestamp(); cut = at - 42 * 86400
fam = {}
for i, m in enumerate(MK):
    if m[4] >= at:
        continue
    if TY.search(m[1]):
        fam[i] = "yield"
    elif MAC.search(m[1]):
        fam[i] = "macro"


def series(slug):
    for k in ("core-cpi", "inflation-us-monthly", "inflation-us-annual", "ppi", "ism-manufacturing", "ism-services", "unemployment",
              "consumer-sentimen", "eggs"):
        if k in slug:
            return k
    return "other"


R = []
blob = gzip.open(f"{B}entries_c.bin.gz").read()
for t, mi, wi, hb, S, C, F, a, a60, a300, lag, fl in ROW.iter_unpack(blob):
    if mi not in fam or S <= 0 or C <= 0:
        continue
    m = MK[mi]
    mon = dt.datetime.fromtimestamp(m[4], dt.timezone.utc).strftime("%Y-%m")
    q = (m[3] or "").lower()
    R.append(dict(f=fam[mi], e=m[1], ser=series(m[1]), mon=mon, hb=hb, p=C / S, c=C, fee_ps=F / S, a60=a60 / 1e4, win=1 if fl & 2 else 0,
                  fr=m[7], new=m[4] >= cut, wi=wi, dirn=("high" if "how-high" in m[1] else "low"), yes=None))
del blob
print("entries", {k: (sum(1 for r in R if r["f"] == k), len({r["e"] for r in R if r["f"] == k})) for k in ("macro", "yield")})
print("macro series", collections.Counter((r["ser"]) for r in R if r["f"] == "macro").most_common())
print("yield months", collections.Counter((r["mon"], r["dirn"]) for r in R if r["f"] == "yield").most_common())


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
    if len(v) < 4:
        return {"n": n, "units": len(v), "pts": round(100 * sum(y[0] for y in v) / n, 2) if n else None}
    bs = []
    for _ in range(1000):
        s = [v[int(random.random() * len(v))] for _i in v]
        bs.append(sum(y[0] for y in s) / max(1, sum(y[1] for y in s)))
    bs.sort()
    return {"n": n, "units": len(v), "pts": round(100 * sum(y[0] for y in v) / n, 2), "ci": [round(100 * bs[25], 1), round(100 * bs[974], 1)],
            "units_pos": sum(1 for y in v if y[0] > 0)}


out = {}
M = [r for r in R if r["f"] == "macro"]
for lo, hi in ((6, 24), (24, 168), (6, 168)):
    fav = [r for r in M if lo <= r["hb"] < hi and 0.60 <= r["p"] <= 0.97]
    out[f"macro FAV {lo}-{hi}h by release"] = stat(fav)
    out[f"macro FAV {lo}-{hi}h follower"] = stat(fav, True)
fav = [r for r in M if 6 <= r["hb"] < 168 and 0.60 <= r["p"] <= 0.97]
out["macro FAV 6-168h by month"] = stat(fav, key="mon")
out["macro FAV 6-168h older6w"] = stat([r for r in fav if not r["new"]])
out["macro FAV 6-168h newer6w"] = stat([r for r in fav if r["new"]])
for s_ in sorted({r["ser"] for r in fav}):
    out[f"macro FAV 6-168h ser {s_}"] = stat([r for r in fav if r["ser"] == s_])
out["macro long shots < 0.20 (>= 6 h)"] = stat([r for r in M if r["p"] < 0.20 and r["hb"] >= 6])
out["macro mid 0.20-0.60 (>= 6 h)"] = stat([r for r in M if 0.20 <= r["p"] < 0.60 and r["hb"] >= 6])
out["macro after release (hb < 6)"] = stat([r for r in M if r["hb"] < 6 and 0.05 <= r["p"] <= 0.97])
out["macro BIG >= $200"] = stat([r for r in M if r["c"] >= 200 and 0.05 <= r["p"] <= 0.95 and r["hb"] >= 1])
out["macro SMALL < $10"] = stat([r for r in M if r["c"] < 10 and 0.05 <= r["p"] <= 0.95 and r["hb"] >= 1])
Y = [r for r in R if r["f"] == "yield"]
# outcome index wi: the tape stores which side the taker bought; price p is that side's price, so 'favourite' = p in band
nofav = [r for r in Y if r["hb"] >= 24 and 0.60 <= r["p"] <= 0.97]
out["yield FAV >= 24h by event"] = stat(nofav)
out["yield FAV >= 24h by month"] = stat(nofav, key="mon")
out["yield FAV >= 24h follower"] = stat(nofav, True)
out["yield FAV >= 24h older6w"] = stat([r for r in nofav if not r["new"]])
out["yield FAV >= 24h newer6w"] = stat([r for r in nofav if r["new"]])
out["yield long shots < 0.20 >= 24h by event"] = stat([r for r in Y if r["hb"] >= 24 and r["p"] < 0.20])
out["yield long shots < 0.20 >= 24h by month"] = stat([r for r in Y if r["hb"] >= 24 and r["p"] < 0.20], key="mon")
out["yield BIG >= $200"] = stat([r for r in Y if r["c"] >= 200 and 0.05 <= r["p"] <= 0.95 and r["hb"] >= 1])
out["yield SMALL < $10"] = stat([r for r in Y if r["c"] < 10 and 0.05 <= r["p"] <= 0.95 and r["hb"] >= 1])
print(json.dumps(out, indent=1))
json.dump(out, open(f"{B}macro_report.json", "w"), indent=1)
