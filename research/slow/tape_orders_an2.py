"""Decisive test of 'follow big taker orders' on the 12-week order file (data/research/orders_<g>.bin.gz, taker orders >= $100).
Edge = win - price - fee in price points per share; ROI = the same per $ staked (fixed-$ follower). CIs: bootstrap over EVENTS.
In-sample = group a, markets ending in the 6 newest weeks (where the $1,000 rule was found); everything else is out of sample.
usage: orders_an2.py [groups=abc] [min hours before end=1]"""
import json, gzip, struct, sys, collections, random, datetime as dt
R2 = struct.Struct("<IIIhffHHHHHIffB")
import os
B = os.environ.get("ORD_DIR", "data/research/")
groups = sys.argv[1] if len(sys.argv) > 1 else "abc"
HB = float(sys.argv[2]) if len(sys.argv) > 2 else 1
rows = []; cut = None
for g in groups:
    try:
        meta = json.load(gzip.open(f"{B}entries_{g}_meta.json.gz")); blob = gzip.open(f"{B}orders_{g}.bin.gz").read()
    except Exception as e:  # noqa: BLE001
        print("group", g, "missing", e); continue
    MK = meta["markets"]; WL = meta["wallets"]
    at = dt.datetime.strptime(meta["at"], "%Y-%m-%d %H:%M").replace(tzinfo=dt.timezone.utc).timestamp()
    cut = at - (3 + 42) * 86400                                  # markets that ended after this = the 6 newest weeks
    ends = [m[4] for m in MK]
    print(f"group {g}: at {meta['at']} markets {len(MK)} (ends {dt.datetime.fromtimestamp(min(ends), dt.timezone.utc):%m-%d}..{dt.datetime.fromtimestamp(max(ends), dt.timezone.utc):%m-%d}) "
          f"wallets {len(WL)} trades {meta['trades']:,} truncated {meta['truncated_markets']} big orders {len(blob) // R2.size:,}; by category {dict(collections.Counter(m[2] for m in MK))}")
    for t, mi, wi, hb, usd, sh, aavg, amax, aprev, a60, a300, lag, volp, cumw, fl in R2.iter_unpack(blob):
        m = MK[mi]
        rows.append({"t": t, "e": m[1], "cat": m[2], "w": WL[wi], "hb": hb, "usd": usd, "a": aavg / 1e4, "amax": amax / 1e4, "aprev": aprev / 1e4 or None,
                     "a60": a60 / 1e4 or None, "a300": a300 / 1e4 or None, "lag": lag, "volp": volp, "cumw": cumw, "win": 1 if fl & 2 else 0, "yes": fl & 1, "fee": m[7],
                     "mi": (g, mi), "g": g, "new6": m[4] >= cut, "wk": dt.datetime.fromtimestamp(m[4], dt.timezone.utc).strftime("%G-W%V"), "q": m[3], "end": m[4]})
print("big orders loaded:", len(rows))
rows = [r for r in rows if r["hb"] >= HB and 0.03 <= r["a"] <= 0.97]
print(f"kept: >= {HB:g} h before the scheduled end, price 0.03-0.97: {len(rows):,}")
random.seed(7)


def edge(r, key):
    p = r[key]
    if p is None or not (0.03 <= p <= 0.97):
        return None
    return r["win"] - p - r["fee"] * p * (1 - p)


def stat(R, key="a", roi=False, minn=20):
    """mean edge in points per share (or ROI per $ for a fixed-$ stake), events, bootstrap CI over events"""
    X = []
    for r in R:
        x = edge(r, key)
        if x is not None:
            X.append((r["e"], x / r[key] if roi else x))
    if len(X) < minn:
        return f"n {len(X):5} -"
    ev = collections.defaultdict(lambda: [0.0, 0])
    for e, x in X:
        ev[e][0] += x; ev[e][1] += 1
    v = list(ev.values()); n = len(v)
    bs = []
    for _ in range(1000):
        s = c = 0.0
        for _i in range(n):
            a = v[int(random.random() * n)]; s += a[0]; c += a[1]
        bs.append(s / c)
    bs.sort(); mean = sum(a[0] for a in v) / sum(a[1] for a in v)
    return f"n {len(X):5} ev {n:4} {mean * 100:+6.2f} [{bs[25] * 100:+5.1f},{bs[974] * 100:+5.1f}]"


def first_per_day(R):                                            # the tracker's rule: the first order per market + direction + UTC day
    seen = set(); out = []
    for r in sorted(R, key=lambda r: r["t"]):
        k = (r["mi"], r["yes"], r["t"] // 86400)
        if k not in seen:
            seen.add(k); out.append(r)
    return out


SEG = [("IN-SAMPLE  culture, 6 newest weeks", lambda r: r["g"] == "a" and r["new6"]), ("OUT culture, 6 older weeks", lambda r: r["g"] == "a" and not r["new6"]),
       ("OUT weather, 12 weeks", lambda r: r["g"] == "b"), ("OUT economy/tech/geo/politics, 12 weeks", lambda r: r["g"] == "c"),
       ("ALL OUT-OF-SAMPLE", lambda r: not (r["g"] == "a" and r["new6"])), ("ALL", lambda r: True)]
SZ = [(100, 250), (250, 500), (500, 1000), (1000, 2500), (2500, 10000), (10000, 1e12)]
print("\n== 1. edge by order size (points per share): at the taker's own average price | follower at the next same-way print >= 60 s later | >= 300 s")
for lab, f in SEG:
    print(f"-- {lab}")
    for lo, hi in SZ:
        R = [r for r in rows if f(r) and lo <= r["usd"] < hi]
        print(f"   ${lo:>6,.0f}+  own {stat(R)} | f60 {stat(R, 'a60')} | f300 {stat(R, 'a300')}")
    R = [r for r in rows if f(r) and r["usd"] >= 1000]
    print(f"   >= $1,000 own {stat(R)} | f60 {stat(R, 'a60')} | f300 {stat(R, 'a300')} | worst fill {stat(R, 'amax')}")
    F = first_per_day(R)
    print(f"   >= $1,000, first per market+direction+day: own {stat(F)} | f60 {stat(F, 'a60')} | fixed-$ ROI at f60 {stat(F, 'a60', roi=True)}")

big = [r for r in rows if r["usd"] >= 1000]
print(f"\n== 2. orders >= $1,000, all segments (n {len(big)}): does the 'next print' sample flatter the follower?")
print(f"   own edge when a next same-way print exists within 6 h: {stat([r for r in big if r['a60']])} | when none exists: {stat([r for r in big if not r['a60']])}")
sl = sorted(r["a60"] - r["a"] for r in big if r["a60"])
if sl:
    lg = sorted(r["lag"] for r in big if r["a60"])
    print(f"   follower slippage (next print - their average price): p10 {sl[len(sl) // 10]:+.3f} p25 {sl[len(sl) // 4]:+.3f} median {sl[len(sl) // 2]:+.3f} p75 {sl[3 * len(sl) // 4]:+.3f} "
          f"p90 {sl[9 * len(sl) // 10]:+.3f} mean {sum(sl) / len(sl):+.3f}; lag to that print: median {lg[len(lg) // 2]} s, p75 {lg[3 * len(lg) // 4]} s")
    for lab, f in (("slip <= +1c", lambda r: r["a60"] - r["a"] <= 0.01), ("slip +1..+3c", lambda r: 0.01 < r["a60"] - r["a"] <= 0.03), ("slip > +3c", lambda r: r["a60"] - r["a"] > 0.03)):
        print(f"   follower edge when {lab:13}: {stat([r for r in big if r['a60'] and f(r)], 'a60')}")
    for lab, f in (("next print within 5 min", lambda r: r["lag"] <= 300), ("5-60 min", lambda r: 300 < r["lag"] <= 3600), ("1-6 h", lambda r: r["lag"] > 3600)):
        print(f"   follower edge when {lab:23}: {stat([r for r in big if r['a60'] and f(r)], 'a60')}")

print("\n== 3. orders >= $1,000 by category (own | follower 60 s), and >= $500")
for c in sorted({r["cat"] for r in rows}):
    R = [r for r in big if r["cat"] == c]; R5 = [r for r in rows if r["cat"] == c and 500 <= r["usd"] < 1000]
    print(f"   {c:12} >= $1,000: own {stat(R)} | f60 {stat(R, 'a60')}   $500-1,000: own {stat(R5)} | f60 {stat(R5, 'a60')}")

print("\n== 4. orders >= $1,000: cuts (own | follower 60 s)")
CUTS = [("buys YES", lambda r: r["yes"]), ("buys NO", lambda r: not r["yes"]),
        ("price < 0.20", lambda r: r["a"] < 0.2), ("price 0.20-0.50", lambda r: 0.2 <= r["a"] < 0.5), ("price 0.50-0.80", lambda r: 0.5 <= r["a"] < 0.8), ("price >= 0.80", lambda r: r["a"] >= 0.8),
        ("ends in >= 72 h", lambda r: r["hb"] >= 72), ("ends in 24-72 h", lambda r: 24 <= r["hb"] < 72), ("ends in 6-24 h", lambda r: 6 <= r["hb"] < 24), ("ends in 1-6 h", lambda r: r["hb"] < 6),
        ("order >= 20% of the market's volume so far", lambda r: r["usd"] >= 0.2 * (r["volp"] + r["usd"])),
        ("order 5-20% of volume so far", lambda r: 0.05 * (r["volp"] + r["usd"]) <= r["usd"] < 0.2 * (r["volp"] + r["usd"])),
        ("order < 5% of volume so far", lambda r: r["usd"] < 0.05 * (r["volp"] + r["usd"])),
        ("pushes the price >= 2c above the previous same-way print", lambda r: r["aprev"] and r["a"] - r["aprev"] >= 0.02),
        ("within 2c of the previous same-way print", lambda r: r["aprev"] and abs(r["a"] - r["aprev"]) < 0.02),
        ("buys >= 2c below the previous same-way print (a dip)", lambda r: r["aprev"] and r["a"] - r["aprev"] <= -0.02),
        ("sweep: worst fill >= 2c above the average", lambda r: r["amax"] - r["a"] >= 0.02),
        ("wallet's first big order here (< $100 before)", lambda r: r["cumw"] < 100), ("wallet adding (>= $1,000 in already)", lambda r: r["cumw"] >= 1000)]
for lab, f in CUTS:
    R = [r for r in big if f(r)]
    print(f"   {lab:58} own {stat(R)} | f60 {stat(R, 'a60')}")

print("\n== 5. orders >= $1,000 by week of the market's end (own | follower 60 s)")
for w in sorted({r["wk"] for r in big}):
    R = [r for r in big if r["wk"] == w]
    print(f"   {w} own {stat(R, minn=10)} | f60 {stat(R, 'a60', minn=10)}")

print("\n== 6. concentration (orders >= $1,000, follower at f60)")
F = [(r, edge(r, "a60")) for r in big]; F = [(r, x) for r, x in F if x is not None]
tot = sum(x for _, x in F)
for name, key in (("event", "e"), ("wallet", "w")):
    agg = collections.defaultdict(lambda: [0.0, 0])
    for r, x in F:
        agg[r[key]][0] += x; agg[r[key]][1] += 1
    top = sorted(agg.items(), key=lambda kv: -kv[1][0])
    print(f"   by {name}: {len(agg)} distinct; sum of follower edge {tot:+.1f} share-points; top 5 give {sum(v[0] for _, v in top[:5]):+.1f}, top 20 {sum(v[0] for _, v in top[:20]):+.1f}; "
          f"worst 5 {sum(v[0] for _, v in top[-5:]):+.1f}; {name}s with a positive sum {sum(1 for _, v in top if v[0] > 0)}/{len(top)}")
    for k, v in top[:6] + top[-3:]:
        print(f"      {str(k)[:60]:60} n {v[1]:4} sum {v[0]:+7.1f} mean {v[0] / v[1] * 100:+6.1f} pts")
    without = [r for r, x in F if r[key] not in {k for k, _ in top[:5]}]
    print(f"      follower edge without the top 5 {name}s: {stat(without, 'a60')}")

# wallet persistence on big orders: wallets ranked on the older half, scored on the newer half
print("\n== 7. do the same wallets keep winning? wallets ranked by their big orders (>= $500) in markets ending BEFORE the cut, scored on markets ending after")
b5 = [r for r in rows if r["usd"] >= 500]
old = collections.defaultdict(list)
for r in b5:
    if not r["new6"]:
        old[r["w"]].append(edge(r, "a"))
good = {w for w, L in old.items() if len(L) >= 5 and sum(L) / len(L) > 0.03}; bad = {w for w, L in old.items() if len(L) >= 5 and sum(L) / len(L) < -0.03}
new = [r for r in b5 if r["new6"]]
print(f"   wallets with >= 5 big orders in the older half: {sum(1 for L in old.values() if len(L) >= 5)}; winners (> +3 pts) {len(good)}, losers (< -3 pts) {len(bad)}")
print(f"   newer half, orders of earlier winners: own {stat([r for r in new if r['w'] in good])} | f60 {stat([r for r in new if r['w'] in good], 'a60')}")
print(f"   newer half, orders of earlier losers : own {stat([r for r in new if r['w'] in bad])} | f60 {stat([r for r in new if r['w'] in bad], 'a60')}")
print(f"   newer half, wallets not seen before  : own {stat([r for r in new if r['w'] not in old])} | f60 {stat([r for r in new if r['w'] not in old], 'a60')}")
