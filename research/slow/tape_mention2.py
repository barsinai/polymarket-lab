"""Mention markets: a blanket, executable rule. For every market take the FIRST taker fill on a side (pre-event, in a price band and
time window) - a price that really existed, with no choice among moments - and hold to resolution. One position per market.
Edge = win - price - fee (points per share); ROI per $; bootstrap over events; split by half of the sample and by speaker."""
import json, gzip, struct, collections, random, re, sys, datetime as dt
ROW = struct.Struct("<IIIhfffHHHIB")
B = "data/research/"
CAT = sys.argv[1] if len(sys.argv) > 1 else "mention"; G = sys.argv[2] if len(sys.argv) > 2 else "a"
meta = json.load(gzip.open(f"{B}entries_{G}_meta.json.gz")); blob = gzip.open(f"{B}entries_{G}.bin.gz").read(); MK = meta["markets"]
at = dt.datetime.strptime(meta["at"], "%Y-%m-%d %H:%M").replace(tzinfo=dt.timezone.utc).timestamp(); cut = at - 45 * 86400
random.seed(6)
first = {}                                                       # (market, side, rule) -> (t, price)
RULES = {"NO <= 0.50": (0, 0.05, 0.50), "NO 0.05-0.20": (0, 0.05, 0.20), "NO 0.20-0.35": (0, 0.20, 0.35), "NO 0.35-0.50": (0, 0.35, 0.50), "NO 0.50-0.70": (0, 0.50, 0.70),
         "NO 0.70-0.95": (0, 0.70, 0.95), "YES 0.50-0.95": (1, 0.50, 0.95), "YES 0.05-0.50": (1, 0.05, 0.50)}
WINS = {"any time >= 1 h before": (1, 10 ** 6), ">= 24 h before": (24, 10 ** 6), "1-24 h before": (1, 24)}
for t, mi, wi, hb, S, C, F, a, a60, a300, lag, fl in ROW.iter_unpack(blob):
    m = MK[mi]
    if m[2] != CAT:
        continue
    p = a / 1e4
    for rn, (side, lo, hi) in RULES.items():
        if (fl & 1) != side or not (lo <= p < hi):
            continue
        for wn, (h0, h1) in WINS.items():
            if h0 <= hb < h1:
                k = (mi, rn, wn)
                if k not in first or t < first[k][0]:
                    first[k] = (t, p, 1 if fl & 2 else 0)


def kind(slug):
    s = slug or ""
    return "trump" if "trump" in s else "earnings" if re.search(r"earnings|-q[1-4]-|quarter", s) else "other"


def stat(K, minn=20):
    if len(K) < minn:
        return f"n {len(K):5}"
    ev = collections.defaultdict(lambda: [0.0, 0.0, 0])
    for mi, p, w in K:
        m = MK[mi]; x = w - p - m[7] * p * (1 - p)
        e = ev[m[1]]; e[0] += x; e[1] += x / p; e[2] += 1
    v = list(ev.values()); n = len(v); N = len(K); bs = []; br = []
    for _ in range(1000):
        s = s2 = c = 0.0
        for _i in range(n):
            x = v[int(random.random() * n)]; s += x[0]; s2 += x[1]; c += x[2]
        bs.append(s / c); br.append(s2 / c)
    bs.sort(); br.sort()
    return (f"n {N:5} ev {n:3} paid {sum(k[1] for k in K) / N:.3f} won {sum(k[2] for k in K) / N:.3f} edge {100 * sum(x[0] for x in v) / N:+6.2f} pts [{100 * bs[25]:+5.1f},{100 * bs[974]:+5.1f}] "
            f"ROI {100 * sum(x[1] for x in v) / N:+6.1f}% [{100 * br[25]:+6.1f},{100 * br[974]:+6.1f}]  events > 0: {sum(1 for x in v if x[0] > 0)}/{n}")


print(f"{CAT}: markets {sum(1 for m in MK if m[2] == CAT)}")
for wn in WINS:
    print(f"\n== first taker fill per market, {wn} the scheduled start")
    for rn in RULES:
        K = [(k[0], v[1], v[2]) for k, v in first.items() if k[1] == rn and k[2] == wn]
        print(f"   {rn:14} {stat(K)}")
rn, wn = "NO <= 0.50", "any time >= 1 h before"
K = [(k[0], v[1], v[2]) for k, v in first.items() if k[1] == rn and k[2] == wn]
print(f"\n== the rule '{rn}', {wn}: robustness")
print("   newest 6 weeks:", stat([k for k in K if MK[k[0]][4] >= cut])); print("   older 6 weeks :", stat([k for k in K if MK[k[0]][4] < cut]))
for kd in ("trump", "earnings", "other"):
    print(f"   {kd:9}: {stat([k for k in K if kind(MK[k[0]][1]) == kd])}")
byw = collections.defaultdict(list)
for k in K:
    byw[dt.datetime.fromtimestamp(MK[k[0]][4], dt.timezone.utc).strftime("%G-W%V")].append(k)
print("   by week of the event:")
for w in sorted(byw):
    L = byw[w]; x = [k[2] - k[1] - MK[k[0]][7] * k[1] * (1 - k[1]) for k in L]
    print(f"      {w} n {len(L):4} events {len({MK[k[0]][1] for k in L}):3} paid {sum(k[1] for k in L) / len(L):.3f} won {sum(k[2] for k in L) / len(L):.3f} edge {100 * sum(x) / len(x):+6.2f} pts  ROI {100 * sum(v / k[1] for v, k in zip(x, L)) / len(L):+6.1f}%")
ev = collections.defaultdict(lambda: [0.0, 0])
for k in K:
    e = ev[MK[k[0]][1]]; e[0] += (k[2] - k[1] - MK[k[0]][7] * k[1] * (1 - k[1])) / k[1]; e[1] += 1
top = sorted(ev.items(), key=lambda kv: kv[1][0])
print("   worst events ($1 per market):", [(k[:40], v[1], round(v[0], 1)) for k, v in top[:5]])
print("   best events:", [(k[:40], v[1], round(v[0], 1)) for k, v in top[-5:]])
tot = sum(v[0] for v in ev.values()); print(f"   total P&L at $1 per market: {tot:+.1f} on {len(K)} bets; without the best 5 events: {tot - sum(v[0] for k, v in top[-5:]):+.1f}; without the best 20: {tot - sum(v[0] for k, v in top[-20:]):+.1f}")
print("\n== halves x kind, rule NO <= 0.50 (>= 1 h before)")
for kd in ("trump", "earnings", "other"):
    for lab, f in (("older 6 wk", lambda k: MK[k[0]][4] < cut), ("newest 6 wk", lambda k: MK[k[0]][4] >= cut)):
        print(f"   {kd:9} {lab:11}: {stat([k for k in K if kind(MK[k[0]][1]) == kd and f(k)], 10)}")
for rn2, wn2 in (("YES 0.50-0.95", "1-24 h before"), ("YES 0.50-0.95", "any time >= 1 h before"), ("NO 0.50-0.70", "any time >= 1 h before"), ("NO 0.05-0.20", ">= 24 h before")):
    K2 = [(k[0], v[1], v[2]) for k, v in first.items() if k[1] == rn2 and k[2] == wn2]
    print(f"== {rn2}, {wn2}: older {stat([k for k in K2 if MK[k[0]][4] < cut])}\n   {'':28} newest {stat([k for k in K2 if MK[k[0]][4] >= cut])}")
# how do NO-favoured events end? share of markets resolving NO per event, by half
evn = collections.defaultdict(lambda: [0, 0, 0])
for m in MK:
    if m[2] == CAT:
        e = evn[m[1]]; e[0] += 1; e[1] += 1 - int(m[6]); e[2] = m[4]
allno = [(k, v) for k, v in evn.items() if v[0] >= 5 and v[1] == v[0]]
print(f"\nevents with >= 5 markets: {sum(1 for v in evn.values() if v[0] >= 5)}; where EVERY market resolved NO: {len(allno)} (older half {sum(1 for k, v in allno if v[2] < cut)}, newest {sum(1 for k, v in allno if v[2] >= cut)})")
print("   e.g.", [k[:60] for k, v in allno[:12]])
yr = lambda L: sum(v[0] - v[1] for v in L) / max(sum(v[0] for v in L), 1)   # noqa: E731
print(f"   share of markets resolving YES: older half {yr([v for v in evn.values() if v[2] < cut]):.3f}, newest half {yr([v for v in evn.values() if v[2] >= cut]):.3f}")
print("\n== last-day rule: first NO fill per market, 1-24 h before the start")
for rn2 in ("NO <= 0.50", "NO 0.20-0.35", "NO 0.35-0.50", "NO 0.50-0.70", "NO 0.70-0.95", "YES 0.05-0.50"):
    K2 = [(k[0], v[1], v[2]) for k, v in first.items() if k[1] == rn2 and k[2] == "1-24 h before"]
    print(f"   {rn2:14} older  {stat([k for k in K2 if MK[k[0]][4] < cut])}\n   {'':14} newest {stat([k for k in K2 if MK[k[0]][4] >= cut])}")
