"""N43 (cycle 17, outside the box): daily 'US national average gas price on <date>' bucket markets (AAA, 1-cent buckets) - never tested.
Why the crowd could be wrong: the AAA average moves slowly and smoothly (wholesale RBOB leads retail by days), yet the books are
priced on 1-cent buckets by a handful of traders; a persistence / trend nowcast from the previous resolved days may beat the price.
Rules fixed BEFORE looking at outcomes (written with this docstring):
  A. N39 favourite rule: taker entries on the favourite 0.60-0.97 by hours before end (1-6, 6-24, 24-168); points = win - price - fee.
  B. Band calibration of YES entries 1-48 h before end (avg price vs won).
  C. Nowcast: for day D take the resolved values of D-1 and D-2 (bucket midpoint; open buckets = edge -/+ 0.5c); trend value
     v = v1 + (v1 - v2). Entries on YES of the bucket containing v, 6-48 h before end: points per share; and on YES of every
     other bucket priced >= 0.30 (the 'crowd says X, nowcast says not X' side, booked as NO via the tape's direction).
Units: event = one date. Event-clustered bootstrap. Older / newer half by end date. Follower = print 60 s later + fee.
Data: 12-week public trade tape entries_c (economy), real fills with fees, receive order = tape order (taker prints)."""
import json, gzip, struct, collections, random, re, datetime as dt
ROW = struct.Struct("<IIIhfffHHHIB")
B = "data/research/"
random.seed(43)
meta = json.load(gzip.open(f"{B}entries_c_meta.json.gz")); MK = meta["markets"]
NUM = re.compile(r"\$(\d+\.\d+)")
mk = {}
for i, m in enumerate(MK):
    if not m[1].startswith("us-gas-price-on-"):
        continue
    q = m[3]; xs = [float(x) for x in NUM.findall(q)]
    if "less than" in q and xs:
        lo, hi = -9.0, xs[0]
    elif "between" in q and len(xs) >= 2:
        lo, hi = xs[0], round(xs[1] + 0.0001, 4)
    elif "+" in q and xs:
        lo, hi = xs[0], 99.0
    else:
        continue
    mk[i] = dict(e=m[1], q=q, end=m[4], lo=lo, hi=hi, fr=m[7])
# resolved YES per market from any entry's flags
R = []; yes = {}
blob = gzip.open(f"{B}entries_c.bin.gz").read()
for t, mi, wi, hb, S, C, F, a, a60, a300, lag, fl in ROW.iter_unpack(blob):
    if mi not in mk or S <= 0 or C <= 0:
        continue
    d = 1 if fl & 1 else -1; w = 1 if fl & 2 else 0
    yes[mi] = w if d == 1 else 1 - w
    R.append(dict(mi=mi, e=mk[mi]["e"], t=t, hb=hb, d=d, p=C / S, fee_ps=F / S, a60=a60 / 1e4, win=w, fr=mk[mi]["fr"]))
ev_m = collections.defaultdict(list)
for mi, m in mk.items():
    ev_m[m["e"]].append(mi)
val = {}
for e, ms in ev_m.items():
    wins = [mi for mi in ms if yes.get(mi) == 1]
    if len(wins) == 1:
        m = mk[wins[0]]
        lo = m["lo"] if m["lo"] > 0 else m["hi"] - 0.005
        hi = m["hi"] if m["hi"] < 50 else m["lo"] + 0.005
        val[e] = ((lo + hi) / 2, mk[wins[0]]["end"])
print("markets", len(mk), "events", len(ev_m), "resolved one-bucket events", len(val), "entries", len(R))
order = sorted(val, key=lambda e: val[e][1])
print("resolved series:", [(e[16:], round(val[e][0], 4)) for e in order])
ends = sorted(val[e][1] for e in val); mid_end = ends[len(ends) // 2] if ends else 0


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
for lo, hi in ((1, 6), (6, 24), (24, 168)):
    fav = [r for r in R if lo <= r["hb"] < hi and 0.60 <= r["p"] <= 0.97]
    out[f"A FAV {lo}-{hi}h"] = stat(fav); out[f"A FAV {lo}-{hi}h follower"] = stat(fav, True)
fav = [r for r in R if 6 <= r["hb"] < 168 and 0.60 <= r["p"] <= 0.97]
out["A FAV 6-168h older"] = stat([r for r in fav if mk[r["mi"]]["end"] < mid_end]); out["A FAV 6-168h newer"] = stat([r for r in fav if mk[r["mi"]]["end"] >= mid_end])
for lo, hi in ((0.03, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 0.97)):
    rows = [r for r in R if 1 <= r["hb"] < 48 and r["d"] == 1 and lo <= r["p"] < hi]
    out[f"B YES band {lo}-{hi}"] = dict(stat(rows), avg_p=round(sum(r["p"] for r in rows) / len(rows), 3) if rows else None,
                                         won=round(sum(r["win"] for r in rows) / len(rows), 3) if rows else None)
# C nowcast
pos = {e: k for k, e in enumerate(order)}
C_in, C_out, hits = [], [], []
for r in R:
    e = r["e"]
    if not (6 <= r["hb"] < 48) or e not in pos or pos[e] < 2:
        continue
    v1 = val[order[pos[e] - 1]][0]; v2 = val[order[pos[e] - 2]][0]
    if val[order[pos[e] - 1]][1] - val[order[pos[e] - 2]][1] > 1.5 * 86400 or val[e][1] - val[order[pos[e] - 1]][1] > 1.5 * 86400:
        continue                                                    # need consecutive days
    v = v1 + (v1 - v2); m = mk[r["mi"]]
    inside = m["lo"] <= v < m["hi"]
    if inside and r["d"] == 1:
        C_in.append(r)
    if (not inside) and r["d"] == -1 and (1 - r["p"]) >= 0.30:      # NO on a bucket the crowd prices >= 0.30 that the nowcast rejects
        C_out.append(r)
for e in order[2:]:
    k = pos[e]
    if val[e][1] - val[order[k - 1]][1] <= 1.5 * 86400 and val[order[k - 1]][1] - val[order[k - 2]][1] <= 1.5 * 86400:
        v = 2 * val[order[k - 1]][0] - val[order[k - 2]][0]; hits.append(abs(v - val[e][0]) < 0.005)
out["C nowcast bucket hit rate"] = {"days": len(hits), "hit": round(sum(hits) / len(hits), 3) if hits else None}
out["C YES nowcast bucket 6-48h"] = stat(C_in); out["C YES nowcast bucket follower"] = stat(C_in, True)
out["C NO on rejected bucket priced >=0.30 6-48h"] = stat(C_out); out["C NO rejected follower"] = stat(C_out, True)
for k, v in out.items():
    print(f"{k:44} {v}")
json.dump(out, open(B + "gas_report.json", "w"), indent=1)
