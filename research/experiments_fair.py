"""The experiment battery, judged ONLY on fair rows (market had >= $5k traded before the bet
moment; see fair.py). Models are trained (a) on all training rows as before and (b) on fair
training rows only. Test: Jun-Oct 2026, events unseen in training, typical measured costs.
Reports 'won minus price' (cents per bet, the raw mispricing) and profit per $1 after costs,
each with a 95% range from resampling whole events.
"""
import json, os, sys
import numpy as np
os.environ.setdefault("COSTSTAT", "median")
src = open("research/rescore_costs.py").read().split("sc = StandardScaler()")[0]
exec(src)
sys.path.insert(0, "research")
from fair import fair_mask  # noqa: E402
MIN_USD = float(os.environ.get("FAIR_MIN_USD", "5000"))
FAIR, KNOWN, USD = fair_mask(MID, DAYS, MIN_USD)
TEST = (VA | LB) & FAIR & ACTIVE
print(f"fair test rows: {TEST.sum()}, fair train rows: {(TR & FAIR).sum()}")

sc = StandardScaler().fit(lin_design(X[TR]))
E = {"boosted (trained on all rows)": HistGradientBoostingRegressor(**GB).fit(X[TR], y[TR]).predict(X),
     "logistic (trained on all rows)": LogisticRegression(C=0.1, max_iter=2000).fit(
         sc.transform(lin_design(X[TR])), OUT[TR].astype(int)).predict_proba(sc.transform(lin_design(X)))[:, 1] - P}
TRF = TR & FAIR
if TRF.sum() > 2000:
    E["boosted (trained on fair rows only)"] = HistGradientBoostingRegressor(**dict(GB, min_samples_leaf=200)).fit(X[TRF], y[TRF]).predict(X)
    scf = StandardScaler().fit(lin_design(X[TRF]))
    E["logistic (trained on fair rows only)"] = LogisticRegression(C=0.05, max_iter=2000).fit(
        scf.transform(lin_design(X[TRF])), OUT[TRF].astype(int)).predict_proba(scf.transform(lin_design(X)))[:, 1] - P
ch1, ch7 = c("chg_1d"), c("chg_7d")
S = {}
for name, e in E.items():
    for thr in (0.03, 0.06):
        S[f"{name}, edge>{int(thr*100)}c"] = side_from_edge(e, thr)
S["fade 1-day jump >15c"] = np.where(ch1 > .15, -1, np.where(ch1 < -.15, 1, 0))
S["fade 7-day move >25c"] = np.where(ch7 > .25, -1, np.where(ch7 < -.25, 1, 0))
S["follow 7-day move >25c"] = -S["fade 7-day move >25c"]
S["long shot 5-20c (buy cheap side), 7d"] = np.where((DAYS == 7) & (P >= .05) & (P < .2), 1, np.where((DAYS == 7) & (P > .8) & (P <= .95), -1, 0))
S["favourite 80-95c, 1d"] = np.where((DAYS == 1) & (P >= .8) & (P <= .95), 1, np.where((DAYS == 1) & (P >= .05) & (P <= .2), -1, 0))
res = {"fair_min_usd": MIN_USD, "fair_test_rows": int(TEST.sum()), "known_share": float(KNOWN.mean()), "results": {}}
for name, s in S.items():
    sel = np.where(TEST & (s != 0))[0]
    if len(sel) < 40:
        continue
    price = np.where(s[sel] > 0, P[sel], 1 - P[sel]); won = np.where(s[sel] > 0, OUT[sel], 1 - OUT[sel])
    cost = np.array([cost_of(p, i) for p, i in zip(price, sel)])
    g = ci(won - price, EV[sel]); r = ci(won / np.clip(price + cost, 0, .999) - 1, EV[sel])
    res["results"][name] = {"bets": len(sel), "events": int(len(np.unique(EV[sel]))), "won_minus_price": g, "profit_per_$": r}
    flag = "  <-- clearly positive" if r[1] > 0 else ""
    print(f"{name:52} bets={len(sel):6} won-price {100*g[0]:+5.1f}c ({100*g[1]:+.1f},{100*g[2]:+.1f}) profit/$ {r}{flag}")
json.dump(res, open(f"results/experiments_fair_{int(MIN_USD)}.json", "w"), indent=1)
