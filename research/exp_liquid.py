"""Models aimed only at markets where buying is cheap (measured cost <= ~1.5c: bigger
markets, game winners, politics), scored with real measured costs. Train before May,
test Jun-Oct (events unseen)."""
import glob, gzip, json
import numpy as np
src = open("research/rescore_costs.py").read().split("sc = StandardScaler()")[0]
exec(src)
cost_row = np.array([cost_of(P[i], i) for i in range(len(y))])  # cost for first side (approx. both)
cheap = cost_row <= 0.015
print(f"cheap-to-trade rows: {cheap.mean():.2f} of all; train {(TR & cheap).sum()}, test {((VA|LB) & cheap & ACTIVE).sum()}")
TEST = (VA | LB) & ACTIVE & cheap
GBl = dict(GB, min_samples_leaf=300)
models = {
    "boosted, trained on all rows": HistGradientBoostingRegressor(**GB).fit(X[TR], y[TR]).predict(X),
    "boosted, trained on cheap rows only": HistGradientBoostingRegressor(**GBl).fit(X[TR & cheap], y[TR & cheap]).predict(X),
}
sc = StandardScaler().fit(lin_design(X[TR & cheap]))
models["logistic, cheap rows only"] = LogisticRegression(C=0.1, max_iter=2000).fit(
    sc.transform(lin_design(X[TR & cheap])), OUT[TR & cheap].astype(int)).predict_proba(sc.transform(lin_design(X)))[:, 1] - P
ch7 = c("chg_7d")
res = {}
for name, e in list(models.items()) + [("rule: fade 7-day >25c", None)]:
    for thr in ((0.02, 0.04, 0.06) if e is not None else (None,)):
        s = side_from_edge(e, thr) if e is not None else np.where(ch7 > .25, -1, np.where(ch7 < -.25, 1, 0))
        sel = np.where(TEST & (s != 0))[0]
        if len(sel) < 50:
            continue
        price = np.where(s[sel] > 0, P[sel], 1 - P[sel]); won = np.where(s[sel] > 0, OUT[sel], 1 - OUT[sel])
        cost = np.array([cost_of(p, i) for p, i in zip(price, sel)])
        r = ci(won / np.clip(price + cost, 0, .999) - 1, EV[sel])
        key = f"{name}" + (f", edge>{int(thr*100)}c" if thr else "")
        res[key] = {"bets": len(sel), "events": int(len(np.unique(EV[sel]))), "avg_cost_c": round(100 * cost.mean(), 2), "profit_per_$": r}
        print(f"{key:48} bets={len(sel):6} events={res[key]['events']:5} cost {100*cost.mean():.1f}c  profit/$ {r}")
json.dump(res, open("results/exp_liquid.json", "w"), indent=1)
