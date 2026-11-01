"""Do trade-based features help? Same rows (markets in the trades sample), same split:
boosted trees with price features only vs price + trade features. Test = Jun-Oct 2026,
events unseen in training. Also: does each trade feature alone carry signal?"""
import json
import numpy as np
src = open("research/experiments.py").read().split("def model_edges")[0]
exec(src)
tf = np.load("derived/trade_feats.npz")
idx, TFX, TFN = tf["idx"], tf["F"], list(tf["names"])
sub = np.zeros(len(y), bool); sub[idx] = True
XT = np.zeros((len(y), len(TFN)), np.float32); XT[idx] = TFX
TEST = (VA | LB) & sub
TRS = TR & sub
print(f"subset rows: train {TRS.sum()}, test {TEST.sum()}")
GBs = dict(GB, min_samples_leaf=200)
base = HistGradientBoostingRegressor(**GBs).fit(X[TRS], y[TRS]).predict(X)
XX = np.column_stack([X, XT])
full = HistGradientBoostingRegressor(**GBs).fit(XX[TRS], y[TRS]).predict(XX)
res = {}
for name, e in (("price features only", base), ("price + trade features", full)):
    r = {"corr_test": round(float(np.corrcoef(e[TEST], y[TEST])[0, 1]), 4)}
    for thr in (0.03, 0.06):
        r[f"edge>{int(thr*100)}c"] = score_hold(side_from_edge(e, thr), TEST)
    res[name] = r
    z3, z6 = r["edge>3c"]["active"], r["edge>6c"]["active"]
    print(f"{name:24} corr {r['corr_test']:+.4f} | edge>3c active: {z3 and (z3['bets'], z3['cost2c'])} | edge>6c active: {z6 and (z6['bets'], z6['cost2c'])}")
# single-feature signal: correlation of each trade feature with the price's error on test rows
print("\ncorrelation of each trade feature with how wrong the price was (test rows):")
res["single_feature_corr"] = {}
for j, n in enumerate(TFN):
    v = XT[TEST, j]
    cc = float(np.corrcoef(v, y[TEST])[0, 1]) if v.std() > 0 else 0.0
    res["single_feature_corr"][n] = round(cc, 4)
    print(f"  {n:20} {cc:+.4f}")
json.dump(res, open("results/exp_trades.json", "w"), indent=1)
