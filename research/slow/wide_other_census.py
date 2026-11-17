"""Cycle 28: two pre-registered tape tests (rules fixed here BEFORE looking at outcomes). No orders, read-only on our own files.

N64 (adjacent to N58 / N59 / N62): WIDE-EVENT LAUNCH-HOUR NO OUTSIDE CULTURE.
  N58 (culture launch-hour NO) may be structural: a new multi-outcome event lists N seed books near 0.50, so the YES side sums to >> 1
  until the event is looked at. If that is the mechanism, it should also work in wide NON-culture events (who will be named / which
  country / which date), even though all launches together (N59) were +0.3. Unit = event. Market = in the event's original batch
  (first trade < E0 + 1 h), event has >= 6 original-batch markets, launch hour of the market, NO side, follower fill a300 (next
  same-direction print by someone else >= 300 s later), price 0.05-0.95, fee rate*p(1-p), one fill per market, lives >= 24 h.
  DEAD if <= +1 pt, or event interval bottom < -1, or halves (by launch) disagree in sign, or < 40 events.
  Also printed (diagnostics, not decisions): culture wide vs narrow (where N58's edge sits), non-culture narrow (2-5).

N65 (outside the box): THE CATCH-ALL OUTCOME ('Other', 'another', 'none', 'no one', 'someone else').
  Fans bid named candidates; the field bucket has no fan base and is the one outcome nobody researches. Hypothesis: YES on the
  catch-all is under-priced. Exposed to 2 (it may be cheap because the named field really covers it), 11 (path vs end: the catch-all
  resolves at the end, so use finished markets only), 5/6 (one event = one bet), 22 (rule fixed here).
  Market = question matches the catch-all regex, its event has >= 4 markets in the tape, finished inside the tape. Arm = entries 6-168 h
  before the end, follower a300, price 0.03-0.97, fee; one fill per market (the first in the arm). YES is the decision side:
  DEAD if <= +1 pt, or event interval bottom < -1, or halves (by end date) disagree in sign, or < 30 events. NO side printed too."""
import json, gzip, struct, collections, random, re, datetime as dt
ROW = struct.Struct("<IIIhfffHHHIB")
B = "data/research/"
random.seed(64)
CULT = {"mention", "movies", "music", "youtube", "awards", "pop-culture"}
OTHER = re.compile(r"\b(other|another|none of|no one|nobody|someone else|anyone else|not listed|field)\b", re.I)
L64 = []; L65 = []
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
    EW = collections.Counter(MK[mi][1] for mi, l in L.items() if l < E0[MK[mi][1]] + 3600)  # original-batch width
    for t, mi, wi, hb, S, C, F, a, a60, a300, lag, fl in ROW.iter_unpack(blob):
        m = MK[mi]; l0 = L[mi]; e = m[1]
        if m[4] >= at or S <= 0:
            continue
        win = 1 if fl & 2 else 0; yes = bool(fl & 1); p = a300 / 1e4
        fee = m[7] * p * (1 - p)
        # N64
        if (hb >= 1 and m[4] - l0 >= 86400 and E0[e] >= t0 + 7 * 86400 and l0 < E0[e] + 3600 and t - l0 < 3600
                and not yes and 0.05 <= p <= 0.95):
            L64.append(dict(g=g, cult=m[2] in CULT, cat=m[2], e=e, m=(g, mi), w=EW[e], l0=l0, t=t, fol=win - p - fee))
        # N65
        if EN[e] >= 4 and OTHER.search(m[3] or "") and 6 <= (m[4] - t) / 3600 <= 168 and 0.03 <= p <= 0.97:
            L65.append(dict(g=g, cat=m[2], e=e, m=(g, mi), yes=yes, end=m[4], t=t, fol=win - p - fee, q=m[3][:90], p=p, win=win))
    del blob


def first(rows):
    seen = {}
    for r in sorted(rows, key=lambda r: r["t"]):
        seen.setdefault(r["m"], r)
    return list(seen.values())


def stat(rows):
    ev = collections.defaultdict(lambda: [0.0, 0])
    for r in rows:
        ev[r["e"]][0] += r["fol"]; ev[r["e"]][1] += 1
    v = list(ev.values()); n = sum(y[1] for y in v)
    out = {"n": n, "events": len(v)}
    if len(v) < 5:
        return out
    bs = []
    for _ in range(1000):
        s = [v[int(random.random() * len(v))] for _i in v]
        bs.append(sum(y[0] for y in s) / max(1, sum(y[1] for y in s)))
    bs.sort()
    out.update(pts=round(100 * sum(y[0] for y in v) / n, 2), ci=[round(100 * bs[25], 1), round(100 * bs[974], 1)],
               events_pos=sum(1 for y in v if y[0] > 0))
    return out


def halves(rows, key):
    if not rows:
        return {}
    xs = sorted(r[key] for r in rows); mid = xs[len(xs) // 2]
    return {"older": stat([r for r in rows if r[key] < mid]), "newer": stat([r for r in rows if r[key] >= mid])}


def weeks(rows, key):
    w = collections.defaultdict(list)
    for r in rows:
        w[time_week(r[key])].append(r)
    return {k: stat(v).get("pts") for k, v in sorted(w.items())}


def time_week(x):
    return dt.datetime.utcfromtimestamp(x).strftime("%m-%d")[:4] + str((dt.datetime.utcfromtimestamp(x).day - 1) // 7)


def verdict(s, h, min_ev):
    if s.get("events", 0) < min_ev or "pts" not in s:
        return "DEAD (too few events)"
    hs = [h.get(k, {}).get("pts") for k in ("older", "newer")]
    if s["pts"] <= 1 or s["ci"][0] < -1 or None in hs or (hs[0] > 0) != (hs[1] > 0):
        return "DEAD"
    return "PASSED"


R = {}
a = first(L64)
nc_wide = [r for r in a if not r["cult"] and r["w"] >= 6]
R["N64 non-culture wide (>= 6) launch-hour NO [DECISION]"] = s = stat(nc_wide)
R["N64 halves"] = h = halves(nc_wide, "l0")
R["N64 verdict"] = verdict(s, h, 40)
R["N64 by category"] = {c: stat([r for r in nc_wide if r["cat"] == c]) for c in sorted({r["cat"] for r in nc_wide})}
R["diag non-culture narrow (2-5)"] = stat([r for r in a if not r["cult"] and 2 <= r["w"] <= 5])
R["diag non-culture single (1)"] = stat([r for r in a if not r["cult"] and r["w"] == 1])
R["diag culture wide (>= 6)"] = stat([r for r in a if r["cult"] and r["w"] >= 6])
R["diag culture narrow (2-5)"] = stat([r for r in a if r["cult"] and 2 <= r["w"] <= 5])
R["diag culture single (1)"] = stat([r for r in a if r["cult"] and r["w"] == 1])

b = first(L65)
y = [r for r in b if r["yes"]]; n = [r for r in b if not r["yes"]]
R["N65 catch-all YES 6-168 h [DECISION]"] = s = stat(y)
R["N65 halves (by end)"] = h = halves(y, "end")
R["N65 verdict"] = verdict(s, h, 30)
R["N65 YES avg price / win rate"] = [round(sum(r["p"] for r in y) / max(1, len(y)), 3), round(sum(r["win"] for r in y) / max(1, len(y)), 3)]
R["N65 YES by category"] = {c: stat([r for r in y if r["cat"] == c]) for c in sorted({r["cat"] for r in y})}
R["N65 YES price < 0.20 / >= 0.20"] = [stat([r for r in y if r["p"] < 0.2]), stat([r for r in y if r["p"] >= 0.2])]
R["N65 catch-all NO"] = stat(n); R["N65 NO halves"] = halves(n, "end")
R["N65 example questions"] = sorted({r["q"] for r in b})[:25]
json.dump(R, open(f"{B}wide_other_report.json", "w"), indent=1)
print(json.dumps(R, indent=1))
