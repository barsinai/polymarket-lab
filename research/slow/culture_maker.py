"""Cycle 39, N86 (adjacent to N58 / N60 / N76): culture launch-hour NO as the MAKER the fans buy YES from.
N58 takes the NO ask in the launch hour (+8.4 pts per market on the tape, N60 F300) but N76 found only ~$8 of single-price NO taker
money per market -> tiny tickets. The fans' YES BUYING is the flow that makes the NO cheap; a resting YES ask (= a NO bid) sits on
the other side of it, pays no taker fee and does not cross the spread. Is that seat better, and is it bigger?
Rules fixed BEFORE looking (group a tape, same filters as N60: market lives >= 24 h after its first trade L, entry >= 1 h before end):
  MAKER fill = the first YES-direction taker entry by anyone with L + 300 s <= t < L + 3600 s and YES price a in 0.10-0.95
               (our NO cost 1 - a in 0.05-0.90, the N58 band); we assume we were the resting order it hit (OPTIMISTIC: queue
               priority, and we must already sit at that price); maker fee 0; one fill per market.
  pts = (1 if NO won) - (1 - a). TAKER reference = the N60 F300 NO row on the same market (follower NO print >= 300 s, fee rate*p(1-p)).
  PLACEBO = the maker on the other side of the first NO-direction taker entry (= we hold YES): should be negative if fans are the edge.
  Capacity = YES-direction entering wallets in the window (count) and their first-print notional upper bound min(C, S * a).
Unit = event slug, bootstrap 1,000; halves by L.
DECISION: 'build' (maker arm on the book recorder) only if maker >= +5 pts with CI low > 0 on >= 100 events AND maker - taker (same
markets) >= +2 in BOTH halves; 'dead' if maker <= +1 or maker - taker <= 0 overall; else 'unclear'.
Exposed to: 17 / 23 (makers lose to the informed; simulate the fill), 22 (one variant, fixed here), 24 (halves), 5."""
import json, gzip, struct, collections, random, datetime as dt
ROW = struct.Struct("<IIIhfffHHHIB")
B = "data/research/"
random.seed(86)
meta = json.load(gzip.open(f"{B}entries_a_meta.json.gz")); MK = meta["markets"]
at = dt.datetime.strptime(meta["at"], "%Y-%m-%d %H:%M").replace(tzinfo=dt.timezone.utc).timestamp()
blob = gzip.open(f"{B}entries_a.bin.gz").read()
L = {}
for t, mi, *_ in ROW.iter_unpack(blob):
    if mi not in L or t < L[mi]:
        L[mi] = t
rows = sorted(ROW.iter_unpack(blob))
del blob
maker, taker, placebo = {}, {}, {}
cap_n = collections.Counter(); cap_usd = collections.defaultdict(float)
for t, mi, wi, hb, S, C, F, a, a60, a300, lag, fl in rows:
    m = MK[mi]; l0 = L[mi]
    if m[4] >= at or S <= 0 or C <= 0 or hb < 1 or m[4] - l0 < 24 * 3600:
        continue
    dtl = t - l0
    if dtl >= 3600:
        continue
    yes_dir = bool(fl & 1); won = bool(fl & 2)
    no_won = (not won) if yes_dir else won
    ap = a / 1e4
    if yes_dir and dtl >= 300 and 0.10 <= ap <= 0.95:
        cap_n[mi] += 1; cap_usd[mi] += min(C, S * ap)
        if mi not in maker:
            maker[mi] = dict(e=m[1], cat=m[2], l0=l0, f=(1 if no_won else 0) - (1 - ap))
    if not yes_dir:
        if mi not in taker:
            p = a300 / 1e4
            if 0.05 <= p <= 0.90:
                taker[mi] = dict(e=m[1], cat=m[2], l0=l0, f=(1 if no_won else 0) - p - m[7] * p * (1 - p))
        if dtl >= 300 and 0.05 <= ap <= 0.90 and mi not in placebo:     # NO taker at ap -> maker holds YES at 1 - ap
            placebo[mi] = dict(e=m[1], cat=m[2], l0=l0, f=(0 if no_won else 1) - (1 - ap))


def stat(rr):
    ev = collections.defaultdict(lambda: [0.0, 0])
    for r in rr:
        ev[r["e"]][0] += r["f"]; ev[r["e"]][1] += 1
    v = list(ev.values()); n = sum(y[1] for y in v)
    if len(v) < 5:
        return {"n": n, "events": len(v), "pts": round(100 * sum(y[0] for y in v) / n, 2) if n else None}
    bs = []
    for _ in range(1000):
        s = [v[int(random.random() * len(v))] for _i in v]
        bs.append(sum(y[0] for y in s) / max(1, sum(y[1] for y in s)))
    bs.sort()
    return {"n": n, "events": len(v), "pts": round(100 * sum(y[0] for y in v) / n, 2), "ci": [round(100 * bs[25], 1), round(100 * bs[974], 1)]}


M = list(maker.values())
mid = sorted(r["l0"] for r in M)[len(M) // 2]
both = [mi for mi in maker if mi in taker]
out = {"maker markets": len(M), "split_at": str(dt.datetime.fromtimestamp(mid, dt.timezone.utc)), "same markets": len(both)}
diff = {}
for h, sel in (("all", lambda r: True), ("older", lambda r: r["l0"] < mid), ("newer", lambda r: r["l0"] >= mid)):
    out[f"{h} maker"] = stat([r for r in M if sel(r)])
    out[f"{h} taker (all its markets)"] = stat([r for r in taker.values() if sel(r)])
    mk = stat([maker[i] for i in both if sel(maker[i])]); tk = stat([taker[i] for i in both if sel(taker[i])])
    out[f"{h} same-market maker"] = mk; out[f"{h} same-market taker"] = tk
    diff[h] = round(mk["pts"] - tk["pts"], 2) if mk.get("pts") is not None and tk.get("pts") is not None else None
    out[f"{h} placebo (maker holds YES)"] = stat([r for r in placebo.values() if sel(r)])
out["maker - taker same markets (pts)"] = diff
out["ex-mention maker"] = stat([r for r in M if r["cat"] != "mention"])
for c, _n in collections.Counter(r["cat"] for r in M).most_common(6):
    out[f"  cat {c}"] = stat([r for r in M if r["cat"] == c])
cn = sorted(cap_n[mi] for mi in maker); cu = sorted(cap_usd[mi] for mi in maker)
out["capacity: YES entering wallets / market (median, p75)"] = [cn[len(cn) // 2], cn[3 * len(cn) // 4]]
out["capacity: their notional upper bound $ / market (median, p75)"] = [round(cu[len(cu) // 2], 1), round(cu[3 * len(cu) // 4], 1)]
o = out["all maker"]
if o.get("events", 0) >= 100 and o["pts"] >= 5 and o["ci"][0] > 0 and (diff["older"] or 0) >= 2 and (diff["newer"] or 0) >= 2:
    out["verdict"] = "build"
elif o.get("pts") is None or o["pts"] <= 1 or (diff["all"] or 0) <= 0:
    out["verdict"] = "dead"
else:
    out["verdict"] = "unclear"
print(json.dumps(out, indent=1))
json.dump(out, open(f"{B}culture_maker_report.json", "w"), indent=1)
