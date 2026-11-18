"""Cycle 38, N84 (adjacent to COPY-1 / N80): does the copy edge live in markets that end >= 24 h after the entry?
COPY-1 paper (in-sample, 74 settled): sharp primaries ending < 24 h -4.0 pts (47 / 34 events), 1-7 d +17.1 (21 / 15), 7-60 d +11.2 (6).
Mechanism: in a market that ends within hours the sharp wallet's information is about to become public, so the price runs
before the follower arrives (lesson 1); a multi-day market leaves time for the follower to share in a slow-to-spread view.
Rules fixed BEFORE looking (same walk-forward as copy_gap.py, groups a + c, pre-event entries):
  wallets = 'good' on markets that ended before the cut (>= 20 entries, >= 5 events, P&L > 0 and pts > 0);
  their entries in the newer 6 weeks; follower price f = next same-way print by someone else >= 300 s later, 0.03-0.97,
  COPY-1 cap: f - wallet price <= +3c; horizon = hours before end at the wallet's entry (hb): <24 h, 1-7 d, 7-60 d, > 60 d.
  Edge = win - f - fee, equal weight per entry, event-clustered bootstrap. Placebo: the same split for non-good wallets.
DECISION: an '>= 24 h' COPY-1 arm is worth a split in the paper report only if hb 24-1439 is >= +1.5 pts, CI low > 0, >= 100 events,
positive in both halves and >= +1 pt above the placebo's same bucket; <= +0.5 -> DEAD. Exposed to 1, 5, 22 (split taken from the
paper after looking - the tape is the out-of-sample check), 24."""
import json, gzip, struct, collections, random, datetime as dt
ROW = struct.Struct("<IIIhfffHHHIB")
B = "data/research/"
random.seed(84)
E = []
for g in "ac":
    meta = json.load(gzip.open(f"{B}entries_{g}_meta.json.gz")); MK = meta["markets"]
    at = dt.datetime.strptime(meta["at"], "%Y-%m-%d %H:%M").replace(tzinfo=dt.timezone.utc).timestamp(); cut = at - 45 * 86400
    for t, mi, wi, hb, S, C, F, a, a60, a300, lag, fl in ROW.iter_unpack(gzip.open(f"{B}entries_{g}.bin.gz").read()):
        m = MK[mi]
        if S <= 0 or C <= 0 or hb < 1 or m[4] >= at:
            continue
        E.append((m[1], (g, wi), S, C, F, a / 1e4, a300 / 1e4, 1 if fl & 2 else 0, m[7], m[4] >= cut, t, hb, m[2]))
old = collections.defaultdict(lambda: [0.0, 0.0, 0, 0.0, set()])
for r in E:
    e, w, S, C, F, a, f, win, fr, new, t = r[:11]
    if not new:
        o = old[w]; o[0] += S * win - C - F; o[1] += C; o[2] += 1; o[3] += win - C / S - F / S; o[4].add(e)
GOOD = {w for w, o in old.items() if o[2] >= 20 and len(o[4]) >= 5 and o[0] > 0 and o[3] > 0}
NEW = [r for r in E if r[9] and 0.03 <= r[6] <= 0.97 and 0.03 <= r[5] <= 0.97 and r[6] - r[5] < 0.03001]
tmid = sorted(r[10] for r in NEW)[len(NEW) // 2]
print("good wallets", len(GOOD), "newer-half capped follower rows", len(NEW))


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


BK = [("<24h", 1, 24), ("1-7d", 24, 168), ("7-60d", 168, 1440), (">60d", 1440, 99999), ("24h-60d", 24, 1440)]
out = {}
for lab, sel in (("good", lambda r: r[1] in GOOD), ("placebo_others", lambda r: r[1] not in GOOD)):
    R = [r for r in NEW if sel(r)]
    d = {"all": stat(R)}
    for b, lo, hi in BK:
        d[b] = stat([r for r in R if lo <= r[11] < hi])
    T = [r for r in R if 24 <= r[11] < 1440]
    d["24h-60d_h1"] = stat([r for r in T if r[10] < tmid]); d["24h-60d_h2"] = stat([r for r in T if r[10] >= tmid])
    d["24h-60d_ex_weather"] = stat([r for r in T if r[12] != "weather"])
    out[lab] = d
for k, d in out.items():
    print(k)
    for b, s in d.items():
        print(f"  {b:22} {s}")
g, p = out["good"]["24h-60d"], out["placebo_others"]["24h-60d"]
ok = (g.get("events", 0) >= 100 and g.get("pts", -99) >= 1.5 and g["ci"][0] > 0 and out["good"]["24h-60d_h1"].get("pts", -9) > 0
      and out["good"]["24h-60d_h2"].get("pts", -9) > 0 and g["pts"] - p.get("pts", 0) >= 1)
verdict = "HORIZON ARM" if ok else ("DEAD" if g.get("pts", -99) <= 0.5 else "UNCLEAR")
out["verdict"] = verdict
print("VERDICT", verdict)
json.dump(out, open(f"{B}copy_horizon_report.json", "w"), indent=1)
