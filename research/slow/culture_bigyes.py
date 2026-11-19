"""Cycle 42, N92 (adjacent to N58 / N78 / lesson 17): culture launch-hour NO, split by WHO bought YES before us.
Why it could differ: lesson 17 says small takers (< $10) lose and $200-1,000 takers win. N58's story is 'fans buy YES on the seed book'.
If a launch-hour market already saw a big YES taker order (>= $200) before our follower could act, the YES buying may be informed and
NO is the wrong side there; where only small tickets bought YES, NO should be better than the +8 average.
Rules fixed BEFORE looking. Rows = exactly the N78 / N88 rows (group a, launch-hour NO entry, follower fill a300 in 0.05-0.90, one fill per
market, finished, lives >= 24 h, L >= tape start + 7 d). Knowable flag: any YES-direction taker order >= $200 (orders_a, one transaction of
one wallet one way) in [L, t_entry + 300 s] - i.e. before the follower's fill could happen. Unit = event slug, bootstrap 1,000; halves by L.
DECISION: 'filter' if BIG has >= 30 events, BIG pts <= 0 in both halves and NONE - BIG >= +4 in both halves -> skip such markets in N58 and
add the split to its read-out; 'split only' if NONE - BIG >= +4 in both halves but BIG > 0; otherwise DEAD (no information in the flag).
Exposed to: 5, 6 (clustered by event), 22 (one split, threshold from lesson 17, fixed here), 24 (halves), 4 (receive time: tape timestamps
are block times; the follower's own fill is >= 300 s after the entry, so orders before t + 300 were visible)."""
import json, gzip, struct, collections, random, bisect, datetime as dt
ROW = struct.Struct("<IIIhfffHHHIB")
ROW2 = struct.Struct("<IIIhffHHHHHIffB")
B = "data/research/"
random.seed(92)
meta = json.load(gzip.open(f"{B}entries_a_meta.json.gz")); MK = meta["markets"]
at = dt.datetime.strptime(meta["at"], "%Y-%m-%d %H:%M").replace(tzinfo=dt.timezone.utc).timestamp()
blob = gzip.open(f"{B}entries_a.bin.gz").read()
L = {}
for t, mi, *_ in ROW.iter_unpack(blob):
    if mi not in L or t < L[mi]:
        L[mi] = t
rows = sorted(ROW.iter_unpack(blob))
del blob
ob = gzip.open(f"{B}orders_a.bin.gz").read()
BIGY = collections.defaultdict(list)       # market -> sorted times of YES-direction orders >= $200
BIGN = collections.defaultdict(list)       # same for NO direction (printed, not used by the decision)
for t, mi, wi, hb, c, sh, *_r, fl in ROW2.iter_unpack(ob):
    if mi in L and c >= 200 and t - L[mi] < 3 * 3600:
        (BIGY if fl & 1 else BIGN)[mi].append(t)
del ob
for d in (BIGY, BIGN):
    for v in d.values():
        v.sort()
T0 = min(L.values())


def nbefore(d, mi, t):
    return bisect.bisect_right(d.get(mi, []), t)


first = {}
for t, mi, wi, hb, S, C, F, a, a60, a300, lag, fl in rows:
    m = MK[mi]; l0 = L[mi]
    if m[4] >= at or S <= 0 or C <= 0 or hb < 1 or m[4] - l0 < 24 * 3600 or fl & 1:
        continue
    if t - l0 >= 3600 or mi in first or l0 < T0 + 7 * 86400:
        continue
    p = a300 / 1e4
    if not 0.05 <= p <= 0.90:
        continue
    first[mi] = dict(e=m[1], cat=m[2], l0=l0, p=p, by=nbefore(BIGY, mi, t + 300), bn=nbefore(BIGN, mi, t + 300),
                     f=(1 if fl & 2 else 0) - p - m[7] * p * (1 - p))
R = list(first.values())
mid = sorted(r["l0"] for r in R)[len(R) // 2]


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
    return {"n": n, "events": len(v), "pts": round(100 * sum(y[0] for y in v) / n, 2), "ci": [round(100 * bs[25], 1), round(100 * bs[974], 1)],
            "avg_p": round(sum(r["p"] for r in rr) / n, 3)}


out = {"markets": len(R), "all": stat(R), "split_at": str(dt.datetime.fromtimestamp(mid, dt.timezone.utc))}
for h, f in (("all", lambda r: True), ("older", lambda r: r["l0"] < mid), ("newer", lambda r: r["l0"] >= mid)):
    out[f"{h} NONE (no big YES before)"] = stat([r for r in R if f(r) and r["by"] == 0])
    out[f"{h} BIG (>= 1 YES order >= $200 before)"] = stat([r for r in R if f(r) and r["by"] > 0])
out["  print only: big NO order before"] = stat([r for r in R if r["bn"] > 0])
out["  print only: big YES and no big NO"] = stat([r for r in R if r["by"] > 0 and r["bn"] == 0])
out["  print only: ex-mention NONE"] = stat([r for r in R if r["by"] == 0 and r["cat"] != "mention"])
out["  print only: ex-mention BIG"] = stat([r for r in R if r["by"] > 0 and r["cat"] != "mention"])
g = {h: (out[f"{h} NONE (no big YES before)"].get("pts") or 0) - (out[f"{h} BIG (>= 1 YES order >= $200 before)"].get("pts") or 0)
     for h in ("older", "newer")}
bb = out["all BIG (>= 1 YES order >= $200 before)"]
if min(g.values()) >= 4 and bb.get("events", 0) >= 30 and all((out[f"{h} BIG (>= 1 YES order >= $200 before)"].get("pts") or 0) <= 0
                                                               for h in ("older", "newer")):
    out["verdict"] = "filter"
elif min(g.values()) >= 4:
    out["verdict"] = "split only"
else:
    out["verdict"] = "DEAD"
out["NONE - BIG by half"] = g
print(json.dumps(out, indent=1))
json.dump(out, open(f"{B}culture_bigyes_report.json", "w"), indent=1)
