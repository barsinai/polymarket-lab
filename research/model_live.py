"""Train the model used for paper trading: same idea as model.py, restricted to features
that the hourly live recording provides (Gamma's own 1h/1d/1w price changes stand in for
the history-based ones; no volatility/range features). Saves research/models/live_v1.pkl.

Run after `python research/model.py build`.
"""
import json
import pickle
from datetime import datetime, timezone

import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor

LIVE_FEATS = ["p", "logit_p", "dist50", "chg_1h", "chg_1d", "chg_7d", "log_days_left", "frac_elapsed",
              "log_age_days", "yes_no", "deadline", "neg_risk", "fees",
              "cat_Sports", "cat_Crypto", "cat_Politics", "cat_Geopolitics", "cat_Economy", "cat_Culture", "cat_Other"]


def main(split="2026-05-01"):
    d = np.load("derived/rows.npz")
    X, y, info, feats = d["X"], d["y"], d["info"], list(d["feats"])
    X = X[:, [feats.index(f) for f in LIVE_FEATS]]
    mid, ev, t, days, vol = info.T
    s = datetime.fromisoformat(split).replace(tzinfo=timezone.utc).timestamp()
    tr = t < s
    te = (t >= s + 30 * 86400) & ~np.isin(ev, np.unique(ev[tr]))
    kw = dict(max_iter=300, learning_rate=0.05, max_leaf_nodes=31, min_samples_leaf=500,
              l2_regularization=1.0, random_state=0)
    gb = HistGradientBoostingRegressor(**kw).fit(X[tr], y[tr])
    pr = gb.predict(X[te])
    p = X[te, 0]; out = y[te] + p
    buy = pr > 0; price = np.where(buy, p, 1 - p); won = np.where(buy, out, 1 - out)
    rep = {"test_corr": float(np.corrcoef(pr, y[te])[0, 1])}
    for thr in (0.02, 0.05):
        sel = np.abs(pr) > thr
        rep[f"edge>{int(thr*100)}c"] = {"bets": int(sel.sum()),
                                        "profit_per_$_cost2c": float((won[sel] / np.clip(price[sel] + .02, 0, .999) - 1).mean())}
    print("held-out test:", json.dumps(rep))
    final = HistGradientBoostingRegressor(**kw).fit(X, y)  # deploy: train on everything
    with open("research/models/live_v1.pkl", "wb") as f:
        pickle.dump({"model": final, "features": LIVE_FEATS, "trained": datetime.now(timezone.utc).isoformat(),
                     "rows": int(len(y)), "test_report": rep}, f)
    print("saved research/models/live_v1.pkl")


if __name__ == "__main__":
    main()
