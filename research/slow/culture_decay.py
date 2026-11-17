"""Cycle 30, N68 (adjacent to N58 / N66): how fast does the culture launch-hour NO edge decay with market age?
Rules fixed BEFORE looking. Why it matters: launch_paper.py only buys culture markets < 60 min old (3 positions in its first 11 h);
if NO still pays at 1-6 h, a 'late look' arm would add markets (and events) the 150-s poll missed or skipped, and give the read faster.
Unit: culture market (mention/movies/music/youtube/awards/pop-culture) that lives >= 24 h and was listed >= 7 d after the tape start
(so its first tape print ~ its listing); taker NO entry at age A; follower buys NO 300 s later at the recorded ask a300 (0.05-0.95),
fee 0.07-style m[7]*p*(1-p); first follower fill per market per age bucket; points per share clustered by event (bootstrap 1000).
Exposed to: 1 (follower >= 300 s), 5/6 (events), 22 (forking: one decision, fixed here), 24 (halves), 11 (all markets finished).
DECISION ('1-6 h' bucket, culture NO): PASS only if >= 40 events, pts > +3, event CI low > 0, both halves (by listing) > 0,
ex-mention > 0, largest event < 25% of positive points. Diagnostic: the same bucket restricted to markets with NO launch-hour fill
(what a wider tracker would ADD), and <1 h / 6-24 h for the decay curve."""
import json, gzip, struct, collections, random, datetime as dt
ROW = struct.Struct("<IIIhfffHHHIB")
B = "data/research/"
random.seed(68)
CULT = {"mention", "movies", "music", "youtube", "awards", "pop-culture"}
BK = [("< 1 h", 0, 1), ("1-3 h", 1, 3), ("3-6 h", 3, 6), ("6-24 h", 6, 24)]
R = []
for g in "abc":
    meta = json.load(gzip.open(f"{B}entries_{g}_meta.json.gz")); MK = meta["markets"]
    at = dt.datetime.strptime(meta["at"], "%Y-%m-%d %H:%M").replace(tzinfo=dt.timezone.utc).timestamp()
    blob = gzip.open(f"{B}entries_{g}.bin.gz").read()
    L = {}
    for t, mi, *_ in ROW.iter_unpack(blob):
        if mi not in L or t < L[mi]:
            L[mi] = t
    t0 = min(L.values())
    for t, mi, wi, hb, S, C, F, a, a60, a300, lag, fl in ROW.iter_unpack(blob):
        m = MK[mi]
        if m[2] not in CULT or fl & 1 or m[4] >= at or S <= 0 or hb < 1:
            continue
        l0 = L[mi]
        if m[4] - l0 < 24 * 3600 or l0 < t0 + 7 * 86400:
            continue
        ah = (t - l0) / 3600
        b = next((n for n, lo, hi in BK if lo <= ah < hi), None)
        p = a300 / 1e4
        if b is None or not 0.05 <= p <= 0.95:
            continue
        R.append(dict(e=(g, m[1]), m=(g, mi), cat=m[2], b=b, t=t, l0=l0, p=p,
                      fol=(1 if fl & 2 else 0) - p - m[7] * p * (1 - p)))
    del blob
first = {}
for r in sorted(R, key=lambda r: r["t"]):
    first.setdefault((r["m"], r["b"]), r)
F = list(first.values())
lh = {r["m"] for r in F if r["b"] == "< 1 h"}
_lm = sorted({r["m"]: r["l0"] for r in F}.values()); mid = _lm[len(_lm) // 2]


def stat(rows):
    ev = collections.defaultdict(lambda: [0.0, 0])
    for r in rows:
        ev[r["e"]][0] += r["fol"]; ev[r["e"]][1] += 1
    v = list(ev.values()); n = sum(y[1] for y in v)
    if len(v) < 5:
        return {"n": n, "events": len(v)}
    bs = []
    for _ in range(1000):
        s = [v[int(random.random() * len(v))] for _i in v]
        bs.append(sum(y[0] for y in s) / max(1, sum(y[1] for y in s)))
    bs.sort()
    pos = sum(y[0] for y in v if y[0] > 0)
    return {"n": n, "events": len(v), "pts": round(100 * sum(y[0] for y in v) / n, 2),
            "ci": [round(100 * bs[25], 1), round(100 * bs[974], 1)], "avg_p": round(sum(r["p"] for r in rows) / n, 3),
            "top_event_share": round(max(y[0] for y in v) / pos, 3) if pos > 0 else None}


out = {"rows": len(R), "markets": len({r["m"] for r in F}), "split_at": str(dt.datetime.fromtimestamp(mid, dt.timezone.utc))}
for n, *_ in BK:
    out[n] = stat([r for r in F if r["b"] == n])
D = [r for r in F if r["b"] in ("1-3 h", "3-6 h")]
seen = {}
for r in sorted(D, key=lambda r: r["t"]):
    seen.setdefault(r["m"], r)
D = list(seen.values())  # one fill per market in 1-6 h
out["DECISION 1-6 h"] = s0 = stat(D)
hv = {h: stat([r for r in D if (r["l0"] < mid) == (h == "older")]) for h in ("older", "newer")}
for h, v in hv.items():
    out[f"  {h} half"] = v
out["  ex-mention"] = xm = stat([r for r in D if r["cat"] != "mention"])
out["  ADDED: markets with no launch-hour fill"] = stat([r for r in D if r["m"] not in lh])
out["  overlap: markets that also had a launch-hour fill"] = stat([r for r in D if r["m"] in lh])
for c_, _n in collections.Counter(r["cat"] for r in D).most_common(6):
    out[f"  cat {c_}"] = stat([r for r in D if r["cat"] == c_])
ok = (s0.get("events", 0) >= 40 and s0["pts"] > 3 and s0["ci"][0] > 0 and all(v.get("pts", -1) > 0 for v in hv.values())
      and xm.get("pts", -1) > 0 and (s0.get("top_event_share") or 1) < 0.25)
out["verdict"] = "PASS" if ok else "FAIL"
print(json.dumps(out, indent=1))
json.dump(out, open(f"{B}culture_decay_report.json", "w"), indent=1)
