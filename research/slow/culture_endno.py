"""Cycle 32, N72 (adjacent to N58 / N68): do fans keep over-pricing YES into the LAST two days of culture markets?
N68's placebo said culture YES buyers lose 4.1 pts at 1-6 h after listing (fans buy YES); the launch-hour edge decays with age
(7.1 -> 3.5 pts at 6-24 h, +0.7 at 24-72 h). Question: does it come back near the end, when the outcome becomes salient again
(the release / show / chart day) and fans pile in? Rules fixed BEFORE looking.
Unit: culture market EX-MENTION (mention resolves on live speech -> a different mechanism, and N28-N44 already covered it), lives
>= 72 h (so 'near the end' is not the launch), market listed >= 7 d after the tape start; a taker's first NO entry with 1 <= hours
before the scheduled end < 48 and market age >= 24 h; follower buys NO 300 s later at the recorded next print a300 (0.05-0.90), fee
m[7]*p*(1-p); first follower fill per market; points per share clustered by event (bootstrap 1000).
Exposed to: 1 (follower >= 300 s), 2 (a cheap NO that survives near the end may be cheap for a reason), 11/15 (path questions resolve
YES early -> we only use markets finished on the tape), 5/6 (events), 22 (forking: one decision, fixed here), 24 (halves).
DECISION: PASS only if >= 40 events, pts > +3, event CI low > 0, both halves (by end date) > 0, largest event < 25% of positive points.
Placebo: the YES side under the same rule (expect <= 0 if the story is fans over-pricing YES)."""
import json, gzip, struct, collections, random, datetime as dt
ROW = struct.Struct("<IIIhfffHHHIB")
B = "data/research/"
random.seed(72)
CULT = {"movies", "music", "youtube", "awards", "pop-culture"}
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
        if m[2] not in CULT or m[4] >= at or S <= 0:
            continue
        l0 = L[mi]
        if m[4] - l0 < 72 * 3600 or l0 < t0 + 7 * 86400:
            continue
        hbe = (m[4] - t) / 3600
        if not (1 <= hbe < 48) or t - l0 < 24 * 3600:
            continue
        p = a300 / 1e4
        if not 0.05 <= p <= 0.90:
            continue
        side = "YES" if fl & 1 else "NO"
        R.append(dict(e=(g, m[1]), m=(g, mi), cat=m[2], side=side, t=t, end=m[4], p=p, hb=hbe,
                      fol=(1 if fl & 2 else 0) - p - m[7] * p * (1 - p)))
    del blob


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


out = {"rows": len(R)}
for side in ("NO", "YES"):
    first = {}
    for r in sorted((r for r in R if r["side"] == side), key=lambda r: r["t"]):
        first.setdefault(r["m"], r)
    F = list(first.values())
    if not F:
        out[side] = {"n": 0}; continue
    ends = sorted(r["end"] for r in F); mid = ends[len(ends) // 2]
    s0 = stat(F)
    hv = {h: stat([r for r in F if (r["end"] < mid) == (h == "older")]) for h in ("older", "newer")}
    out[side] = s0
    if side == "NO":
        out["  split_at"] = str(dt.datetime.fromtimestamp(mid, dt.timezone.utc))
        for h, v in hv.items():
            out[f"  {h} half"] = v
        out["  1-12 h before end"] = stat([r for r in F if r["hb"] < 12])
        out["  12-48 h before end"] = stat([r for r in F if r["hb"] >= 12])
        out["  NO 0.05-0.50"] = stat([r for r in F if r["p"] <= 0.5])
        out["  NO 0.50-0.90"] = stat([r for r in F if r["p"] > 0.5])
        for c_, _n in collections.Counter(r["cat"] for r in F).most_common(5):
            out[f"  cat {c_}"] = stat([r for r in F if r["cat"] == c_])
        ok = (s0.get("events", 0) >= 40 and s0["pts"] > 3 and s0["ci"][0] > 0 and all(v.get("pts", -1) > 0 for v in hv.values())
              and (s0.get("top_event_share") or 1) < 0.25)
        out["verdict"] = "PASS" if ok else "FAIL"
print(json.dumps(out, indent=1))
json.dump(out, open(f"{B}culture_endno_report.json", "w"), indent=1)
