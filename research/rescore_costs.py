"""Re-score the leading strategies with realistic costs measured from live order books
(results/costs.json: mean extra cost to buy $10, by market kind / size / price level)
instead of a flat 2c. Rows: validation + lockbox (Jun-Oct 2026), events unseen in training.
Size uses lifetime volume as a stand-in for liquidity at bet time (used only for cost).
"""
import glob, gzip, json, re, sys
import numpy as np
src = open("research/experiments.py").read().split("def model_edges")[0]
exec(src)
sys.path.insert(0, "research")
from costs import kind, tier, band  # noqa: E402
import os
COSTSTAT = os.environ.get("COSTSTAT", "mean")  # "median" = typical book (trader skips wide books)
C = {(g["kind"], g["size"], g["price"]): g[f"extra_cost_c_$10_{COSTSTAT}"] / 100 for g in json.load(open("results/costs.json"))["groups"]
     if g[f"extra_cost_c_$10_{COSTSTAT}"] is not None}
q = {}
need = set(MID.astype(int))
for f in glob.glob("data/listing/*.gz"):
    for l in gzip.open(f, "rt"):
        i = l.find('"id":"'); mid = int(l[i + 6:l.index('"', i + 6)])
        if mid in need:
            m = json.loads(l); q[mid] = kind((m.get("question") or "").lower())
K = np.array([q.get(int(i), "other") for i in MID])
TRV = (T < day("2026-09-01")) & ~LB & ~VA
EVAL = VA | LB


def cost_of(side_price, i):
    k, t, b = K[i], tier(VOL[i]), band(side_price)
    return C.get((k, t, b), C.get(("other", t, b), 0.05))


sc = StandardScaler().fit(lin_design(X[TR]))
m2 = HistGradientBoostingRegressor(**GB).fit(X[TR], y[TR]).predict(X)
m4 = LogisticRegression(C=0.1, max_iter=2000).fit(sc.transform(lin_design(X[TR])), OUT[TR].astype(int)).predict_proba(sc.transform(lin_design(X)))[:, 1] - P
ch1, ch7 = c("chg_1d"), c("chg_7d")
S = {"M2 boosted edge>6c": side_from_edge(m2, .06), "M4 logistic edge>6c": side_from_edge(m4, .06),
     "R3 fade 7-day >25c": np.where(ch7 > .25, -1, np.where(ch7 < -.25, 1, 0)),
     "R1 fade 1-day >15c": np.where(ch1 > .15, -1, np.where(ch1 < -.15, 1, 0))}
liquid = (VOL >= 2e4) & (K != "soccer prop")
res = {}
for name, s in S.items():
    for seg, mask in (("all", EVAL & ACTIVE), ("liquid only", EVAL & ACTIVE & liquid)):
        sel = np.where(mask & (s != 0))[0]
        if len(sel) < 100:
            continue
        price = np.where(s[sel] > 0, P[sel], 1 - P[sel]); won = np.where(s[sel] > 0, OUT[sel], 1 - OUT[sel])
        cost = np.array([cost_of(p, i) for p, i in zip(price, sel)])
        flat = ci(won / np.clip(price + .02, 0, .999) - 1, EV[sel])
        real = ci(won / np.clip(price + cost, 0, .999) - 1, EV[sel])
        res[f"{name} | {seg}"] = {"bets": len(sel), "avg_cost_c": round(100 * cost.mean(), 2), "flat_2c": flat, "real_costs": real}
        print(f"{name:22} {seg:12} n={len(sel):6} avg real cost {100*cost.mean():4.1f}c   flat 2c: {flat}   real: {real}")
json.dump(res, open("results/rescore_costs.json", "w"), indent=1)
