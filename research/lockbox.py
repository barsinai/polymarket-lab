"""One-time lockbox test of the three finalists chosen from validation (see experiments.py):
  M2 boosted trees edge>6c, M4 logistic edge>6c, R3 fade 7-day move >25c.
Trained on train+validation (everything before 2026-09-01), scored on the lockbox."""
import json
import numpy as np
src = open("research/experiments.py").read().split("def model_edges")[0]
exec(src)
TRV = (T < day("2026-09-01")) & ~LB
sc = StandardScaler().fit(lin_design(X[TRV]))
m2 = HistGradientBoostingRegressor(**GB).fit(X[TRV], y[TRV]).predict(X)
m4 = LogisticRegression(C=0.1, max_iter=2000).fit(sc.transform(lin_design(X[TRV])), OUT[TRV].astype(int)).predict_proba(sc.transform(lin_design(X)))[:, 1] - P
ch7 = c("chg_7d")
r3 = np.where(ch7 > .25, -1, np.where(ch7 < -.25, 1, 0))
sp = c("cat_Sports") == 1
res = {"M2 boosted trees, edge>6c": score_hold(side_from_edge(m2, .06), LB),
       "M4 logistic, edge>6c": score_hold(side_from_edge(m4, .06), LB),
       "R3 fade 7-day move >25c": score_hold(r3, LB),
       "R3 fade 7-day move >25c, sports only": score_hold(np.where(sp, r3, 0), LB),
       "R3 fade 7-day move >25c, non-sports": score_hold(np.where(~sp, r3, 0), LB)}
json.dump(res, open("results/lockbox.json", "w"), indent=1)
for name, r in res.items():
    for seg in ("all", "active"):
        z = r[seg]
        if z:
            print(f"{name:40} {seg:6} n={z['bets']:6} 1c {z['cost1c']}  2c {z['cost2c']}  3c {z['cost3c']}")
