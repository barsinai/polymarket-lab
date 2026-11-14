"""Cheap-side bids, second look (6-week raw tapes). A bot that keeps its bid pegged one tick above the LIVE best bid would be hit
by the next taker 'towards the favourite' at that print's own cheap price + tick (the print shows where the best bid was).
RT rule: the first such print in the band starts the peg, the NEXT one (>= 60 s later) fills us at its price + one tick,
whatever direction the price moved in between. One fill per market side. Also: all later prints, split by the move since the
previous print (did someone raise the bid, or is it falling?)."""
import json, gzip, collections, random, sys
cats = ["youtube", "movies", "mention", "music", "awards", "tweets"]
CAPP = float(sys.argv[1]) if len(sys.argv) > 1 else 0.10
random.seed(8); RT = []; ALL = []
for cat in cats:
    for l in gzip.open(f"data/research/tape_raw_{cat}.jsonl.gz", "rt"):
        m = json.loads(l)
        rows = sorted(r for r in m["rows"] if r[0] <= m["end"] - 3600)
        for side in (0, 1):
            ycheap = m["y0"] if side == 0 else 1 - m["y0"]
            prev = None; filled = False
            for t, buy, oi, p, s, w in rows:
                if buy and oi != side:
                    c = 1 - p
                elif (not buy) and oi == side:
                    c = p
                else:
                    continue
                if not (0.003 <= c <= CAPP):
                    prev = None; continue
                tick = 0.001 if c < 0.04 else 0.01
                if prev is not None and t >= prev[1] + 60:
                    mv = "up" if c > prev[0] + 1e-9 else "down" if c < prev[0] - 1e-9 else "flat"
                    rec = (m["e"], cat, c + tick, ycheap, (m["end"] - t) / 3600, mv, buy, c)
                    ALL.append(rec)
                    if not filled:
                        filled = True; RT.append(rec)
                if prev is None or t >= prev[1] + 60:
                    prev = (c, t)


def stat(R, minn=25):
    if len(R) < minn:
        return f"n {len(R):6}"
    ev = collections.defaultdict(lambda: [0.0, 0.0, 0])
    for r in R:
        e = ev[r[0]]; e[0] += r[3] - r[2]; e[1] += r[2]; e[2] += 1
    v = list(ev.values()); n = len(v); bs = []; br = []
    for _ in range(1000):
        s = c = k = 0.0
        for _i in range(n):
            x = v[int(random.random() * n)]; s += x[0]; c += x[1]; k += x[2]
        bs.append(s / k); br.append(s / c)
    bs.sort(); br.sort(); N = len(R); cost = sum(r[2] for r in R); pnl = sum(r[3] - r[2] for r in R)
    return (f"n {N:6} ev {n:3} bid {cost / N:.3f} won {sum(r[3] for r in R) / N:.3f} edge {100 * pnl / N:+5.2f} pts [{100 * bs[25]:+5.1f},{100 * bs[974]:+5.1f}] "
            f"return {100 * pnl / cost:+6.1f}% [{100 * br[25]:+6.1f},{100 * br[974]:+6.1f}]")


print(f"cheap side <= {CAPP}")
print("== RT (live peg, first fill per market side):", stat(RT))
for lo, hi in ((0.003, 0.02), (0.02, 0.04), (0.04, 0.07), (0.07, 0.111)):
    print(f"   bid {lo:.3f}-{hi:.3f}: {stat([r for r in RT if lo <= r[2] < hi])}")
for mv in ("up", "flat", "down"):
    print(f"   price since the previous print: {mv:5} {stat([r for r in RT if r[5] == mv])}")
print("   filled by a favourite BUY:", stat([r for r in RT if r[6]])); print("   filled by a SALE of the cheap token:", stat([r for r in RT if not r[6]]))
for lab, f in ((">= 7 d before the end", lambda r: r[4] >= 168), ("1-7 d", lambda r: 24 <= r[4] < 168), ("< 24 h", lambda r: r[4] < 24)):
    print(f"   {lab:22}: {stat([r for r in RT if f(r)])}")
print("== every print after the first (many per market side; weight = prints):", stat(ALL))
for mv in ("up", "flat", "down"):
    print(f"   {mv:5} {stat([r for r in ALL if r[5] == mv])}")
print("   one tick subtracted? no: at the print's own price (what the real maker paid):")
ALL0 = [r[:2] + (r[7],) + r[3:] for r in ALL]
for mv in ("up", "flat", "down"):
    print(f"   {mv:5} {stat([r for r in ALL0 if r[5] == mv])}")
print("   SALES of the cheap token only, at the print's own price:", stat([r for r in ALL0 if not r[6]]), "\n   favourite BUYS only:", stat([r for r in ALL0 if r[6]]))
