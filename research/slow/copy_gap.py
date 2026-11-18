"""Cycle 36, N80 (adjacent to COPY-1): does the copy edge survive only when the price has NOT run away from the sharp wallet?
COPY-1 buys at the ask if it is <= the wallet's price + 3c. The 12-week tape said the follower at the next print keeps only
+0.5 of the wallet's +1.6 pts. Question: is that +0.5 an average of 'no move -> edge kept' and 'price ran -> edge gone',
so that a tighter cap (gap <= +1c) keeps a real edge? Or does a small gap mean the market did not believe the wallet
(lesson 2: a cheap price that survives is cheap for a reason)?
Rules fixed BEFORE looking (tape_entries_an.py section D walk-forward, groups a + c, pre-event entries hb >= 1):
  wallets = 'good' on markets that ended before the cut (>= 20 entries, >= 5 events, P&L > 0 and pts > 0);
  their entries in the newer 6 weeks; follower price f = next same-way print by someone else >= 300 s later (a300), 0.03-0.97;
  gap = f - wallet's first-trade price; buckets <= 0, (0, 1c], (1c, 3c], (3c, 10c], > 10c.
  Edge = win - f - fee_rate * f (1 - f), equal weight per entry, event-clustered bootstrap (unit = event slug).
  Placebo: the same buckets for wallets NOT in the good set (does a small gap help everyone?).
  Halves = newer 6 weeks split at its middle by entry time.
DECISION: 'tight cap' arm worth adding to the COPY-1 report only if gap <= 1c (buckets <= 0 and (0,1c] pooled) is >= +1.5 pts with
CI low > 0 on >= 100 events, positive in both halves, AND exceeds the placebo's same bucket by >= +1 pt; if <= +0.5 -> DEAD
(the cap is not where an edge hides). Exposed to: 1 (we are minutes late), 2, 5, 22 (one split, fixed here), 24 (halves)."""
import json, gzip, struct, collections, random, datetime as dt
ROW = struct.Struct("<IIIhfffHHHIB")
B = "data/research/"
random.seed(80)
E = []
for g in "ac":
    meta = json.load(gzip.open(f"{B}entries_{g}_meta.json.gz")); MK = meta["markets"]
    at = dt.datetime.strptime(meta["at"], "%Y-%m-%d %H:%M").replace(tzinfo=dt.timezone.utc).timestamp(); cut = at - 45 * 86400
    for t, mi, wi, hb, S, C, F, a, a60, a300, lag, fl in ROW.iter_unpack(gzip.open(f"{B}entries_{g}.bin.gz").read()):
        m = MK[mi]
        if S <= 0 or C <= 0 or hb < 1 or m[4] >= at:
            continue
        E.append((m[1], (g, wi), S, C, F, a / 1e4, a300 / 1e4, 1 if fl & 2 else 0, m[7], m[4] >= cut, t))
print("pre-event entries", len(E))
old = collections.defaultdict(lambda: [0.0, 0.0, 0, 0.0, set()])
for e, w, S, C, F, a, f, win, fr, new, t in E:
    if not new:
        o = old[w]; o[0] += S * win - C - F; o[1] += C; o[2] += 1; o[3] += win - C / S - F / S; o[4].add(e)
GOOD = {w for w, o in old.items() if o[2] >= 20 and len(o[4]) >= 5 and o[0] > 0 and o[3] > 0}
NEW = [r for r in E if r[9] and 0.03 <= r[6] <= 0.97 and 0.03 <= r[5] <= 0.97]
tmid = sorted(r[10] for r in NEW)[len(NEW) // 2]
print("good wallets", len(GOOD), "newer-half follower rows", len(NEW))


def stat(R):
    ev = collections.defaultdict(lambda: [0.0, 0])
    for r in R:
        f = r[6]; ev[r[0]][0] += r[7] - f - r[8] * f * (1 - f); ev[r[0]][1] += 1
    v = list(ev.values()); n = sum(x[1] for x in v)
    if len(v) < 10:
        return {"n": n, "events": len(v)}
    bs = []
    for _ in range(500):
        s = c = 0
        for _i in range(len(v)):
            x = v[int(random.random() * len(v))]; s += x[0]; c += x[1]
        bs.append(s / c)
    bs.sort()
    return {"n": n, "events": len(v), "pts": round(100 * sum(x[0] for x in v) / n, 2), "ci": [round(100 * bs[12], 1), round(100 * bs[487], 1)]}


BK = [("<=0", -9, 0.00001), ("0-1c", 0.00001, 0.01001), ("1-3c", 0.01001, 0.03001), ("3-10c", 0.03001, 0.10001), (">10c", 0.10001, 9)]
out = {}
for lab, sel in (("good", lambda r: r[1] in GOOD), ("placebo_others", lambda r: r[1] not in GOOD)):
    R = [r for r in NEW if sel(r)]
    d = {"all": stat(R)}
    for b, lo, hi in BK:
        d[b] = stat([r for r in R if lo <= r[6] - r[5] < hi])
    T = [r for r in R if r[6] - r[5] < 0.01001]
    d["gap<=1c"] = stat(T); d["gap<=1c_h1"] = stat([r for r in T if r[10] < tmid]); d["gap<=1c_h2"] = stat([r for r in T if r[10] >= tmid])
    d["gap<=3c (COPY-1 cap)"] = stat([r for r in R if r[6] - r[5] < 0.03001])
    out[lab] = d
for k, d in out.items():
    print(k)
    for b, s in d.items():
        print(f"  {b:22} {s}")
g, p = out["good"]["gap<=1c"], out["placebo_others"]["gap<=1c"]
ok = (g.get("events", 0) >= 100 and g.get("pts", -99) >= 1.5 and g["ci"][0] > 0 and out["good"]["gap<=1c_h1"].get("pts", -9) > 0
      and out["good"]["gap<=1c_h2"].get("pts", -9) > 0 and g["pts"] - p.get("pts", 0) >= 1)
verdict = "TIGHT-CAP ARM" if ok else ("DEAD" if g.get("pts", -99) <= 0.5 else "UNCLEAR")
out["verdict"] = verdict
print("VERDICT", verdict)
json.dump(out, open(f"{B}copy_gap_report.json", "w"), indent=1)
