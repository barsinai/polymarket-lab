"""Calibration at EXECUTABLE prices from the 12-week taker tape: for every market side and price band, the mean price takers paid
on their first trade (pre-event) vs how often that side won. Unit = market + side + band; bootstrap over events.
Taker edge = win - price - fee. The maker who filled them has the mirror position: (1 - price) for a share that pays 1 - win."""
import json, gzip, struct, sys, collections, random, datetime as dt, os
ROW = struct.Struct("<IIIhfffHHHIB")
B = os.environ.get("ORD_DIR", "data/research/")
groups = sys.argv[1] if len(sys.argv) > 1 else "ac"; HMIN = float(sys.argv[2]) if len(sys.argv) > 2 else 1
BANDS = [(0.005, 0.02), (0.02, 0.05), (0.05, 0.10), (0.10, 0.20), (0.20, 0.35), (0.35, 0.50), (0.50, 0.65), (0.65, 0.80), (0.80, 0.90), (0.90, 0.95), (0.95, 0.98), (0.98, 0.995)]
random.seed(11)
U = {}
for g in groups:
    try:
        meta = json.load(gzip.open(f"{B}entries_{g}_meta.json.gz")); blob = gzip.open(f"{B}entries_{g}.bin.gz").read()
    except Exception as e:  # noqa: BLE001
        print("missing", g, e); continue
    MK = meta["markets"]
    for t, mi, wi, hb, S, C, F, a, a60, a300, lag, fl in ROW.iter_unpack(blob):
        if hb < HMIN:
            continue
        p = a / 1e4
        b = next((x for x in BANDS if x[0] <= p < x[1]), None)
        if b is None:
            continue
        k = (g, mi, fl & 1, b); u = U.get(k)
        if u is None:
            m = MK[mi]
            u = U[k] = [0.0, 0, m[1], m[2], 1 if fl & 2 else 0, m[7], dt.datetime.fromtimestamp(m[4], dt.timezone.utc).strftime("%Y-%m"), 0.0]
        u[0] += p; u[1] += 1; u[7] += C
rows = [(k[3], u[0] / u[1], u[2], u[3], u[4], u[5], u[6], u[7], k[2]) for k, u in U.items()]   # band, price, event, cat, win, fee, month, taker cost, yes
print(f"groups {groups}, entries opened >= {HMIN:g} h before the scheduled end; market-side-band units: {len(rows):,}")


def stat(R, minn=30):
    if len(R) < minn:
        return f"n {len(R):6}"
    ev = collections.defaultdict(lambda: [0.0, 0.0, 0, 0.0])
    for r in R:
        x = r[4] - r[1] - r[5] * r[1] * (1 - r[1]); mk = (r[1] - r[4]) / (1 - r[1])           # maker ROI on the capital he posts (1 - price)
        e = ev[r[2]]; e[0] += x; e[1] += mk; e[2] += 1; e[3] += r[1] - r[4]
    v = list(ev.values()); n = len(v); N = len(R); bs = []; bm = []
    for _ in range(800):
        s = s2 = c = 0.0
        for _i in range(n):
            x = v[int(random.random() * n)]; s += x[0]; s2 += x[1]; c += x[2]
        bs.append(s / c); bm.append(s2 / c)
    bs.sort(); bm.sort()
    return (f"n {N:6} ev {n:4} paid {sum(r[1] for r in R) / N:.3f} won {sum(r[4] for r in R) / N:.3f} taker {100 * sum(x[0] for x in v) / N:+5.2f} pts [{100 * bs[20]:+5.1f},{100 * bs[779]:+5.1f}]"
            f" | maker {100 * sum(x[3] for x in v) / N:+5.2f} pts = {100 * sum(x[1] for x in v) / N:+6.1f}% of his stake [{100 * bm[20]:+6.1f},{100 * bm[779]:+6.1f}]")


print("\n== all categories: what takers paid vs what happened, by price band of the side they bought")
for b in BANDS:
    print(f"   {b[0]:.3f}-{b[1]:.3f}  {stat([r for r in rows if r[0] == b])}")
FAV = lambda r: r[0][0] >= 0.90   # noqa: E731
print("\n== takers buying the favourite at 0.90-0.995 (the maker holds the long shot), by category")
for c in sorted({r[3] for r in rows}):
    print(f"   {c:12} {stat([r for r in rows if r[3] == c and FAV(r)])}")
print("   by month of the market's end:")
for mth in sorted({r[6] for r in rows}):
    print(f"   {mth}      {stat([r for r in rows if r[6] == mth and FAV(r)])}")
print("   by side: favourite = NO", stat([r for r in rows if FAV(r) and not r[8]]))
print("            favourite = YES", stat([r for r in rows if FAV(r) and r[8]]))
print("\n== takers buying the long shot at 0.02-0.10, by category")
LS = lambda r: 0.02 <= r[0][0] < 0.10   # noqa: E731
for c in sorted({r[3] for r in rows}):
    print(f"   {c:12} {stat([r for r in rows if r[3] == c and LS(r)])}")
print("   long shot = YES", stat([r for r in rows if LS(r) and r[8]]))
print("   long shot = NO ", stat([r for r in rows if LS(r) and not r[8]]))
