"""Cycle 35, N78 (adjacent to N58 / N60 / N74): is the culture launch-hour NO edge a ONE-OFF effect (no base rate for fans to
anchor on) or does it also live in RECURRING series (weekly Netflix / Spotify / Billboard / App Store / MrBeast views / Big Brother
mention episodes / tweet counts), where regulars and bots re-price each new copy from the last one (lesson 13)?
Rules fixed BEFORE looking. Rows = exactly the N60 F300 rows (as culture_clock.py: group a, market lives >= 24 h after its first trade L,
entry >= 1 h before end, NO-side taker entry in the launch hour, one fill per market, follower = next NO print >= 300 s later at
0.05-0.90, fee = rate * p(1-p)), plus L >= tape start + 7 d (so the tape sees earlier copies of a series).
Series key = event slug with all digits, month names and weekday names removed. Event kinds (by the event's first L):
  'recurring' = the series has an EARLIER event first traded >= 1 day before this one;
  'one-off'   = the series has exactly one event in the 12 weeks;
  'series-first' = first copy of a multi-event series (diagnostic only).
Unit = event slug, bootstrap 1,000; halves by L.
DECISION: 'skip recurring' (tracker change) only if recurring <= +1 pt AND one-off >= +5 with CI low > 0, each >= 40 events, and
one-off - recurring >= +4 in BOTH halves; 'flat' if |one-off - recurring| < 3 overall; else 'unclear' (no change).
Exposed to: 5 (arm sizes), 22 (one split, fixed here), 24 (halves), 13 (the mechanism this tests)."""
import json, gzip, struct, collections, random, re, datetime as dt
ROW = struct.Struct("<IIIhfffHHHIB")
B = "data/research/"
random.seed(78)
meta = json.load(gzip.open(f"{B}entries_a_meta.json.gz")); MK = meta["markets"]
at = dt.datetime.strptime(meta["at"], "%Y-%m-%d %H:%M").replace(tzinfo=dt.timezone.utc).timestamp()
blob = gzip.open(f"{B}entries_a.bin.gz").read()
L = {}
for t, mi, *_ in ROW.iter_unpack(blob):
    if mi not in L or t < L[mi]:
        L[mi] = t
rows = sorted(ROW.iter_unpack(blob))
del blob
T0 = min(L.values())
MON = r"(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)"
DAY = r"(monday|tuesday|wednesday|thursday|friday|saturday|sunday)"


def series(slug):
    s = re.sub(r"\d+", "", slug.lower()); s = re.sub(MON, "", s); s = re.sub(DAY, "", s)
    return re.sub(r"-+", "-", s).strip("-")


evL = {}
for mi, l0 in L.items():
    e = MK[mi][1]
    evL[e] = min(evL.get(e, 1e12), l0)
ser = collections.defaultdict(list)
for e, l0 in evL.items():
    ser[series(e)].append(l0)


def kind(e):
    s = ser[series(e)]; l0 = evL[e]
    if len(s) == 1:
        return "one-off"
    return "recurring" if any(x <= l0 - 86400 for x in s) else "series-first"


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
    first[mi] = dict(e=m[1], cat=m[2], l0=l0, k=kind(m[1]), f=(1 if fl & 2 else 0) - p - m[7] * p * (1 - p))
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


out = {"markets": len(R), "all": stat(R), "split_at": str(dt.datetime.fromtimestamp(mid, dt.timezone.utc))}
diff = {}
for h, sel in (("all", lambda r: True), ("older", lambda r: r["l0"] < mid), ("newer", lambda r: r["l0"] >= mid)):
    S = [r for r in R if sel(r)]
    for k in ("one-off", "recurring", "series-first"):
        out[f"{h} {k}"] = stat([r for r in S if r["k"] == k])
    a_, b_ = out[f"{h} one-off"].get("pts"), out[f"{h} recurring"].get("pts")
    diff[h] = round(a_ - b_, 2) if a_ is not None and b_ is not None else None
out["one-off - recurring (pts)"] = diff
for k in ("one-off", "recurring"):
    for c, _n in collections.Counter(r["cat"] for r in R if r["k"] == k).most_common(5):
        out[f"  {k} cat {c}"] = stat([r for r in R if r["k"] == k and r["cat"] == c])
out["  recurring ex-mention"] = stat([r for r in R if r["k"] == "recurring" and r["cat"] != "mention"])
out["top recurring series"] = collections.Counter(series(r["e"]) for r in R if r["k"] == "recurring").most_common(8)
o, rc = out["all one-off"], out["all recurring"]
sz = o.get("events", 0) >= 40 and rc.get("events", 0) >= 40
if sz and rc["pts"] <= 1 and o["pts"] >= 5 and o["ci"][0] > 0 and (diff["older"] or 0) >= 4 and (diff["newer"] or 0) >= 4:
    out["verdict"] = "skip recurring"
elif diff["all"] is not None and abs(diff["all"]) < 3:
    out["verdict"] = "flat"
else:
    out["verdict"] = "unclear"
print(json.dumps(out, indent=1))
json.dump(out, open(f"{B}culture_series_report.json", "w"), indent=1)
