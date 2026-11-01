"""Train the model only on rows free of the final-volume bias (>= $5k traded before the bet,
trades sample), test the same way on Jun-Oct. Small data, so a cautious model."""
import json, os
import numpy as np
os.environ.setdefault("COSTSTAT", "median")
src = open("research/rescore_costs.py").read().split("sc = StandardScaler()")[0]
exec(src)
tf = np.load("derived/trade_feats.npz")
idx, TFX, TFN = tf["idx"], tf["F"], list(tf["names"])
ub = np.zeros(len(y), bool); usd = np.zeros(len(y)); usd[idx] = np.expm1(TFX[:, TFN.index("log_usd_so_far")])
XT = np.zeros((len(y), len(TFN)), np.float32); XT[idx] = TFX
ub = usd >= 5000
TRu, TEu = TR & ub, (VA | LB) & ub & ACTIVE
print(f"unbiased rows: train {TRu.sum()}, test {TEu.sum()}")
res = {}
for name, XX, kw in (("boosted, price features", X, dict(GB, min_samples_leaf=150, max_iter=150)),
                     ("boosted, price + trade features", np.column_stack([X, XT]), dict(GB, min_samples_leaf=150, max_iter=150))):
    e = HistGradientBoostingRegressor(**kw).fit(XX[TRu], y[TRu]).predict(XX)
    for thr in (0.02, 0.04):
        sd = side_from_edge(e, thr); sel = np.where(TEu & (sd != 0))[0]
        if len(sel) < 30:
            continue
        price = np.where(sd[sel] > 0, P[sel], 1 - P[sel]); won = np.where(sd[sel] > 0, OUT[sel], 1 - OUT[sel])
        cost = np.array([cost_of(p, i) for p, i in zip(price, sel)])
        k = f"{name}, edge>{int(thr*100)}c"
        res[k] = {"bets": len(sel), "won_minus_price": ci(won - price, EV[sel]), "profit_per_$": ci(won / np.clip(price + cost, 0, .999) - 1, EV[sel])}
        print(f"{k:44} bets={len(sel):5} won-price {res[k]['won_minus_price']} profit/$ {res[k]['profit_per_$']}")
    print(f"{name}: test corr {np.corrcoef(e[TEu], y[TEu])[0,1]:+.4f}")
json.dump(res, open("results/exp_unbiased_model.json", "w"), indent=1)
