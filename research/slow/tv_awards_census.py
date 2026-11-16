"""Cycle 21, two pre-registered tests on the 12-week public trade tape (rules fixed here before looking at outcomes).

N50 (outside the box): reality-TV elimination / eviction markets (Big Brother evictions, Dancing with the Stars eliminations,
  America's Got Talent advances; NOT the 'what will be said during episode' mention family). Never touched.
  Why the crowd could be wrong: Big Brother's eviction vote is visible days early on the 24/7 live feeds and spoiler sites; DWTS /
  AGT are judged + voted shows where fans over-back their favourites. If outside information arrives early, the favourite should be
  under-priced 6-168 h out and large takers (>= $200) should win (lesson 17: where skill is paid, big takers win).
N51 (adjacent to N45, 'a public / pre-decided outcome priced by fans'): awards whose result is fixed before the ceremony (Ballon d'Or,
  Nobel, VMAs, Emmys and other award slugs in the tape). Favourite 0.60-0.97 at 1-24 h and 24-168 h before the end.
Rules (both): taker entries on the side priced 0.60-0.97 by hours before end (1-6, 6-24, 24-168); points per share = win - price - fee;
  follower = the print 60 s later + fee; large takers = cost >= $200, any price 0.05-0.95; older / newer 6 weeks.
  Units: event = slug; N51 also clustered by ceremony (slug prefix) because one night = one bet (lesson 6). Bootstrap 1,000 draws.
  Dead if the favourite at 6-168 h is <= +1 pt or its interval reaches below -2 (N50), or the ceremony-clustered interval reaches
  below 0 (N51). Data: entries_a (pop-culture / awards / music groups), real taker fills with fees, tape order = receive order."""
import json, gzip, struct, collections, random, re, datetime as dt
ROW = struct.Struct("<IIIhfffHHHIB")
B = "data/research/"
random.seed(50)
TV = re.compile(r"(evicted|eliminat|advances|winner).*?(big-brother|dancing|got-talent|survivor|traitors|bachelor|love-island|the-voice)|"
                r"(big-brother|dancing-with|got-talent|survivor|traitors|bachelor|love-island|the-voice).*(evict|elimin|advance|winner|win)")
AW = re.compile(r"emmy|vma|ballon|nobel|grammy|oscar|golden-globe|cma-|booker|pulitzer|-award")
meta = json.load(gzip.open(f"{B}entries_a_meta.json.gz")); MK = meta["markets"]
fam = {}
for i, m in enumerate(MK):
    s = m[1]
    if "what-will-be-said" in s:
        continue
    if TV.search(s):
        fam[i] = "tv"
    elif AW.search(s):
        fam[i] = "awards"
at = dt.datetime.strptime(meta["at"], "%Y-%m-%d %H:%M").replace(tzinfo=dt.timezone.utc).timestamp(); cut = at - 42 * 86400
R = []
blob = gzip.open(f"{B}entries_a.bin.gz").read()
for t, mi, wi, hb, S, C, F, a, a60, a300, lag, fl in ROW.iter_unpack(blob):
    if mi not in fam or S <= 0 or C <= 0:
        continue
    m = MK[mi]
    cer = re.sub(r"-(outstanding|mens|womens|winner|prize|voty|aoty|soty|bna|collab|pop|hiphop|rnb|alt|latin|kpop|dance|country|direction|artdirection|cinematography|editing|choreography|vfx|best|young|goalkeeper|coach|club).*$", "", m[1])
    cer = re.sub(r"-(chemistry|economics|physics|peace|literature|medicine)", "", cer)
    R.append(dict(f=fam[mi], e=m[1], cer=cer, hb=hb, p=C / S, c=C, fee_ps=F / S, a60=a60 / 1e4, win=1 if fl & 2 else 0, fr=m[7],
                  new=m[4] >= cut))
del blob
print("entries", {k: (sum(1 for r in R if r["f"] == k), len({r["e"] for r in R if r["f"] == k})) for k in ("tv", "awards")})
print("tv events", sorted({r["e"] for r in R if r["f"] == "tv"})[:40])


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
for f_ in ("tv", "awards"):
    F_ = [r for r in R if r["f"] == f_]
    for lo, hi in ((1, 6), (6, 24), (24, 168), (6, 168)):
        fav = [r for r in F_ if lo <= r["hb"] < hi and 0.60 <= r["p"] <= 0.97]
        out[f"{f_} FAV {lo}-{hi}h"] = stat(fav)
        out[f"{f_} FAV {lo}-{hi}h follower"] = stat(fav, True)
        if f_ == "awards":
            out[f"{f_} FAV {lo}-{hi}h by ceremony"] = stat(fav, key="cer")
    fav = [r for r in F_ if 6 <= r["hb"] < 168 and 0.60 <= r["p"] <= 0.97]
    out[f"{f_} FAV 6-168h older6w"] = stat([r for r in fav if not r["new"]])
    out[f"{f_} FAV 6-168h newer6w"] = stat([r for r in fav if r["new"]])
    big = [r for r in F_ if r["c"] >= 200 and 0.05 <= r["p"] <= 0.95 and r["hb"] >= 1]
    out[f"{f_} BIG >= $200"] = stat(big)
    out[f"{f_} BIG >= $200 follower"] = stat(big, True)
    if f_ == "awards":   # robustness added after seeing the event-level number (lesson 22): one ceremony = one bet
        out[f"{f_} BIG >= $200 follower by ceremony"] = stat(big, True, key="cer")
    small = [r for r in F_ if r["c"] < 10 and 0.05 <= r["p"] <= 0.95 and r["hb"] >= 1]
    out[f"{f_} SMALL < $10"] = stat(small)
    out[f"{f_} long shots < 0.20"] = stat([r for r in F_ if r["p"] < 0.20 and r["hb"] >= 1])
print("ceremonies", sorted({r["cer"] for r in R if r["f"] == "awards"}))
print(json.dumps(out, indent=1))
json.dump(out, open(f"{B}tv_awards_report.json", "w"), indent=1)
