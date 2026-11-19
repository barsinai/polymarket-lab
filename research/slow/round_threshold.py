"""Cycle 43, N94 (outside the box: never used the NUMBER in the question). Round-number salience: do crowds overpay for YES on
'reach / above / N+' thresholds that are round (one significant digit: 10, 50, 300, 1,000, $2m, 100k) vs the same kind of question
with a non-round threshold (15, 125, 2.5m)? Story: round milestones are what headlines and fans talk about ('BTC 100k', '1 billion
views'), so YES there carries an attention premium and NO is cheap.
Rules fixed BEFORE looking. Rows: tape groups a + c, finished markets, ex-mention (mention counts are small integers, all 'round'),
question has an UPWARD threshold word (above / over / more than / greater than / at least / exceed / reach / hit / N+ / or more)
followed by one number >= 10 (k / m / b / % suffix allowed). Entry = first taker entry per market and side anywhere in the market's
life, follower fill a300 (next print the same way >= 300 s later), 0.05-0.95, fee = rate * p(1-p). Unit = event slug (bootstrap 1,000);
halves by end date.
DECISION: PASS if ROUND NO >= +3 pts, CI low > 0, >= 30 events, both halves > 0, and ROUND NO - OTHER NO >= +2. Otherwise DEAD.
Exposed to 13 (the threshold is public), 22 (one split fixed here), 24 (halves), 5/6 (ladders: one event = one bet), 9."""
import json, gzip, struct, collections, random, re, datetime as dt
ROW = struct.Struct("<IIIhfffHHHIB")
B = "data/research/"
random.seed(94)
RE = re.compile(r"(?:above|over|more than|greater than|at least|exceed(?:s)?|reach(?:es)?|hit(?:s)?)\s+\$?([\d][\d,]*\.?\d*)\s*(k|m|b|million|billion|%)?|\$?([\d][\d,]*\.?\d*)\s*(k|m|b|%)?\s*(?:\+|or more)", re.I)


def thr(q):
    m = RE.search(q)
    if not m: return None
    s = (m[1] or m[3] or "").replace(",", "")
    try: v = float(s)
    except ValueError: return None
    if v < 10 and "." not in s: return None
    if v < 10: return None
    digits = s.replace(".", "").strip("0") if "." in s else s.rstrip("0")
    digits = digits.lstrip("0")
    return "ROUND" if len(digits) == 1 else "OTHER"


R = []
for g in "ac":
    meta = json.load(gzip.open(f"{B}entries_{g}_meta.json.gz")); MK = meta["markets"]
    at = dt.datetime.strptime(meta["at"], "%Y-%m-%d %H:%M").replace(tzinfo=dt.timezone.utc).timestamp()
    kind = {mi: thr(m[3]) for mi, m in enumerate(MK) if m[2] != "mention" and m[4] < at}
    blob = gzip.open(f"{B}entries_{g}.bin.gz").read()
    first = {}
    for t, mi, wi, hb, S, C, F, a, a60, a300, lag, fl in ROW.iter_unpack(blob):
        k0 = kind.get(mi)
        if not k0 or S <= 0 or C <= 0: continue
        p = a300 / 1e4
        if not 0.05 <= p <= 0.95: continue
        side = "YES" if fl & 1 else "NO"; m = MK[mi]
        k = (g, mi, side)
        if k in first and first[k]["t"] <= t: continue
        first[k] = dict(t=t, e=(g, m[1]), side=side, end=m[4], cat=m[2], kind=k0, p=p, q=m[3],
                        f=(1 if fl & 2 else 0) - p - m[7] * p * (1 - p))
    R += first.values(); del blob


def stat(rr):
    ev = collections.defaultdict(lambda: [0.0, 0])
    for r in rr: ev[r["e"]][0] += r["f"]; ev[r["e"]][1] += 1
    v = list(ev.values()); n = sum(y[1] for y in v)
    if not n: return {"n": 0, "events": 0}
    o = {"n": n, "events": len(v), "pts": round(100 * sum(y[0] for y in v) / n, 2), "avg_p": round(sum(r["p"] for r in rr) / n, 3)}
    if len(v) >= 5:
        bs = sorted(sum(y[0] for y in s) / max(1, sum(y[1] for y in s)) for s in ([v[int(random.random() * len(v))] for _ in v] for _ in range(1000)))
        o["ci"] = [round(100 * bs[25], 1), round(100 * bs[974], 1)]
    return o


ends = sorted(r["end"] for r in R); mid = ends[len(ends) // 2]
out = {"rows": len(R), "split_at": str(dt.datetime.fromtimestamp(mid, dt.timezone.utc)),
       "examples ROUND": [r["q"] for r in R if r["kind"] == "ROUND"][:4], "examples OTHER": [r["q"] for r in R if r["kind"] == "OTHER"][:4]}
for kd in ("ROUND", "OTHER"):
    for side in ("NO", "YES"):
        sel = [r for r in R if r["kind"] == kd and r["side"] == side]
        out[f"{kd} {side}"] = stat(sel)
        out[f"  {kd} {side} older"] = stat([r for r in sel if r["end"] < mid]); out[f"  {kd} {side} newer"] = stat([r for r in sel if r["end"] >= mid])
        if side == "NO":
            out[f"  {kd} NO by cat"] = {c: stat([r for r in sel if r["cat"] == c]) for c in sorted({r["cat"] for r in sel})}
n = out["ROUND NO"]
ok = (n.get("events", 0) >= 30 and n.get("pts", -99) >= 3 and n.get("ci", [-1])[0] > 0 and out["  ROUND NO older"].get("pts", -1) > 0
      and out["  ROUND NO newer"].get("pts", -1) > 0 and n["pts"] - out["OTHER NO"].get("pts", 0) >= 2)
out["verdict"] = "PASS -> paper arm" if ok else "DEAD"
print(json.dumps(out, indent=1))
json.dump(out, open(f"{B}round_threshold_report.json", "w"), indent=1)
