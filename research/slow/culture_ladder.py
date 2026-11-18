"""Cycle 37, N82 (adjacent to N58 / N60): culture launch-hour NO on DEADLINE LADDERS ('Will X ... by Nov 24 / Nov 28 / Dec 1?').
On 11-18 the N58 tracker bought 18 of its 26 positions in five 'streamer finishes GTA VI by <date>' ladders within ~30 min - one theme,
several rungs each (lesson 6). Question: does the launch-hour NO edge hold on deadline ladders, and does buying every rung add
independent edge or just stack one bet?
Rules fixed BEFORE looking. Rows = the N60 F300 rows (as culture_clock.py: group a, market lives >= 24 h after its first trade L,
entry >= 1 h before end, NO-side taker entry within 1 h of L, one fill per market, follower = next NO print >= 300 s later at
0.05-0.90, fee = rate * p(1-p)). Deadline market = question matches ' by <month | end of | digit>' (or ' before <...>').
Kinds: 'ladder' = deadline market in an event with >= 3 deadline markets; 'deadline-single' = other deadline markets;
'other' = the rest. Unit = event (bootstrap 1,000). Rung: within a ladder event, rows ordered by end time: 'earliest' / 'later'.
DECISION: cap N58 to one rung per ladder event (the earliest-deadline rung) if ladder <= +1 pt or (later rungs <= +1 and earliest >= +4);
'no change' if ladder >= +5 with CI low > 0 on >= 30 events; else 'unclear' (report N58 by event, no code change).
Exposed to: 5, 6 (the point of this), 22 (one split, fixed here), 24 (halves)."""
import json, gzip, struct, collections, random, re, datetime as dt
ROW = struct.Struct("<IIIhfffHHHIB")
B = "data/research/"
random.seed(82)
meta = json.load(gzip.open(f"{B}entries_a_meta.json.gz")); MK = meta["markets"]
at = dt.datetime.strptime(meta["at"], "%Y-%m-%d %H:%M").replace(tzinfo=dt.timezone.utc).timestamp()
blob = gzip.open(f"{B}entries_a.bin.gz").read()
L = {}
for t, mi, *_ in ROW.iter_unpack(blob):
    if mi not in L or t < L[mi]:
        L[mi] = t
rows = sorted(ROW.iter_unpack(blob))
del blob
DL = re.compile(r"\b(by|before) (january|february|march|april|may|june|july|august|september|october|november|december|end of|the end|\d)", re.I)
dlc = collections.Counter(m[1] for m in MK if DL.search(m[3] or ""))


def kind(m):
    if not DL.search(m[3] or ""):
        return "other"
    return "ladder" if dlc[m[1]] >= 3 else "deadline-single"


first = {}
for t, mi, wi, hb, S, C, F, a, a60, a300, lag, fl in rows:
    m = MK[mi]; l0 = L[mi]
    if m[4] >= at or S <= 0 or C <= 0 or hb < 1 or m[4] - l0 < 24 * 3600 or fl & 1:
        continue
    if t - l0 >= 3600 or mi in first:
        continue
    p = a300 / 1e4
    if not 0.05 <= p <= 0.90:
        continue
    first[mi] = dict(e=m[1], end=m[4], cat=m[2], l0=l0, k=kind(m), p=p, f=(1 if fl & 2 else 0) - p - m[7] * p * (1 - p))
R = list(first.values())
byev = collections.defaultdict(list)
for r in R:
    if r["k"] == "ladder":
        byev[r["e"]].append(r)
for e, v in byev.items():
    v.sort(key=lambda r: r["end"])
    for i, r in enumerate(v):
        r["rung"] = "earliest" if i == 0 else "later"
mid = sorted(r["l0"] for r in R)[len(R) // 2]


def stat(rr, unit_event_mean=False):
    ev = collections.defaultdict(lambda: [0.0, 0])
    for r in rr:
        ev[r["e"]][0] += r["f"]; ev[r["e"]][1] += 1
    v = list(ev.values())
    if unit_event_mean:                      # one bet per event: mean edge of its rungs, weight 1
        v = [[y[0] / y[1], 1] for y in v]
    n = sum(y[1] for y in v)
    if not v:
        return {"n": 0}
    o = {"n": len(rr), "events": len(v), "pts": round(100 * sum(y[0] for y in v) / n, 2)}
    if len(v) >= 5:
        bs = []
        for _ in range(1000):
            s = [v[int(random.random() * len(v))] for _i in v]
            bs.append(sum(y[0] for y in s) / max(1, sum(y[1] for y in s)))
        bs.sort(); o["ci"] = [round(100 * bs[25], 1), round(100 * bs[974], 1)]
    return o


out = {"markets": len(R), "all": stat(R), "split_at": str(dt.datetime.fromtimestamp(mid, dt.timezone.utc))}
for k in ("ladder", "deadline-single", "other"):
    S = [r for r in R if r["k"] == k]
    out[k] = stat(S)
    out[k + " older / newer"] = [stat([r for r in S if r["l0"] < mid]).get("pts"), stat([r for r in S if r["l0"] >= mid]).get("pts")]
    out[k + " avg NO price"] = round(sum(r["p"] for r in S) / len(S), 3) if S else None
lad = [r for r in R if r["k"] == "ladder"]
out["ladder one bet per event (mean of rungs)"] = stat(lad, True)
out["ladder earliest rung"] = stat([r for r in lad if r["rung"] == "earliest"])
out["ladder later rungs"] = stat([r for r in lad if r["rung"] == "later"])
out["ladder rungs per event (median)"] = sorted(len(v) for v in byev.values())[len(byev) // 2] if byev else None
out["top ladder events"] = collections.Counter(r["e"] for r in lad).most_common(8)
la, ea, lr = out["ladder"], out["ladder earliest rung"], out["ladder later rungs"]
if la.get("events", 0) >= 10 and (la["pts"] <= 1 or (lr.get("pts", 9) <= 1 and ea.get("pts", -9) >= 4)):
    out["verdict"] = "cap one rung per ladder event"
elif la.get("events", 0) >= 30 and la["pts"] >= 5 and la["ci"][0] > 0:
    out["verdict"] = "no change"
else:
    out["verdict"] = "unclear"
print(json.dumps(out, indent=1))
json.dump(out, open(f"{B}culture_ladder_report.json", "w"), indent=1)
