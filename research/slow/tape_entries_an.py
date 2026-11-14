"""12-week taker ENTRIES (one row per wallet x market x direction): who wins, by category and entry size; and do wallets persist?
Edge in points per share = win - avg price - fee; P&L % of cost; event-clustered bootstrap."""
import json, gzip, struct, sys, collections, random, datetime as dt, os
ROW = struct.Struct("<IIIhfffHHHIB")
B = os.environ.get("ORD_DIR", "data/research/")
groups = sys.argv[1] if len(sys.argv) > 1 else "ac"
E = []
for g in groups:
    meta = json.load(gzip.open(f"{B}entries_{g}_meta.json.gz")); blob = gzip.open(f"{B}entries_{g}.bin.gz").read()
    MK = meta["markets"]; WL = meta["wallets"]
    at = dt.datetime.strptime(meta["at"], "%Y-%m-%d %H:%M").replace(tzinfo=dt.timezone.utc).timestamp(); cut = at - 45 * 86400
    print(f"group {g}: markets {len(MK)} entries {len(blob) // ROW.size:,}")
    for t, mi, wi, hb, S, C, F, a, a60, a300, lag, fl in ROW.iter_unpack(blob):
        m = MK[mi]
        if S <= 0 or C <= 0:
            continue
        E.append((m[1], m[2], (g, wi), hb, S, C, F, a / 1e4, a60 / 1e4, fl & 2 and 1 or 0, m[7], m[4] >= cut, fl & 1, (g, mi), t))
print("entries:", len(E))
random.seed(5)
# fields: 0 e, 1 cat, 2 w, 3 hb, 4 S, 5 C, 6 F, 7 a_first, 8 a60, 9 win, 10 fee, 11 new6, 12 yes, 13 market, 14 t


def boot(ev):
    v = list(ev.values()); n = len(v)
    if n < 8:
        return float("nan"), float("nan")
    bs = []
    for _ in range(600):
        s = c = 0.0
        for _i in range(n):
            x = v[int(random.random() * n)]; s += x[0]; c += x[1]
        bs.append(s / c if c else 0)
    bs.sort()
    return bs[15], bs[584]


def pnl_pct(R):                                                  # taker P&L after fees as % of cost (volume-weighted)
    ev = collections.defaultdict(lambda: [0.0, 0.0])
    for r in R:
        ev[r[0]][0] += r[4] * r[9] - r[5] - r[6]; ev[r[0]][1] += r[5]
    if not ev:
        return "n 0"
    lo, hi = boot(ev); tot = sum(x[1] for x in ev.values())
    return f"n {len(R):7} ev {len(ev):4} cost ${tot / 1e6:6.2f}M  {100 * sum(x[0] for x in ev.values()) / tot:+6.2f}% [{100 * lo:+5.1f},{100 * hi:+5.1f}]"


def pts(R, follower=False):                                      # equal weight per entry, points per share
    ev = collections.defaultdict(lambda: [0.0, 0])
    for r in R:
        if follower:
            p = r[8]
            if not (0.03 <= p <= 0.97):
                continue
            x = r[9] - p - r[10] * p * (1 - p)
        else:
            p = r[5] / r[4]
            if not (0.03 <= p <= 0.97):
                continue
            x = r[9] - p - r[6] / r[4]
        ev[r[0]][0] += x; ev[r[0]][1] += 1
    n = sum(x[1] for x in ev.values())
    if n < 30:
        return f"n {n}"
    lo, hi = boot(ev)
    return f"n {n:7} ev {len(ev):4} {100 * sum(x[0] for x in ev.values()) / n:+6.2f} [{100 * lo:+5.1f},{100 * hi:+5.1f}]"


pre = [r for r in E if r[3] >= 1]
print(f"\n== A. all taker entries opened >= 1 h before the scheduled end ({len(pre):,}): taker P&L after fees, % of cost, by category")
for c in sorted({r[1] for r in pre}):
    R = [r for r in pre if r[1] == c]
    print(f"   {c:12} {pnl_pct(R)}   | newest 6 weeks {pnl_pct([r for r in R if r[11]])[18:]} | older {pnl_pct([r for r in R if not r[11]])[18:]}")
print("   live (opened in the last hour before / after the scheduled end):")
for c in sorted({r[1] for r in E}):
    print(f"   {c:12} {pnl_pct([r for r in E if r[1] == c and r[3] < 1])}")
print("\n== B. by entry size (wallet's total cost in that market and direction), pre-event: % of cost | points per entry (equal weight) | follower at next print")
for lo, hi in ((0, 10), (10, 50), (50, 200), (200, 1000), (1000, 5000), (5000, 1e12)):
    R = [r for r in pre if lo <= r[5] < hi]
    print(f"   ${lo:>5,}+ {pnl_pct(R)} | {pts(R)} | f60 {pts(R, True)}")
print("\n== C. by price of the first trade (pre-event): % of cost | points per entry")
for lo, hi in ((0.0, 0.05), (0.05, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 0.95), (0.95, 1.01)):
    R = [r for r in pre if lo <= r[7] < hi]
    print(f"   {lo:.2f}-{hi:.2f} {pnl_pct(R)} | YES side {pnl_pct([r for r in R if r[12]])[10:]} | NO side {pnl_pct([r for r in R if not r[12]])[10:]}")

print("\n== D. wallet persistence, walk-forward: wallets scored on markets that ended BEFORE the cut (older 6 weeks), their entries in the newer 6 weeks")
old = collections.defaultdict(lambda: [0.0, 0.0, 0, 0.0, set()])   # pnl, cost, n, sum pts, events
for r in pre:
    if not r[11]:
        o = old[r[2]]; o[0] += r[4] * r[9] - r[5] - r[6]; o[1] += r[5]; o[2] += 1; o[3] += r[9] - r[5] / r[4] - r[6] / r[4]; o[4].add(r[0])
new = [r for r in pre if r[11]]
print(f"   wallets with entries in the older half: {len(old):,}; with >= 20 entries over >= 5 events: {sum(1 for o in old.values() if o[2] >= 20 and len(o[4]) >= 5):,}")
for lab, f in (("top: >= 20 entries, >= 5 events, P&L >= +10% of cost and >= +3 pts/entry", lambda o: o[2] >= 20 and len(o[4]) >= 5 and o[0] / o[1] >= 0.10 and o[3] / o[2] >= 0.03),
               ("good: >= 20 entries, >= 5 events, P&L > 0 and pts > 0", lambda o: o[2] >= 20 and len(o[4]) >= 5 and o[0] > 0 and o[3] > 0),
               ("bad: >= 20 entries, >= 5 events, P&L <= -10% and <= -3 pts/entry", lambda o: o[2] >= 20 and len(o[4]) >= 5 and o[0] / o[1] <= -0.10 and o[3] / o[2] <= -0.03),
               ("whales: >= $50k cost in the older half, P&L > +5%", lambda o: o[1] >= 5e4 and o[0] / o[1] > 0.05),
               ("whales: >= $50k cost, P&L < -5%", lambda o: o[1] >= 5e4 and o[0] / o[1] < -0.05)):
    W = {w for w, o in old.items() if f(o)}
    R = [r for r in new if r[2] in W]
    print(f"   {lab}: {len(W)} wallets")
    print(f"      newer half: % of cost {pnl_pct(R)} | pts per entry {pts(R)} | follower f60 {pts(R, True)}")
    for c in sorted({r[1] for r in R}):
        Rc = [r for r in R if r[1] == c]
        if len(Rc) >= 200:
            print(f"         {c:12} {pnl_pct(Rc)} | pts {pts(Rc)} | f60 {pts(Rc, True)}")
R = [r for r in new if r[2] not in old]
print(f"   wallets not seen in the older half: % of cost {pnl_pct(R)} | pts {pts(R)} | f60 {pts(R, True)}")
