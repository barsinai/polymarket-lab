"""Cycle 40, N88 (adjacent to N58 / N78 / N82): culture launch-hour NO by EVENT WIDTH.
Why it could differ: in a wide event (one winner among many named outcomes: awards, '#1 song', 'who will...') fans bid YES on their
favourite names, so many siblings are rich at launch; a stand-alone binary has one YES to overbid and a crowd that prices both sides.
If N58's edge lives only in wide events, stand-alones are dead weight in the tracker (and the reverse).
Rules fixed BEFORE looking. Rows = exactly the N78 rows (culture_series.py: group a, N60 F300 launch-hour NO, one fill per market,
L >= tape start + 7 d). Width = number of markets of the event slug in the tape meta: single (1), small (2-4), wide (5+).
Unit = event slug, bootstrap 1,000; halves by L.
DECISION: drop a width class from the N58 forward read (pre-registered split, no tracker change) if it has >= 40 events and pts <= 0
in BOTH halves; 'wide only' if wide - single >= +4 in both halves and single <= +2; else 'flat/unclear' (keep reading all).
Exposed to: 5, 6 (a wide event is one bet: clustered by event), 22 (one split fixed here), 24 (halves), 13."""
import json, gzip, struct, collections, random, re, datetime as dt
ROW = struct.Struct("<IIIhfffHHHIB")
B = "data/research/"
random.seed(88)
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


W = collections.Counter(m[1] for m in MK)


def width(e):
    n = W[e]
    return "single" if n == 1 else ("small" if n <= 4 else "wide")


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
    first[mi] = dict(e=m[1], cat=m[2], l0=l0, k=width(m[1]), f=(1 if fl & 2 else 0) - p - m[7] * p * (1 - p))
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
for h, f in (("all", lambda r: True), ("older", lambda r: r["l0"] < mid), ("newer", lambda r: r["l0"] >= mid)):
    for k in ("single", "small", "wide"):
        out[f"{h} {k}"] = stat([r for r in R if f(r) and r["k"] == k])
    for k in ("single", "small", "wide"):
        out[f"  {h} {k} ex-mention"] = stat([r for r in R if f(r) and r["k"] == k and r["cat"] != "mention"]) if h == "all" else None
out = {k: v for k, v in out.items() if v is not None}
drop = [k for k in ("single", "small", "wide") if out[f"all {k}"].get("events", 0) >= 40
        and out[f"older {k}"].get("pts", 1) <= 0 and out[f"newer {k}"].get("pts", 1) <= 0]
dw = {h: (out[f"{h} wide"].get("pts") or 0) - (out[f"{h} single"].get("pts") or 0) for h in ("older", "newer")}
if drop:
    out["verdict"] = "drop " + ",".join(drop) + " from the N58 read"
elif min(dw.values()) >= 4 and (out["all single"].get("pts") or 0) <= 2:
    out["verdict"] = "wide only"
else:
    out["verdict"] = "flat/unclear"
out["wide - single by half"] = dw
print(json.dumps(out, indent=1))
json.dump(out, open(f"{B}culture_width_report.json", "w"), indent=1)
