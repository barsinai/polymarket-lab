"""Numbers behind the visual report (research/fast/report.html): computed from the repo's own files."""
import gzip, json, math
from collections import defaultdict
from statistics import NormalDist

D = "data/fast"
N = NormalDist()
out = {}
M = json.load(open(f"{D}/results_meta.json"))

# 1. official rule + margins + Binance-Chainlink gap
W = [json.loads(l) for l in open(f"{D}/windows.jsonl")]
gap = sorted((md["ptb"] - w["mean_pre60"]) / md["ptb"] * 1e4 for w in W if (md := M.get(w["slug"])) and md.get("ptb") and w.get("mean_pre60"))
margins = sorted(abs(md["final"] - md["ptb"]) / md["ptb"] * 1e4 for md in M.values() if md.get("ptb") and md.get("final"))
def hist(vals, lo, hi, step):
    edges = [lo + i * step for i in range(int(round((hi - lo) / step)) + 1)]
    counts = [0] * (len(edges) - 1)
    for v in vals:
        if lo <= v < hi:
            counts[min(int((v - lo) / step), len(counts) - 1)] += 1
    return {"edges": edges, "counts": counts, "n": len(vals), "below": sum(v < lo for v in vals), "above": sum(v >= hi for v in vals)}
out["gap"] = {"hist": hist(gap, -18, -9, 0.5), "median": gap[len(gap) // 2], "p10": gap[len(gap) // 10], "p90": gap[9 * len(gap) // 10]}
out["margin"] = {"hist": hist(margins, 0, 40, 2), "median": margins[len(margins) // 2], "p10": margins[len(margins) // 10], "p90": margins[9 * len(margins) // 10]}
rule_ok = sum((md["final"] >= md["ptb"]) == md["up"] for md in M.values() if md.get("ptb") and md.get("final") and md.get("up") is not None)
out["rule"] = {"ok": rule_ok, "n": sum(1 for md in M.values() if md.get("ptb") and md.get("final") and md.get("up") is not None)}
# proxy rules (from windows.jsonl with results)
res = {s: md["up"] for s, md in M.items() if md.get("up") is not None}
rules = {"Chainlink final vs price to beat (official)": None,
         "Binance: mean of last 60 s vs mean of 60 s before start": lambda w: w["mean_last60"] >= w["mean_pre60"],
         "Binance: last 60 s mean vs start spot": lambda w: w["mean_last60"] >= w["spot_start"],
         "Binance: end spot vs start spot (chart reader)": lambda w: w["spot_end"] >= w["spot_start"],
         "Binance: whole-window mean vs start spot (our v1)": lambda w: w["mean_window"] >= w["spot_start"]}
rr = []
for name, f in rules.items():
    if f is None:
        rr.append({"rule": name, "ok": out["rule"]["ok"], "n": out["rule"]["n"]}); continue
    ok = n = 0
    for w in W:
        if w["slug"] in res and all(w.get(k) is not None for k in ("spot_end", "spot_start", "mean_window", "mean_last60", "mean_pre60")):
            n += 1; ok += f(w) == res[w["slug"]]
    rr.append({"rule": name, "ok": ok, "n": n})
out["rules"] = rr

# 2. linkage
pairs = {"two_dollar": 0, "one_dollar": 0, "impossible": 0}
for s, md in M.items():
    if md["window"] != 900:
        continue
    s5 = f"{s.split('-')[0]}-updown-5m-{md['start'] + 600}"; m5 = M.get(s5)
    if not m5 or md.get("ptb") is None or m5.get("ptb") is None or md.get("up") is None or m5.get("up") is None:
        continue
    k15, k5, u15, u5 = md["ptb"], m5["ptb"], md["up"], m5["up"]
    if (k15 < k5 and not u15 and u5) or (k15 > k5 and u15 and not u5):
        pairs["impossible"] += 1
    elif (k15 < k5 and u15 and not u5) or (k15 > k5 and not u15 and u5):
        pairs["two_dollar"] += 1
    else:
        pairs["one_dollar"] += 1
out["pairs"] = pairs

# 3. tape: return per $ by price x time-left (after full taker fee)
B = defaultdict(lambda: [0, 0.0, 0.0])
rb = lambda r: 0 if r <= 15 else 1 if r <= 30 else 2 if r <= 60 else 3 if r <= 120 else 4 if r <= 300 else 5
pb = lambda p: 0 if p <= 0.02 else 1 if p <= 0.10 else 2 if p <= 0.3 else 3 if p <= 0.5 else 4 if p <= 0.7 else 5 if p <= 0.9 else 6 if p <= 0.97 else 7
tape_n = 0; wallets = set(); vol = 0.0
dogwin = defaultdict(float)
with gzip.open(f"{D}/tape.jsonl.gz", "rt") as fh:
    for line in fh:
        t = json.loads(line); tape_n += 1; wallets.add(t["w"]); vol += t["s"] * t["p"]
        if t["side"] != "BUY":
            continue
        md = M[t["slug"]]
        if md.get("up") is None:
            continue
        r = md["start"] + md["window"] - t["ts"]
        won = 1.0 if ((t["o"] == "Up") == md["up"]) else 0.0
        pnl = t["s"] * (won - t["p"]) - 0.07 * t["p"] * (1 - t["p"]) * t["s"]
        b = B[(rb(r), pb(t["p"]))]; b[0] += 1; b[1] += t["s"] * t["p"]; b[2] += pnl
        if 30 <= r <= 120 and 0.05 <= t["p"] <= 0.35:
            dogwin[t["slug"]] += pnl
out["tape"] = {"fills": tape_n, "wallets": len(wallets), "volume": vol, "windows": len(M),
               "time_labels": ["≤15 s", "≤30 s", "≤60 s", "≤2 min", "≤5 min", "earlier"],
               "price_labels": ["1-2¢", "3-10¢", "10-30¢", "30-50¢", "50-70¢", "70-90¢", "90-97¢", "98-99.9¢"],
               "cells": [{"t": k[0], "p": k[1], "n": v[0], "usd": round(v[1]), "ret": round(v[2] / v[1], 3)} for k, v in B.items() if v[1] >= 50]}
dw = sorted(dogwin.values(), reverse=True)
tot = sum(dw); cum = []; c = 0.0
for v in dw:
    c += v; cum.append(round(c))
out["dog"] = {"windows": len(dw), "total": round(tot), "top5": round(sum(dw[:5])), "positive": sum(v > 0 for v in dw), "median": round(sorted(dw)[len(dw) // 2], 1), "cum": cum[:: max(1, len(cum) // 120)] + [cum[-1]], "sorted": [round(v) for v in dw]}

# 4. wallets: P&L after fees for regulars
Wl = defaultdict(lambda: {"vol": 0.0, "pnl": 0.0, "win": set(), "ups": 0, "buys": 0})
with gzip.open(f"{D}/tape.jsonl.gz", "rt") as fh:
    for line in fh:
        t = json.loads(line); md = M[t["slug"]]
        if md.get("up") is None:
            continue
        won = 1.0 if ((t["o"] == "Up") == md["up"]) else 0.0; buy = t["side"] == "BUY"
        pnl = t["s"] * ((won - t["p"]) if buy else (t["p"] - won)) - 0.07 * t["p"] * (1 - t["p"]) * t["s"]
        w = Wl[t["w"]]; w["vol"] += t["s"] * t["p"]; w["pnl"] += pnl; w["win"].add(t["slug"])
        if buy:
            w["buys"] += 1; w["ups"] += t["o"] == "Up"
reg = [w for w in Wl.values() if len(w["win"]) >= 30 and w["vol"] >= 500]
rets = sorted(w["pnl"] / w["vol"] for w in reg)
out["wallets"] = {"regulars": len(reg), "profitable": sum(w["pnl"] > 0 for w in reg), "net": round(sum(w["pnl"] for w in reg)),
                  "ret_hist": hist([r * 100 for r in rets], -60, 40, 5), "median_ret": round(rets[len(rets) // 2] * 100, 1),
                  "up_bias": [{"bucket": lab, "n": len(g), "median_ret": round(sorted(x["pnl"] / x["vol"] for x in g)[len(g) // 2] * 100, 1)}
                              for lab, g in (("Up < 45%", [w for w in reg if w["buys"] and w["ups"] / w["buys"] < 0.45]),
                                             ("45-55%", [w for w in reg if w["buys"] and 0.45 <= w["ups"] / w["buys"] <= 0.55]),
                                             ("55-65%", [w for w in reg if w["buys"] and 0.55 < w["ups"] / w["buys"] <= 0.65]),
                                             ("Up > 65%", [w for w in reg if w["buys"] and w["ups"] / w["buys"] > 0.65])) if g]}

# 5. our observations: ask sums (set arbitrage) and v4 calibration
O = [json.loads(l) for l in open(f"{D}/obs.jsonl")]
by = defaultdict(dict)
for o in O:
    by[(o["slug"], int(o["ts"]))][o["side"]] = o
sums = sorted(d["Up"]["ask"] + d["Down"]["ask"] for d in by.values() if "Up" in d and "Down" in d)
out["asksum"] = {"hist": hist(sums, 0.98, 1.10, 0.005), "n": len(sums), "min": sums[0], "median": sums[len(sums) // 2], "below1": sum(s < 1 for s in sums)}
resx = dict(res)
for t in (json.loads(l) for l in open(f"{D}/trades.jsonl")):
    if t.get("result") is not None:
        resx[t["slug"]] = (t["result"] == 1) if t["side"] == "Up" else (t["result"] == 0)
O4 = [o for o in O if o.get("v") == 4 and o["slug"] in resx and o["src"] == "chainlink"]
def ll(p, y):
    p = min(max(p, 1e-3), 1 - 1e-3); return -(y * math.log(p) + (1 - y) * math.log(1 - p))
cal = []
for lo, hi, lab in ((90, 121, "90-120 s"), (60, 90, "60-90 s"), (30, 60, "30-60 s"), (0, 30, "0-30 s")):
    S = [o for o in O4 if lo <= o["rem"] < hi and o["bid"] is not None and o["side"] == "Up"]
    if len(S) < 20:
        continue
    y = [1 if resx[o["slug"]] else 0 for o in S]; mid = [(o["ask"] + o["bid"]) / 2 for o in S]
    cal.append({"bucket": lab, "n": len(S), "market": round(sum(ll(m, a) for m, a in zip(mid, y)) / len(S), 3), "model": round(sum(ll(o["p_model"], a) for o, a in zip(S, y)) / len(S), 3)})
out["calibration"] = {"rows": cal, "windows": len({o["slug"] for o in O4})}
zrows = []
for lo, hi, lab in ((0, 1, "0-1"), (1, 2, "1-2"), (2, 3, "2-3"), (3, 5, "3-5"), (5, 1e9, "5+")):
    seen = set(); n = w = 0
    for o in O4:
        k = (o["slug"], o["side"], o["rem"] // 10)
        if k in seen or o["rem"] > 60 or not (lo <= o["z"] < hi):
            continue
        seen.add(k); n += 1; w += 1 if (resx[o["slug"]] == (o["side"] == "Up")) else 0
    if n:
        zrows.append({"z": lab, "n": n, "realized": round(w / n, 3), "model_min": round(N.cdf(lo), 3)})
out["zcal"] = zrows
# v4 paper results so far
T4 = [t for t in (json.loads(l) for l in open(f"{D}/trades.jsonl")) if t.get("model") == "v4" and t.get("result") is not None]
bs = defaultdict(lambda: [0, 0, 0.0, 0.0])
for t in T4:
    b = bs[t["strat"]]; b[0] += 1; b[1] += t["result"]; b[2] += t["price"] * t["shares"]; b[3] += t["pnl"]
out["v4"] = [{"strat": k, "n": v[0], "win": round(v[1] / v[0], 2), "staked": round(v[2]), "pnl": round(v[3], 1)} for k, v in bs.items()]
# v1/v2 paper results (the Binance-era bots)
T12 = [json.loads(l) for l in open(f"{D}/trades_v1_wrong_rule.jsonl")] + [t for t in (json.loads(l) for l in open(f"{D}/trades.jsonl")) if t.get("model") == "v2"]
T12 = [t for t in T12 if t.get("result") is not None]
out["old_bots"] = {"n": len(T12), "staked": round(sum(t["price"] * t["shares"] for t in T12)), "pnl": round(sum(t["pnl"] for t in T12))}
# the "maker" replay (naive) and its sweep summary are quoted from the log, not recomputed here
json.dump(out, open(f"{D}/report_data.json", "w"))
print(json.dumps({k: (v if not isinstance(v, (list, dict)) or len(json.dumps(v)) < 300 else "...") for k, v in out.items()}, indent=1)[:3000])
