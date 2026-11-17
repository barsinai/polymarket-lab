"""Cycle 31, N71 (outside the box): collectible price Over/Under markets (Pokemon sealed product / card prices, strike ~ the price at
listing, resolve ~1 month later on a public price tracker). Why the crowd could be wrong: collectors buy 'Over' on things they love
(fans, N58's pattern) while new-set singles and sealed product usually drift down after release; nobody models it.
Exposed to 6 (all markets of one date move with the whole Pokemon market = one bet per date), 5 (dates, not markets), 13 (price
trackers are public), 11 (all finished). Test fixed before looking: every taker entry in the first 72 h after the market's first print,
follower at the next other-wallet print >= 300 s later (a300), BOTH sides reported; first follower fill per market per side;
points per share, clustered by END DATE (the independent unit). DEAD if < 6 end dates (independent events) regardless of the number."""
import json, gzip, struct, collections, re, datetime as dt
ROW = struct.Struct("<IIIhfffHHHIB")
meta = json.load(gzip.open("data/research/entries_a_meta.json.gz")); MK = meta["markets"]
idx = {i for i, m in enumerate(MK) if re.search(r"price-up-down|price over/under", m[1] + m[3], re.I)}
blob = gzip.open("data/research/entries_a.bin.gz").read()
L = {}; rows = []
for t, mi, wi, hb, S, C, F, a, a60, a300, lag, fl in ROW.iter_unpack(blob):
    if mi in idx:
        L[mi] = min(L.get(mi, t), t); rows.append((t, mi, fl, a300 / 1e4))
first = {}
for t, mi, fl, p in sorted(rows):
    if t - L[mi] < 72 * 3600 and 0.03 <= p <= 0.97:
        first.setdefault((mi, fl & 1), (p, 1 if fl & 2 else 0, MK[mi][7]))
out = {"markets": len(idx), "yes_won": sum(MK[i][6] >= 0.5 for i in idx),
       "end_dates": sorted({str(dt.datetime.fromtimestamp(MK[i][4], dt.timezone.utc).date()) for i in idx})}
for side, nm in ((1, "Over (YES)"), (0, "Under (NO)")):
    by = collections.defaultdict(list)
    for (mi, s), (p, w, f) in first.items():
        if s == side:
            by[str(dt.datetime.fromtimestamp(MK[mi][4], dt.timezone.utc).date())].append(w - p - f * p * (1 - p))
    n = sum(len(v) for v in by.values())
    out[nm] = {"n": n, "pts": round(100 * sum(sum(v) for v in by.values()) / max(1, n), 1),
               "by_end_date": {d: [len(v), round(100 * sum(v) / len(v), 1)] for d, v in sorted(by.items())}}
out["verdict"] = "DEAD by count (< 6 independent end dates)" if len(out["end_dates"]) < 6 else "READ"
print(json.dumps(out, indent=1))
