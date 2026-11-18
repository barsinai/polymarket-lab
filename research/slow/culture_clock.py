"""Cycle 33, N74 (adjacent to N58 / N60): is culture launch-hour NO a 'nobody is awake' effect or a 'fans buy YES' effect?
If the seed-book NO is cheap because no corrector is watching, the edge should sit in US night (Mon-Fri 04:00-12:59 UTC) and on
weekends (Sat/Sun UTC) and shrink in US day (Mon-Fri 13:00-03:59 UTC). If it is fan YES buying (N68 placebo: YES -4.1), it should be
flat across the clock. Rules fixed BEFORE looking: exactly the N60 F300 rows (group a, market lives >= 24 h after its first trade L,
entry >= 1 h before end, NO-side taker entry in the launch hour, one fill per market, follower = next NO print >= 300 s later at
0.05-0.90, fee = rate * p(1-p)); clock by L. Unit = event slug (bootstrap 1,000); halves by L.
DECISION: 'off-hours effect' only if (night+weekend) - (US day) >= +3 pts in BOTH halves and each arm >= 40 events; 'flat' if the
difference is < 3 pts in absolute value overall; anything else = 'unclear'. Exposed to 5 (arm sizes), 22 (one split, fixed here), 24."""
import json, gzip, struct, collections, random, datetime as dt
ROW = struct.Struct("<IIIhfffHHHIB")
B = "data/research/"
random.seed(74)
meta = json.load(gzip.open(f"{B}entries_a_meta.json.gz")); MK = meta["markets"]
at = dt.datetime.strptime(meta["at"], "%Y-%m-%d %H:%M").replace(tzinfo=dt.timezone.utc).timestamp()
blob = gzip.open(f"{B}entries_a.bin.gz").read()
L = {}
for t, mi, *_ in ROW.iter_unpack(blob):
    if mi not in L or t < L[mi]:
        L[mi] = t
rows = sorted(ROW.iter_unpack(blob))
del blob
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
    d = dt.datetime.fromtimestamp(l0, dt.timezone.utc)
    clk = "weekend" if d.weekday() >= 5 else ("us_night" if 4 <= d.hour < 13 else "us_day")
    first[mi] = dict(e=m[1], cat=m[2], l0=l0, clk=clk, f=(1 if fl & 2 else 0) - p - m[7] * p * (1 - p))
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
    return {"n": n, "events": len(v), "pts": round(100 * sum(y[0] for y in v) / n, 2), "ci": [round(100 * bs[25], 1), round(100 * bs[974], 1)]}


out = {"markets": len(R), "all": stat(R)}
diffs = {}
for h, sel in (("all", lambda r: True), ("older", lambda r: r["l0"] < mid), ("newer", lambda r: r["l0"] >= mid)):
    S = [r for r in R if sel(r)]
    for c in ("us_day", "us_night", "weekend"):
        out[f"{h} {c}"] = stat([r for r in S if r["clk"] == c])
    off = stat([r for r in S if r["clk"] != "us_day"]); day = out[f"{h} us_day"]
    out[f"{h} off-hours (night+weekend)"] = off
    diffs[h] = round(off["pts"] - day["pts"], 2)
out["off - day (pts)"] = diffs
ev_ok = out["all off-hours (night+weekend)"]["events"] >= 40 and out["all us_day"]["events"] >= 40
out["verdict"] = ("off-hours effect" if ev_ok and diffs["older"] >= 3 and diffs["newer"] >= 3 else
                  "flat" if abs(diffs["all"]) < 3 else "unclear")
print(json.dumps(out, indent=1))
json.dump(out, open(f"{B}culture_clock_report.json", "w"), indent=1)
