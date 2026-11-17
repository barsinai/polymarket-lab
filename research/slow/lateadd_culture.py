"""Cycle 29, N66 (adjacent to N58 / N62): CULTURE LATE-ADDS + the tracker's one-look rule. Rules fixed here BEFORE looking at
the new splits (the pooled +11.0 was a cycle-27 side read, so it is NOT evidence here - only the pre-registered splits below count).

Why: launch_paper.py marks every market 'seen' at its first sight. 158 of 161 candidates in its first 7 h were skipped for
transient reasons ('not accepting orders' placeholders 86, 'no NO ask' 35, 'ask outside band' 28, 'spread > 10c' 7) and are never
looked at again, even when the book forms minutes later or a placeholder ('Person A..L') becomes a real named outcome days later -
which is exactly a culture LATE-ADD. If culture late-add NO holds up, the tracker should re-check transient skips and watch
placeholders until they open.
Exposed to: 22 (the pooled number was seen; decide on halves / categories / one-event concentration only), 5/6 (unit = event),
1 (follower >= 300 s), 2, 24.
DECISION (culture LATE-ADD, NO, launch hour, follower a300, one fill per market): PASS only if pooled > +1 pt, event interval
bottom > -1, both halves (by market launch) > 0, ex-mention > 0, the largest single event < 25% of the summed points, >= 40 events.
Diagnostics: delay since event launch 1-3 d vs >= 3 d, NO price < 0.5 vs >= 0.5, by category, original culture NO for scale."""
import json, gzip, struct, collections, random, datetime as dt
ROW = struct.Struct("<IIIhfffHHHIB")
B = "data/research/"
random.seed(66)
CULT = {"mention", "movies", "music", "youtube", "awards", "pop-culture"}
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
    E0 = {}; EN = collections.Counter()
    for mi, l in L.items():
        e = MK[mi][1]; EN[e] += 1
        E0[e] = min(E0.get(e, l), l)
    for t, mi, wi, hb, S, C, F, a, a60, a300, lag, fl in ROW.iter_unpack(blob):
        m = MK[mi]; l0 = L[mi]; e = m[1]
        if m[4] >= at or S <= 0 or hb < 1 or m[4] - l0 < 24 * 3600 or EN[e] < 3 or E0[e] < t0 + 7 * 86400:
            continue
        kind = "LATE" if l0 >= E0[e] + 86400 else "ORIG" if l0 < E0[e] + 3600 else None
        age = t - l0
        arm = "launch hour" if age < 3600 else "24-72 h" if 86400 <= age < 3 * 86400 else None
        if kind is None or arm is None:
            continue
        p = a300 / 1e4
        if not 0.05 <= p <= 0.95:
            continue
        win = 1 if fl & 2 else 0
        R.append(dict(g=g, cult=(m[2] in CULT), cat=m[2], e=e, kind=kind, arm=arm, yes=bool(fl & 1), l0=l0, m=mi,
                      p=p, fol=win - p - m[7] * p * (1 - p), delay_h=(l0 - E0[e]) / 3600))
    del blob
_lm = sorted({r["m"]: r["l0"] for r in R if r["kind"] == "LATE"}.values()); mid = _lm[len(_lm) // 2]  # median launch of late-add MARKETS
for r in R:
    r["half"] = "older" if r["l0"] < mid else "newer"


def stat(rows, key="e"):
    ev = collections.defaultdict(lambda: [0.0, 0])
    for r in rows:
        ev[r[key]][0] += r["fol"]; ev[r[key]][1] += 1
    v = list(ev.values()); n = sum(y[1] for y in v)
    if len(v) < 5:
        return {"n": n, "events": len(v)}
    bs = []
    for _ in range(1000):
        s = [v[int(random.random() * len(v))] for _i in v]
        bs.append(sum(y[0] for y in s) / max(1, sum(y[1] for y in s)))
    bs.sort()
    return {"n": n, "events": len(v), "markets": len({r["m"] for r in rows}), "pts": round(100 * sum(y[0] for y in v) / n, 2),
            "ci": [round(100 * bs[25], 1), round(100 * bs[974], 1)], "events_pos": sum(1 for y in v if y[0] > 0)}


def sel(kind, arm, yes, cult=None, half=None, one_per_market=True):
    rows = [r for r in R if r["kind"] == kind and r["arm"] == arm and r["yes"] == yes and (cult is None or r["cult"] == cult)
            and (half is None or r["half"] == half)]
    if one_per_market:  # first follower fill per market (what a tracker buying once would get)
        seen = {}; [seen.setdefault(r["m"], r) for r in sorted(rows, key=lambda r: r["l0"])]
        rows = list(seen.values())
    return rows



def top_share(rows):
    ev = collections.defaultdict(float)
    for r in rows:
        ev[r["e"]] += r["fol"]
    tot = sum(v for v in ev.values() if v > 0)
    return round(max(ev.values()) / tot, 3) if tot > 0 else None


D = sel("LATE", "launch hour", False, cult=True)
out = {"rows": len(R), "split_at": str(dt.datetime.fromtimestamp(mid, dt.timezone.utc))}
out["DECISION culture late-add NO launch hour"] = s0 = stat(D)
hv = {}
for h in ("older", "newer"):
    out[f"  {h} half"] = hv[h] = stat([r for r in D if r["half"] == h])
out["  ex-mention"] = xm = stat([r for r in D if r["cat"] != "mention"])
out["  largest event share of positive points"] = ts_ = top_share(D)
out["  delay 1-3 d"] = stat([r for r in D if r["delay_h"] < 72])
out["  delay >= 3 d"] = stat([r for r in D if r["delay_h"] >= 72])
out["  NO price < 0.5"] = stat([r for r in D if r["p"] < 0.5])
out["  NO price >= 0.5"] = stat([r for r in D if r["p"] >= 0.5])
for c_, _n in collections.Counter(r["cat"] for r in D).most_common(6):
    out[f"  cat {c_}"] = stat([r for r in D if r["cat"] == c_])
out["culture late-add NO 24-72 h (control)"] = stat(sel("LATE", "24-72 h", False, cult=True))
out["culture original NO launch hour (scale)"] = stat(sel("ORIG", "launch hour", False, cult=True))
ok = (s0.get("events", 0) >= 40 and s0["pts"] > 1 and s0["ci"][0] > -1 and all(v.get("pts", -1) > 0 for v in hv.values())
      and xm.get("pts", -1) > 0 and ts_ is not None and ts_ < 0.25)
out["verdict"] = "PASS" if ok else "FAIL"
print(json.dumps(out, indent=1))
json.dump(out, open(f"{B}lateadd_culture_report.json", "w"), indent=1)
