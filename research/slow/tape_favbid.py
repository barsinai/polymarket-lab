"""N28 (cycle 12): rest a bid on the FAVOURITE (0.94-0.985) instead of taking its ask. Raw public tape (mention + awards: the only
raw tapes in the repo). Live peg, as tape_bidsim2.py does for the cheap side: the first favourite-SELLING print in the band starts the
peg; the NEXT one >= 60 s later fills us at its price + one tick (that print shows where the best bid was). Selling prints = a taker
sells the favourite, or buys the other outcome (matched against a favourite bid at 1 - p). One fill per market side; maker pays no fee.
Edge = won - bid, in points per share, bootstrap clustered by event; split by end-date halves and weeks (LESSONS 23, 24).
Rows within 1 h of the end are dropped (resolution-time noise)."""
import json, gzip, collections, random, datetime, os
CATS = os.environ.get("CATS", "mention,awards").split(",")   # c13: N31 replication on categories never looked at
REPORT = os.environ.get("REPORT", "data/research/tape_favbid_report.json")
random.seed(12)
LO, HI = 0.94, 0.985
SPLIT = datetime.datetime(2026, 10, 1, tzinfo=datetime.timezone.utc).timestamp()
RT = []; ALL = []
for cat in CATS:
    for l in gzip.open(f"data/research/tape_raw_{cat}.jsonl.gz", "rt"):
        m = json.loads(l)
        rows = sorted(r for r in m["rows"] if r[0] <= m["end"] - 3600)
        for side in (0, 1):
            yf = m["y0"] if side == 0 else 1 - m["y0"]
            prev = None; filled = False
            for t, buy, oi, p, s, w in rows:
                if (not buy) and oi == side:
                    c = p                      # taker sells the favourite into a bid
                elif buy and oi != side:
                    c = 1 - p                  # taker buys the other side = sells the favourite
                else:
                    continue
                if not (LO <= c <= HI):
                    prev = None; continue
                tick = 0.001 if c >= 0.96 else 0.01
                if prev is not None and t >= prev[1] + 60:
                    mv = "up" if c > prev[0] + 1e-9 else "down" if c < prev[0] - 1e-9 else "flat"
                    rec = (m["e"], cat, min(c + tick, 0.999), yf, (m["end"] - t) / 3600, mv, m["end"], t)
                    ALL.append(rec)
                    if not filled:
                        filled = True; RT.append(rec)
                if prev is None or t >= prev[1] + 60:
                    prev = (c, t)


def stat(R, minn=20):
    if len(R) < minn:
        return f"n {len(R)}"
    ev = collections.defaultdict(lambda: [0.0, 0.0, 0])
    for r in R:
        e = ev[r[0]]; e[0] += r[3] - r[2]; e[1] += r[2]; e[2] += 1
    v = list(ev.values()); n = len(v); bs = []
    for _ in range(2000):
        s = k = 0.0
        for _i in range(n):
            x = v[int(random.random() * n)]; s += x[0]; k += x[2]
        bs.append(s / k)
    bs.sort(); N = len(R); pnl = sum(r[3] - r[2] for r in R)
    return (f"n {N:5} ev {n:4} bid {sum(r[2] for r in R) / N:.3f} won {sum(r[3] for r in R) / N:.3f} losses {sum(1 - r[3] for r in R):3} "
            f"edge {100 * pnl / N:+5.2f} pts [{100 * bs[50]:+5.1f},{100 * bs[1949]:+5.1f}]")


out = []
P = lambda *a: out.append(" ".join(str(x) for x in a))
P("== live peg, first fill per market side:", stat(RT))
P("   halves by end date: Aug-Sep", stat([r for r in RT if r[6] < SPLIT]), "| Oct-Nov", stat([r for r in RT if r[6] >= SPLIT]))
for cat in CATS:
    P(f"   {cat:8}", stat([r for r in RT if r[1] == cat], 5))
for lo, hi in ((0.94, 0.96), (0.96, 0.98), (0.98, 1.0)):
    P(f"   bid {lo}-{hi}:", stat([r for r in RT if lo <= r[2] < hi], 5))
for mv in ("up", "flat", "down"):
    P(f"   price since previous selling print {mv:5}", stat([r for r in RT if r[5] == mv], 5))
for lab, f in ((">= 7 d before end", lambda r: r[4] >= 168), ("1-7 d", lambda r: 24 <= r[4] < 168), ("< 24 h", lambda r: r[4] < 24)):
    P(f"   {lab:18}", stat([r for r in RT if f(r)], 5))
wk = collections.defaultdict(list)
for r in RT:
    wk[datetime.datetime.utcfromtimestamp(r[6]).strftime("%G-W%V")].append(r)
for k in sorted(wk):
    v = wk[k]; P(f"   week {k}: n {len(v):4} losses {sum(1 - r[3] for r in v):3} edge {100 * sum(r[3] - r[2] for r in v) / len(v):+6.2f} pts")
P("== N29 pre-registered rule (1 h - 7 d before the end, no fill right after a lower selling print):",
  stat([r for r in RT if r[4] < 168 and r[5] != "down"], 5))
P("== every later selling print (weight = prints):", stat(ALL))
print("\n".join(out))
json.dump({"lines": out}, open(REPORT, "w"), indent=1)
