"""Cycle 18, two pre-registered tests on the 12-week public trade tape (rules fixed in this docstring before looking at outcomes).

N45 (outside the box): AI-leaderboard markets - never touched. 'Which company has the best AI model / text / code / webdev / image /
  video model end of <week|month>' (LMArena leaderboard) and 'Top / 2nd / 3rd AI lab by OpenRouter market share week of ...'.
  Why the crowd could be wrong: the resolving page is public and updates continuously, the leader rarely changes inside a week, yet
  the books are thin and priced by AI fans who over-weight 'a new model drops this week' -> the current leader (favourite) may be
  under-priced late; and the 2nd/3rd-place markets get less attention than the 'top' market.
  Rules: A taker entries on the favourite side 0.60-0.97 by hours before end (1-6, 6-24, 24-168, 168-720); points per share =
  win - price - fee; follower = print 60 s later + fee; older / newer 6 weeks; B same A rule split 'top' vs '2nd/3rd' markets.
N44 (adjacent, replication of the one half-worked tape result, N41 ship transits: favourite 6-24 h out +11.1 pts [-0.8, +18.8]):
  is 'favourite of a weekly count-bucket market 6-24 h before end' a general effect? Family: tweet / post count buckets (Elon, Trump,
  White House, CZ, Khamenei, Ted Cruz ... '# of tweets' and 'what will X post this week'), whose tracker counts are public.
  Rule: exactly the N41 rule. Dead if the 6-24 h favourite is <= +1 pt or its interval reaches below -2.
Units: event = slug (one week / one date). Event-clustered bootstrap, 1,000 draws.
Data: entries_a/b/c (real taker fills with fees, tape order = receive order of the prints)."""
import json, gzip, struct, collections, random, re, datetime as dt
ROW = struct.Struct("<IIIhfffHHHIB")
B = "data/research/"
random.seed(45)
FAM = {"lmarena": re.compile(r"best-ai-model|text-arena|code-arena|webdev|text-to-image|text-to-video|best-ai-agent|vision-arena"),
       "openrouter": re.compile(r"openrouter"),
       "tweet_counts": re.compile(r"of-tweets|-post-this-week")}
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
        key = (m[0], t, wi, S, C)                      # the same market can sit in two groups
        if key in seen:
            continue
        seen.add(key)
        R.append(dict(f=fam[mi], e=m[1], q=m[3], hb=hb, p=C / S, fee_ps=F / S, a60=a60 / 1e4, win=1 if fl & 2 else 0, fr=m[7],
                      new=m[4] >= cut, rank2=bool(re.match(r"(second|third|2nd|3rd)", m[1]))))
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
for fam in list(FAM):
    F_ = [r for r in R if r["f"] == fam]
    for lo, hi in ((1, 6), (6, 24), (24, 168), (168, 720)):
        fav = [r for r in F_ if lo <= r["hb"] < hi and 0.60 <= r["p"] <= 0.97]
        out[f"{fam} FAV {lo}-{hi}h"] = stat(fav)
        out[f"{fam} FAV {lo}-{hi}h follower"] = stat(fav, True)
    fav = [r for r in F_ if 6 <= r["hb"] < 168 and 0.60 <= r["p"] <= 0.97]
    out[f"{fam} FAV 6-168h older6w"] = stat([r for r in fav if not r["new"]])
    out[f"{fam} FAV 6-168h newer6w"] = stat([r for r in fav if r["new"]])
    if fam == "tweet_counts":
        f2 = [r for r in F_ if 6 <= r["hb"] < 24 and 0.60 <= r["p"] <= 0.97]
        out[f"{fam} FAV 6-24h older6w"] = stat([r for r in f2 if not r["new"]])
        out[f"{fam} FAV 6-24h newer6w"] = stat([r for r in f2 if r["new"]])
    for lo, hi in ((0.03, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 0.97)):
        rows = [r for r in F_ if 1 <= r["hb"] < 168 and lo <= r["p"] < hi]
        out[f"{fam} band {lo}-{hi} 1-168h"] = dict(stat(rows), avg_p=round(sum(r["p"] for r in rows) / len(rows), 3) if rows else None,
                                                   won=round(sum(r["win"] for r in rows) / len(rows), 3) if rows else None)
lm = [r for r in R if r["f"] in ("lmarena", "openrouter") and 6 <= r["hb"] < 168 and 0.60 <= r["p"] <= 0.97]
out["B leaderboards FAV 6-168h top"] = stat([r for r in lm if not r["rank2"]])
out["B leaderboards FAV 6-168h 2nd/3rd"] = stat([r for r in lm if r["rank2"]])
for k, v in out.items():
    print(f"{k:44} {v}")
json.dump(out, open(B + "leaderboard_report.json", "w"), indent=1)
