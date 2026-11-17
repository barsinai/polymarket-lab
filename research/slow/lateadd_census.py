"""Cycle 27, N62 (adjacent to N58 / N59): LATE-ADDED OUTCOMES. Rules fixed here BEFORE looking at outcomes.

Idea: multi-outcome events (who will win / be named / which film...) get new outcome markets added days after the event lists
(a new candidate, a new title, 'Other' split up). The added market launches with a seed book while the event's traders are
looking at the old favourites; fans of the new name buy YES. N58 found launch-hour NO works on CULTURE launches in general; N59
found nothing across all launches. Question here: is a late-added outcome a better, wider (all categories) version - or nothing?
Exposed to: 1 (seed snipers: follower >= 300 s), 2, 22 (found by analogy -> rule fixed here), 24 (halves), 5/6 (unit = event),
13 (the rest of the event's book already shows where the money is).

Data: 12-week public trade tape (entries_a/b/c). L = first trade of a market in the tape. Event E0 = min L over its markets.
Only events with E0 >= tape start + 7 d (event itself launched inside the tape: no censoring) and >= 3 markets in the tape.
LATE-ADD market: L >= E0 + 24 h. ORIGINAL market: L < E0 + 1 h. Markets must live >= 24 h after L.
Arms (entries >= 1 h before the end), launch hour of the market (L <= t < L + 1 h), follower fill = next same-direction print by
someone else >= 300 s later (a300), price 0.05-0.95, fee = rate * p(1-p). Points per share = win - price - fee, unit = event.
DECISION: LATE-ADD, NO side, ALL categories except group a's culture (= N58 already covers culture launches):
  DEAD if <= +1 pt, or event interval bottom < -1, or halves (by L) disagree in sign, or < 40 events.
  Reported also: culture late-adds (does it add to N58?), YES side, ORIGINAL launch hour NO (control), late-add 24-72 h NO."""
import json, gzip, struct, collections, random, datetime as dt
ROW = struct.Struct("<IIIhfffHHHIB")
B = "data/research/"
random.seed(62)
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
                      fol=win - p - m[7] * p * (1 - p), delay_h=(l0 - E0[e]) / 3600))
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


out = {"rows": len(R), "late_markets": len({r["m"] for r in R if r["kind"] == "LATE"}), "split_at": str(dt.datetime.fromtimestamp(mid, dt.timezone.utc))}
out["DECISION late-add NO launch hour, non-culture"] = stat(sel("LATE", "launch hour", False, cult=False))
for h in ("older", "newer"):
    out[f"  {h} half"] = stat(sel("LATE", "launch hour", False, cult=False, half=h))
for g in "abc":
    out[f"  group {g}"] = stat([r for r in sel("LATE", "launch hour", False, cult=False) if r["g"] == g])
out["late-add NO launch hour, culture"] = stat(sel("LATE", "launch hour", False, cult=True))
out["late-add YES launch hour, non-culture"] = stat(sel("LATE", "launch hour", True, cult=False))
out["late-add YES launch hour, culture"] = stat(sel("LATE", "launch hour", True, cult=True))
out["original NO launch hour, non-culture (control)"] = stat(sel("ORIG", "launch hour", False, cult=False))
out["original NO launch hour, culture (N58-like)"] = stat(sel("ORIG", "launch hour", False, cult=True))
out["late-add NO 24-72 h, non-culture"] = stat(sel("LATE", "24-72 h", False, cult=False))
cats = collections.Counter(r["cat"] for r in sel("LATE", "launch hour", False, cult=False))
for c_, _n in cats.most_common(8):
    out[f"  cat {c_}"] = stat([r for r in sel("LATE", "launch hour", False, cult=False) if r["cat"] == c_])
print(json.dumps(out, indent=1))
json.dump(out, open(f"{B}lateadd_report.json", "w"), indent=1)
