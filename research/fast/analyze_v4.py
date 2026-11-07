"""Offline scoring of the v4 observations (exact feed) against actual results. Read-only.
Usage: python research/fast/analyze_v4.py   (needs data/fast/obs.jsonl, trades.jsonl, windows.jsonl, results*.json)"""
import json, math, os
from collections import defaultdict
from statistics import NormalDist

D = "data/fast"
N = NormalDist()
res = {}
for f in ("results.json",):
    try:
        res.update(json.load(open(f"{D}/{f}")))
    except OSError:
        pass
try:
    for s, md in json.load(open(f"{D}/results_meta.json")).items():
        if md.get("up") is not None:
            res[s] = md["up"]
except OSError:
    pass
for t in (json.loads(l) for l in open(f"{D}/trades.jsonl")):
    if t.get("result") is not None:
        res[t["slug"]] = (t["result"] == 1) if t["side"] == "Up" else (t["result"] == 0)
O = [o for o in (json.loads(l) for l in open(f"{D}/obs.jsonl")) if o.get("v") == 4 and o["slug"] in res]
print("v4 observations with a result:", len(O), "windows:", len({o["slug"] for o in O}))


def ll(p, y):
    p = min(max(p, 1e-3), 1 - 1e-3)
    return -(y * math.log(p) + (1 - y) * math.log(1 - p))


print("\nCalibration: log loss (lower is better), model vs market mid, by seconds left and feed")
for src in ("chainlink", "binance"):
    for lo, hi in ((90, 121), (60, 90), (30, 60), (10, 30), (0, 10)):
        S = [o for o in O if o["src"] == src and lo <= o["rem"] < hi and o["bid"] is not None and o["side"] == "Up"]
        if len(S) < 20:
            continue
        y = [1 if res[o["slug"]] else 0 for o in S]
        mid = [(o["ask"] + o["bid"]) / 2 for o in S]
        lm = sum(ll(m, a) for m, a in zip(mid, y)) / len(S); lp = sum(ll(o["p_model"], a) for o, a in zip(S, y)) / len(S)
        acc_m = sum((m > 0.5) == bool(a) for m, a in zip(mid, y)) / len(S); acc_p = sum((o["p_model"] > 0.5) == bool(a) for o, a in zip(S, y)) / len(S)
        print(f"  {src:9} rem {lo:3}-{hi:3}: n={len(S):5}  logloss market {lm:.3f} model {lp:.3f}   direction market {acc_m:.3f} model {acc_p:.3f}")

print("\nLOCK opportunities: first moment per (window, side) in the last 60 s with z >= Z and ask <= A; realized outcome")
for Z in (2.0, 2.5, 3.0, 4.0):
    for A in (0.90, 0.95, 0.97):
        seen = set(); n = w = 0; stake = pnl = 0.0; prices = []
        for o in sorted(O, key=lambda o: o["ts"]):
            k = (o["slug"], o["side"])
            if k in seen or o["rem"] > 60 or o["z"] < Z or o["ask"] > A or o["src"] != "chainlink" or o.get("k_src") not in ("ptb", "twap", "chainlink"):
                continue
            seen.add(k); y = 1 if (res[o["slug"]] == (o["side"] == "Up")) else 0
            a = o["ask"]; fee = 0.07 * a * (1 - a)
            n += 1; w += y; stake += a; pnl += y - a - fee; prices.append(a)
        if n:
            prices.sort()
            print(f"  z>={Z} ask<={A}: n={n:4} win {w / n:.3f}  return/$ {pnl / stake:+.3f}  median ask {prices[len(prices) // 2]:.2f}  (one share each)")

print("\nSame, by seconds left (z>=2.5, ask<=0.97)")
for lo, hi in ((45, 61), (30, 45), (15, 30), (0, 15)):
    seen = set(); n = w = 0; stake = pnl = 0.0
    for o in sorted(O, key=lambda o: o["ts"]):
        k = (o["slug"], o["side"])
        if k in seen or not (lo <= o["rem"] < hi) or o["z"] < 2.5 or o["ask"] > 0.97 or o["src"] != "chainlink":
            continue
        seen.add(k); y = 1 if (res[o["slug"]] == (o["side"] == "Up")) else 0
        a = o["ask"]; fee = 0.07 * a * (1 - a); n += 1; w += y; stake += a; pnl += y - a - fee
    if n:
        print(f"  rem {lo:2}-{hi:2}: n={n:4} win {w / n:.3f} return/$ {pnl / stake:+.3f}")

print("\nModel confidence vs outcome in the last 60 s (chainlink feed): is z honest?")
for lo, hi in ((0, 1), (1, 2), (2, 3), (3, 5), (5, 1e9)):
    seen = set(); n = w = 0
    for o in O:
        k = (o["slug"], o["side"], o["rem"] // 10)
        if k in seen or o["rem"] > 60 or not (lo <= o["z"] < hi) or o["src"] != "chainlink":
            continue
        seen.add(k); n += 1; w += 1 if (res[o["slug"]] == (o["side"] == "Up")) else 0
    if n:
        print(f"  z {lo}-{hi}: n={n:5} realized {w / n:.3f}  model says >= {N.cdf(lo):.3f}")

# pairs
try:
    P = [json.loads(l) for l in open(f"{D}/pairs.jsonl")]
    P = [p for p in P if p["legs"][0][1] in res and p["legs"][1][1] in res]
    print(f"\nPAIRS: {len(P)} observations, {len({p['legs'][0][1] for p in P})} windows")
    sums = sorted(p["sum"] for p in P)
    if sums:
        print(f"  ask sum: min {sums[0]:.2f} 10% {sums[len(sums) // 10]:.2f} median {sums[len(sums) // 2]:.2f}; share < 1.00: {sum(s < 1 for s in sums) / len(sums):.3f}")
    for E in (0.0, 0.03, 0.06, 0.10):
        seen = set(); n = 0; cost = pay = 0.0
        for p in sorted(P, key=lambda p: p["ts"]):
            k = p["legs"][0][1]
            if k in seen or p["ev"] < E or p["sum"] > 1.15:
                continue
            seen.add(k); n += 1
            paid = 0
            for side, slug, ask, _ in p["legs"]:
                paid += 1 if (res[slug] == (side == "Up")) else 0
            fees = sum(0.07 * a * (1 - a) for _, _, a, _ in p["legs"])
            cost += p["sum"] + fees; pay += paid
        if n:
            print(f"  ev>={E:.2f}: n={n:4} paid per pair {cost / n:.3f} received {pay / n:.3f} -> {(pay - cost) / cost:+.3f}/$")
except OSError:
    print("no pairs file yet")

# feed vs official references
try:
    meta = json.load(open(f"{D}/results_meta.json"))
    W = [json.loads(l) for l in open(f"{D}/windows.jsonl")]
    d1 = []; d2 = []
    for w in W:
        md = meta.get(w["slug"])
        if not md or w.get("v") != 4:
            continue
        if md.get("ptb") and w.get("K_twap"):
            d1.append((w["K_twap"] - md["ptb"]) / md["ptb"] * 1e4)
        if md.get("final") and w.get("twap_end"):
            d2.append((w["twap_end"] - md["final"]) / md["final"] * 1e4)
    for name, d in (("feed TWAP at start vs official priceToBeat", d1), ("feed TWAP at end vs official finalPrice", d2)):
        if d:
            d.sort(); print(f"\n{name}: n={len(d)} median {d[len(d) // 2]:+.2f} bp, 10-90% {d[len(d) // 10]:+.2f}..{d[9 * len(d) // 10]:+.2f} bp, |d|<0.5bp: {sum(abs(x) < 0.5 for x in d) / len(d):.2f}")
except OSError:
    pass
