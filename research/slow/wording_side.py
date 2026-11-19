"""Cycle 40, N89 (outside the box): does the YES premium belong to the TOKEN or to the DRAMA?
The tape says YES buyers lose and NO buyers win at launch (launch_report: follower YES -2.0, NO +2.0). Two stories:
  token bias - people like buying 'YES' tickets whatever the question says -> YES is rich even when YES = 'nothing happens';
  drama bias - people overbet that SOMETHING happens -> where the question is negated / 'stays' / 'remains', YES (= nothing
               happens) should be CHEAP and buying it should win.
We never used the question's wording. Rules fixed BEFORE looking.
Rows: tape groups a (culture, ex-mention) and c (politics / economy / tech / geopolitics), finished markets (end < tape date),
market lives >= 48 h after its first trade L. Entry window = mid-life: market age >= 24 h and >= 24 h before the scheduled end
(so neither the launch effect nor the last-day tail). Per market and side, the FIRST taker entry that way in the window; the
follower buys that side at the next print the same way >= 300 s later (a300), 0.05-0.95, fee = rate * p(1-p).
Wording class of the question text (meta keeps the first 70 chars):
  NEG  : not / n't / no longer / without / fail to / miss
  STAY : remain / stay / still / keep / hold / survive / retain / continue / again
  AFF  : everything else (LOW-side thresholds like 'below/under/fewer' are their own diagnostic class, not status quo).
Unit = event slug (bootstrap 1,000); halves by end date.
DECISION (drama bias -> tracker 'buy YES on NEG+STAY mid-life'): YES side on NEG+STAY >= +3 pts, CI low > 0, >= 40 events, both
halves > 0. Token bias is the reading if NEG+STAY YES <= -1 (then the NO side there is the reference). Otherwise DEAD/flat.
Exposed to: 13 (a public fact - wording - may already be priced), 22 (one split fixed here), 24 (halves), 5/6 (events), 11 (only
finished markets), 7 (a text feature; but it targets a behavioural mechanism, not a fit)."""
import json, gzip, struct, collections, random, re, datetime as dt
ROW = struct.Struct("<IIIhfffHHHIB")
B = "data/research/"
random.seed(89)
NEG = re.compile(r"\b(not|no longer|without|fail to|fails to|miss|misses)\b|n't\b", re.I)
STAY = re.compile(r"\b(remain|remains|stay|stays|still|keep|keeps|hold|holds|survive|survives|retain|retains|continue|continues|again)\b", re.I)
LOW = re.compile(r"\b(below|under|fewer|less than|lower than|at most|or less|or lower)\b", re.I)


def wclass(q):
    if NEG.search(q):
        return "NEG"
    if STAY.search(q):
        return "STAY"
    if LOW.search(q):
        return "LOW"
    return "AFF"


R = []
for g in "ac":
    meta = json.load(gzip.open(f"{B}entries_{g}_meta.json.gz")); MK = meta["markets"]
    at = dt.datetime.strptime(meta["at"], "%Y-%m-%d %H:%M").replace(tzinfo=dt.timezone.utc).timestamp()
    blob = gzip.open(f"{B}entries_{g}.bin.gz").read()
    L = {}
    for t, mi, *_ in ROW.iter_unpack(blob):
        if mi not in L or t < L[mi]:
            L[mi] = t
    first = {}
    for t, mi, wi, hb, S, C, F, a, a60, a300, lag, fl in ROW.iter_unpack(blob):
        m = MK[mi]
        if m[2] == "mention" or m[4] >= at or S <= 0 or C <= 0:
            continue
        l0 = L[mi]
        if m[4] - l0 < 48 * 3600 or t - l0 < 24 * 3600 or m[4] - t < 24 * 3600:
            continue
        p = a300 / 1e4
        if not 0.05 <= p <= 0.95:
            continue
        side = "YES" if fl & 1 else "NO"
        k = (g, mi, side)
        if k in first and first[k]["t"] <= t:
            continue
        won = 1 if fl & 2 else 0   # bit 2 = the token of this direction won (tape_entries.py)
        first[k] = dict(t=t, e=(g, m[1]), side=side, end=m[4], cat=m[2], w=wclass(m[3]), p=p,
                        f=won - p - m[7] * p * (1 - p))
    R += first.values()
    del blob


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
    return {"n": n, "events": len(v), "pts": round(100 * sum(y[0] for y in v) / n, 2),
            "ci": [round(100 * bs[25], 1), round(100 * bs[974], 1)], "avg_p": round(sum(r["p"] for r in rr) / n, 3)}


mid = sorted(r["end"] for r in R)[len(R) // 2]
out = {"rows": len(R), "split_at": str(dt.datetime.fromtimestamp(mid, dt.timezone.utc)),
       "classes (markets)": dict(collections.Counter(r["w"] for r in R if r["side"] == "YES"))}
for side in ("YES", "NO"):
    for w in ("AFF", "NEG", "STAY", "LOW", "NEG+STAY"):
        sel = [r for r in R if r["side"] == side and (r["w"] in ("NEG", "STAY") if w == "NEG+STAY" else r["w"] == w)]
        out[f"{side} {w}"] = stat(sel)
        if w == "NEG+STAY":
            for h in ("older", "newer"):
                out[f"  {side} {w} {h}"] = stat([r for r in sel if (r["end"] < mid) == (h == "older")])
            out[f"  {side} {w} by group"] = {g: stat([r for r in sel if r["e"][0] == g]) for g in "ac"}
out["examples NEG+STAY"] = sorted({r["e"][1] for r in R if r["w"] in ("NEG", "STAY")})[:15]
y = out["YES NEG+STAY"]
ok = (y.get("events", 0) >= 40 and y["pts"] >= 3 and y["ci"][0] > 0 and
      out["  YES NEG+STAY older"].get("pts", -1) > 0 and out["  YES NEG+STAY newer"].get("pts", -1) > 0)
out["verdict"] = "PASS (drama bias)" if ok else ("token bias (YES rich even when YES = nothing happens)"
                                                 if y.get("pts") is not None and y["pts"] <= -1 else "DEAD (flat)")
print(json.dumps(out, indent=1))
json.dump(out, open(f"{B}wording_side_report.json", "w"), indent=1)
