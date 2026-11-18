"""Cycle 34, N76 (adjacent to N58 / N60 / N68): how much money does culture launch-hour NO hold? Rules fixed BEFORE looking.
N58 is paper at $10 per market. Before any live talk the question is size: an edge of +8 pts on $10 is 80c per market.
Sample: culture market living >= 24 h, listed 2026-08-17 .. cut (old stray listings dropped so a per-day rate means something), ends before the tape cut).
Unit: taker rows (wallet, market, direction NO) whose FIRST NO trade came 300-3600 s after listing, first price 0.05-0.90.
Per market: NO taker cost in that window (C, all of that wallet's NO cost before the end - an upper bound) and 'single-price'
cost (rows with C/S within 1c of the first price = bought once or at one level); dollar edge harvested = sum S*(win - a - fee).
Reported per market (median, p75), per day (12-week average) and points per share clustered by event (= the N60 check from
another angle: what these real takers got).
DECISION: N58 has room above $10/market only if the median market shows >= $50 of single-price NO cost in the window AND
the harvested dollar edge is >= $20/day; otherwise N58 is a small-ticket edge (lesson 8 style) and any live proposal is sized
at $10-20 per market."""
import json, gzip, struct, collections, random, datetime as dt, statistics as st
ROW = struct.Struct("<IIIhfffHHHIB")
B = "data/research/"
random.seed(76)
CULT = {"mention", "movies", "music", "youtube", "awards", "pop-culture"}
meta = json.load(gzip.open(f"{B}entries_a_meta.json.gz")); MK = meta["markets"]
at = dt.datetime.strptime(meta["at"], "%Y-%m-%d %H:%M").replace(tzinfo=dt.timezone.utc).timestamp()
blob = gzip.open(f"{B}entries_a.bin.gz").read()
L = {}
for t, mi, *_ in ROW.iter_unpack(blob):
    if mi not in L or t < L[mi]:
        L[mi] = t
t0 = dt.datetime(2026, 8, 10, tzinfo=dt.timezone.utc).timestamp()   # tape start (12 weeks); stray old listings excluded
elig = set(); rows = []
for t, mi, wi, hb, S, C, F, a, a60, a300, lag, fl in ROW.iter_unpack(blob):
    m = MK[mi]
    if m[2] not in CULT or m[4] >= at:
        continue
    l0 = L[mi]
    if m[4] - l0 < 24 * 3600 or l0 < t0 + 7 * 86400:
        continue
    elig.add(mi)
    if fl & 1 or S <= 0 or not 300 <= t - l0 < 3600:
        continue
    p = a / 1e4
    if not 0.05 <= p <= 0.90:
        continue
    win = 1 if fl & 2 else 0
    single = abs(C / S - p) <= 0.01
    rows.append(dict(m=mi, e=m[1], cat=m[2], S=S, C=C, p=p, single=single,
                     edge=S * (win - p - m[7] * p * (1 - p)), pts=win - p - m[7] * p * (1 - p)))
del blob
pm = collections.defaultdict(lambda: [0.0, 0.0, 0.0, 0])
for r in rows:
    x = pm[r["m"]]; x[0] += r["C"]; x[1] += r["C"] if r["single"] else 0; x[2] += r["edge"]; x[3] += 1
_l = sorted(L[x] for x in elig); days = (_l[-1] - _l[0]) / 86400
out0 = {"listing span": [str(dt.datetime.fromtimestamp(_l[0], dt.timezone.utc))[:16], str(dt.datetime.fromtimestamp(_l[-1], dt.timezone.utc))[:16]], "listings per day": round(len(_l) / days, 1)}
tot = [v[0] for v in pm.values()]; sing = [v[1] for v in pm.values()]
allm = len(elig); nm = len(pm)
sing_all = sing + [0.0] * (allm - nm)    # markets with no such taker count as 0


def q(v, f):
    v = sorted(v); return round(v[min(len(v) - 1, int(f * len(v)))], 1)


ev = collections.defaultdict(lambda: [0.0, 0.0])
for r in rows:
    ev[r["e"]][0] += r["edge"]; ev[r["e"]][1] += r["S"]
v = list(ev.values()); bs = []
for _ in range(1000):
    s = [v[int(random.random() * len(v))] for _i in v]
    bs.append(sum(y[0] for y in s) / sum(y[1] for y in s))
bs.sort()
out = {**out0, "eligible_markets": allm, "markets_with_window_NO_takers": nm, "events": len(ev), "days": round(days, 1),
       "taker_rows": len(rows),
       "NO cost per market (upper bound): median / p75 / p90": [q(tot, .5), q(tot, .75), q(tot, .9)],
       "single-price NO cost per market: median / p75 / p90": [q(sing, .5), q(sing, .75), q(sing, .9)],
       "single-price cost, all eligible markets (0 if none): median / p75": [q(sing_all, .5), q(sing_all, .75)],
       "takers' share-weighted pts (event CI)": [round(100 * sum(y[0] for y in v) / sum(y[1] for y in v), 2),
                                                 [round(100 * bs[25], 1), round(100 * bs[974], 1)]],
       "harvested $ edge per day": round(sum(r["edge"] for r in rows) / days, 1),
       "harvested $ edge per day, single-price rows": round(sum(r["edge"] for r in rows if r["single"]) / days, 1),
       "NO cost per day": round(sum(r["C"] for r in rows) / days, 0),
       "top-10 markets share of $ edge": round(sum(sorted((x[2] for x in pm.values()), reverse=True)[:10]) /
                                               max(1e-9, sum(x[2] for x in pm.values())), 2)}
for c in sorted(CULT):
    rr = [r for r in rows if r["cat"] == c]
    if rr:
        out[f"by cat {c}: rows / $edge per day / pts"] = [len(rr), round(sum(r['edge'] for r in rr) / days, 1),
                                                           round(100 * sum(r['edge'] for r in rr) / sum(r['S'] for r in rr), 1)]
ok = q(sing, .5) >= 50 and out["harvested $ edge per day"] >= 20
out["verdict"] = "ROOM above $10/market" if ok else "SMALL-TICKET: size N58 at $10-20 per market"
print(json.dumps(out, indent=1))
json.dump(out, open(f"{B}culture_capacity_report.json", "w"), indent=1)
