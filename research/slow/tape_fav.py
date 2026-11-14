"""Near-certain outcomes bought by real takers (12 weeks, real fills): does the favourite pay in TALLY markets (resolved by a public
running number: leaderboards, charts, box office, counts) vs OPINION / NEWS markets?
Unit = one market + side; price = mean first-trade price of the takers who entered that side in the band and time window (real
prints at the ask); edge = win - price - fee (points per share); ROI = edge / price. Bootstrap over events.
Families are slug patterns fixed BEFORE looking at their results."""
import json, gzip, struct, sys, collections, re, random, datetime as dt, os
ROW = struct.Struct("<IIIhfffHHHIB")
B = os.environ.get("ORD_DIR", "data/research/")
groups = sys.argv[1] if len(sys.argv) > 1 else "ac"
TALLY = [("AI leaderboards", r"best-ai|ai-lab|ai-model|ai-agent|arena|livebench|openrouter|chinese-ai|ai-company"),
         ("app-store ranks", r"app-store"), ("GPU rental index", r"gpu-rental"),
         ("box office", r"box-office|domestic-gross|opening-weekend|worldwide-gross|grossing"),
         ("music charts", r"billboard|spotify|hot-100|top-song|top-album|apple-music|monthly-listeners"),
         ("views / streams counts", r"views|subscribers|mrbeast|streams"), ("review scores", r"rotten-tomatoes|metacritic|imdb|letterboxd"),
         ("netflix / streaming charts", r"netflix|top-10|top-show|top-movie"), ("tweet counts", r"of-tweets|tweets-"),
         ("largest company / market cap", r"largest-company|market-cap"), ("weather", r"temperature|highest-temp|precipitation|rainfall|snow|hurricane")]
random.seed(3)
U = collections.defaultdict(lambda: [0.0, 0, None])              # (market, yes, band, window) -> [sum price, n, info]
BANDS = ((0.80, 0.90), (0.90, 0.95), (0.95, 0.98), (0.98, 0.995)); WIN = ((1, 24), (24, 72), (72, 168), (168, 720))
for g in groups:
    try:
        meta = json.load(gzip.open(f"{B}entries_{g}_meta.json.gz")); blob = gzip.open(f"{B}entries_{g}.bin.gz").read()
    except Exception as e:  # noqa: BLE001
        print("missing", g, e); continue
    MK = meta["markets"]
    fam = {}
    for i, m in enumerate(MK):
        s = (m[1] or "").lower()
        fam[i] = next((n for n, rx in TALLY if re.search(rx, s)), None) or ("weather" if m[2] == "weather" else None)
    for t, mi, wi, hb, S, C, F, a, a60, a300, lag, fl in ROW.iter_unpack(blob):
        p = a / 1e4
        b = next((x for x in BANDS if x[0] <= p < x[1]), None); w = next((x for x in WIN if x[0] <= hb < x[1]), None)
        if b is None or w is None:
            continue
        m = MK[mi]
        u = U[(g, mi, fl & 1, b, w)]; u[0] += p; u[1] += 1
        if u[2] is None:
            u[2] = (m[1], m[2], fam[mi], 1 if fl & 2 else 0, m[7], m[3], dt.datetime.fromtimestamp(m[4], dt.timezone.utc).strftime("%Y-%m"))
rows = [(k[3], k[4], u[0] / u[1]) + u[2] for k, u in U.items()]    # band, window, price, event, cat, family, win, fee, q, month
print("market-sides in the bands:", len(rows))


def stat(R, minn=25):
    if len(R) < minn:
        return f"n {len(R):5}"
    ev = collections.defaultdict(lambda: [0.0, 0.0, 0])
    for r in R:
        x = r[6] - r[2] - r[7] * r[2] * (1 - r[2])
        e = ev[r[3]]; e[0] += x; e[1] += x / r[2]; e[2] += 1
    v = list(ev.values()); n = len(v); N = len(R); bs = []; bs2 = []
    for _ in range(800):
        s = s2 = c = 0.0
        for _i in range(n):
            x = v[int(random.random() * n)]; s += x[0]; s2 += x[1]; c += x[2]
        bs.append(s / c); bs2.append(s2 / c)
    bs.sort(); bs2.sort()
    return (f"n {N:5} ev {n:4} price {sum(r[2] for r in R) / N:.3f} won {sum(r[6] for r in R) / N:.3f} edge {100 * sum(x[0] for x in v) / N:+5.2f} pts [{100 * bs[20]:+5.1f},{100 * bs[779]:+5.1f}] "
            f"ROI {100 * sum(x[1] for x in v) / N:+5.2f}% [{100 * bs2[20]:+5.1f},{100 * bs2[779]:+5.1f}] losses {sum(1 for r in R if not r[6])}")


tal = [r for r in rows if r[5]]; opi = [r for r in rows if not r[5]]
for name, R in (("TALLY markets (all families)", tal), ("OPINION / NEWS markets (everything else)", opi)):
    print(f"\n== {name}: favourite side bought by takers, by price band x time before the scheduled end")
    for b in BANDS:
        for w in WIN:
            print(f"   price {b[0]:.2f}-{b[1]:.3f}  {w[0]:>3}-{w[1]:<3} h  {stat([r for r in R if r[0] == b and r[1] == w])}")
        print(f"   price {b[0]:.2f}-{b[1]:.3f}  all windows {stat([r for r in R if r[0] == b])}")
print("\n== tally families, price 0.90-0.98, 24 h - 30 d before the end")
core = lambda r: r[0] in ((0.90, 0.95), (0.95, 0.98)) and r[1][0] >= 24   # noqa: E731
for n, _ in TALLY:
    print(f"   {n:30} {stat([r for r in tal if r[5] == n and core(r)], 10)}")
print(f"   {'ALL TALLY':30} {stat([r for r in tal if core(r)])}")
print(f"   {'ALL OPINION/NEWS':30} {stat([r for r in opi if core(r)])}")
for c in sorted({r[4] for r in opi}):
    print(f"      opinion/news in {c:12} {stat([r for r in opi if r[4] == c and core(r)])}")
print("\n== by month of the market's end, price 0.90-0.98, 24 h - 30 d: tally | opinion/news")
for mth in sorted({r[9] for r in rows}):
    print(f"   {mth}  tally {stat([r for r in tal if r[9] == mth and core(r)], 10)}\n            other {stat([r for r in opi if r[9] == mth and core(r)], 10)}")
print("\n== the losses in tally markets (price 0.90-0.98, 24 h - 30 d)")
for r in sorted([r for r in tal if core(r) and not r[6]], key=lambda r: r[5])[:60]:
    print(f"   {r[5]:28} {r[9]} price {r[2]:.3f} {r[1][0]:>3}-{r[1][1]:<3}h  {r[8][:70]}")
