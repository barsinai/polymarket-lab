"""Cycle 44, N96 (outside the box, never touched: the LANGUAGE of the news that resolves a market). Politics markets about non-English-
speaking countries (elections, leaders, coalitions, cabinet votes in Germany, Japan, Brazil, Poland, Chile ...) are traded by an English-
speaking crowd that reads translated headlines hours late; whoever reads the local press / local polls / local electoral commission first
should show up on the tape as BIG takers who win more there than in US / UK politics. If so, following big takers there (COPY-1 style, at
the follower fill) is a lead the lab has never had; if not, the 'local-language edge' is priced like any other.
Rules fixed BEFORE looking. Tape group c, category politics, finished markets. Class by keywords in question + slug: LOCAL (a non-English-
speaking country, its leader or party), ANGLO (UK, Canada, Australia, Ireland, New Zealand), else US/OTHER. Rows: taker entries with cost
>= $200 (lesson 17's informed bucket), first such entry per market and side, follower fill a300 (next print the same way >= 300 s later),
0.05-0.95, fee = rate * p(1-p). Unit = event slug, bootstrap 1,000; halves by end date. Printed also: all entries (any size) first per
market+side, both sides, to see whether LOCAL markets are mispriced in general (no decision on that).
DECISION: PASS (-> COPY-1 'local' read-out arm) if LOCAL big-follower >= +3 pts, CI low > 0, >= 30 events, both halves > 0 and LOCAL - US
>= +2. Otherwise DEAD. Exposed to 22 (big-taker rules died on all events), 24, 5/6 (one election = many markets), 27, 13."""
import json, gzip, struct, collections, random, re, datetime as dt
ROW = struct.Struct("<IIIhfffHHHIB")
B = "data/research/"
random.seed(96)
LOCAL = r"german|germany|merz|afd|bundestag|france|french|macron|le pen|bardella|japan|japanese|takaichi|ldp|korea|korean|brazil|lula|" \
        r"bolsonaro|mexico|mexican|sheinbaum|argentin|milei|chile|chilean|kast|jara|colombia|peru|peruvian|ecuador|noboa|venezuela|maduro|" \
        r"machado|bolivia|poland|polish|nawrocki|tusk|hungar|orban|magyar|czech|babis|romania|portugal|portuguese|spain|spanish|s[aá]nchez|" \
        r"italy|italian|meloni|netherlands|dutch|belgi|sweden|swedish|norway|norwegian|denmark|danish|finland|finnish|austria|switzerland|" \
        r"turkey|turkish|erdogan|iran|israel|netanyahu|knesset|thailand|thai|indonesia|philippine|vietnam|taiwan|china|chinese|russia|putin|" \
        r"ukrain|zelensk|moldova|serbia|bulgaria|greece|greek|egypt|morocco|saudi|pakistan|bangladesh|nepal|honduras|costa rica|guatemala|" \
        r"el salvador|bukele|haiti|cuba|paraguay|uruguay|slovak|slovenia|croatia|lithuania|latvia|estonia|kosovo|albania|bosnia|iraq|" \
        r"lebanon|syria|kenya|nigeria|ethiopia|tanzania|cameroon|ivory coast|c[oô]te d|senegal|georgian dream|armenia|azerbaijan|kazakh|tokyo|seoul"
ANGLO = r"\buk\b|britain|british|starmer|farage|reform uk|labour|tory|tories|conservative party|canada|canadian|carney|poilievre|" \
        r"australia|albanese|ireland|irish|new zealand|scotland|scottish|wales|welsh"
RL, RA = re.compile(LOCAL, re.I), re.compile(ANGLO, re.I)


def cls(m):
    s = m[3] + " " + m[1].replace("-", " ")
    return "LOCAL" if RL.search(s) else ("ANGLO" if RA.search(s) else "US")


meta = json.load(gzip.open(f"{B}entries_c_meta.json.gz")); MK = meta["markets"]
at = dt.datetime.strptime(meta["at"], "%Y-%m-%d %H:%M").replace(tzinfo=dt.timezone.utc).timestamp()
kind = {mi: cls(m) for mi, m in enumerate(MK) if m[2] == "politics" and m[4] < at}
blob = gzip.open(f"{B}entries_c.bin.gz").read()
big, allf = {}, {}
for t, mi, wi, hb, S, C, F, a, a60, a300, lag, fl in ROW.iter_unpack(blob):
    k0 = kind.get(mi)
    if not k0 or S <= 0 or C <= 0: continue
    p = a300 / 1e4
    if not 0.05 <= p <= 0.95: continue
    side = "YES" if fl & 1 else "NO"; m = MK[mi]
    r = dict(t=t, e=m[1], side=side, end=m[4], kind=k0, p=p, q=m[3], f=(1 if fl & 2 else 0) - p - m[7] * p * (1 - p))
    k = (mi, side)
    if k not in allf or allf[k]["t"] > t: allf[k] = r
    if C >= 200 and (k not in big or big[k]["t"] > t): big[k] = r
del blob


def stat(rr):
    ev = collections.defaultdict(lambda: [0.0, 0])
    for r in rr: ev[r["e"]][0] += r["f"]; ev[r["e"]][1] += 1
    v = list(ev.values()); n = sum(y[1] for y in v)
    if not n: return {"n": 0, "events": 0}
    o = {"n": n, "events": len(v), "pts": round(100 * sum(y[0] for y in v) / n, 2), "avg_p": round(sum(r["p"] for r in rr) / n, 3)}
    if len(v) >= 5:
        bs = sorted(sum(y[0] for y in s) / max(1, sum(y[1] for y in s)) for s in ([v[int(random.random() * len(v))] for _ in v] for _ in range(1000)))
        o["ci"] = [round(100 * bs[25], 1), round(100 * bs[974], 1)]
    return o


B_ = list(big.values()); ends = sorted(r["end"] for r in B_); mid = ends[len(ends) // 2]
out = {"politics markets": len(kind), "by class": dict(collections.Counter(kind.values())),
       "split_at": str(dt.datetime.fromtimestamp(mid, dt.timezone.utc)),
       "examples LOCAL": sorted({r["q"] for r in B_ if r["kind"] == "LOCAL"})[:8],
       "examples ANGLO": sorted({r["q"] for r in B_ if r["kind"] == "ANGLO"})[:5]}
for kd in ("LOCAL", "ANGLO", "US"):
    sel = [r for r in B_ if r["kind"] == kd]
    out[f"BIG {kd}"] = stat(sel)
    out[f"  BIG {kd} older"] = stat([r for r in sel if r["end"] < mid]); out[f"  BIG {kd} newer"] = stat([r for r in sel if r["end"] >= mid])
    for side in ("YES", "NO"):
        out[f"  BIG {kd} {side}"] = stat([r for r in sel if r["side"] == side])
        out[f"  ALL {kd} {side} (any size, first per market+side)"] = stat([r for r in allf.values() if r["kind"] == kd and r["side"] == side])
n = out["BIG LOCAL"]
ok = (n.get("events", 0) >= 30 and n.get("pts", -99) >= 3 and n.get("ci", [-1])[0] > 0 and out["  BIG LOCAL older"].get("pts", -1) > 0
      and out["  BIG LOCAL newer"].get("pts", -1) > 0 and n["pts"] - out["BIG US"].get("pts", 0) >= 2)
out["verdict"] = "PASS -> COPY-1 local read-out arm" if ok else "DEAD"
print(json.dumps(out, indent=1, ensure_ascii=False))
json.dump(out, open(f"{B}local_language_report.json", "w"), indent=1, ensure_ascii=False)
