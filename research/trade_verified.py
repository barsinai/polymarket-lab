"""Trade-verified backtest: count a historical bet only if someone actually bought that side
soon after the bet moment, and use the price they paid.

For each bet (validation + lockbox rows, Jun-Oct 2026) in a market whose trades we have:
  fill = price of the first recorded BUY of the chosen outcome within 6 hours after the
         bet moment (that price was demonstrably available to a buyer), plus a 0.5c cushion.
  No such trade -> the bet is counted as "not fillable" and dropped.
Compares profit per $1 at (a) history price + 2c (the old assumption) and (b) the real fill,
on exactly the same bets.
"""
import glob, gzip, json
import numpy as np
src = open("research/experiments.py").read().split("def model_edges")[0]
exec(src)
sc = StandardScaler().fit(lin_design(X[TR]))
m2 = HistGradientBoostingRegressor(**GB).fit(X[TR], y[TR]).predict(X)
m4 = LogisticRegression(C=0.1, max_iter=2000).fit(sc.transform(lin_design(X[TR])), OUT[TR].astype(int)).predict_proba(sc.transform(lin_design(X)))[:, 1] - P
ch1, ch7 = c("chg_1d"), c("chg_7d")
S = {"M2 boosted edge>6c": side_from_edge(m2, .06), "M4 logistic edge>6c": side_from_edge(m4, .06),
     "R3 fade 7-day >25c": np.where(ch7 > .25, -1, np.where(ch7 < -.25, 1, 0)),
     "R1 fade 1-day >15c": np.where(ch1 > .15, -1, np.where(ch1 < -.15, 1, 0)),
     "everything (both sides of every row)": None}
EVAL = (VA | LB) & ACTIVE
need = set(MID[EVAL].astype(int))
trades = {}
for f in glob.glob("data/trades/parts/*.jsonl.gz"):
    for l in gzip.open(f, "rt"):
        i = l.find('"market_id":"'); mid = int(l[i + 13:l.index('"', i + 13)])
        if mid in need:
            r = json.loads(l)
            rows = r["trades"] + r.get("big", [])
            if rows:
                a = np.array([x[:5] for x in rows], dtype=float)
                trades[mid] = a[(a[:, 1] == 1)]  # buys only: [ts, side, outcome, price, size]
print(f"trades available for {len(trades)} of {len(need)} evaluation markets")
res = {}
for name, s in S.items():
    sel = np.where(EVAL & np.isin(MID.astype(int), list(trades)))[0]
    if s is not None:
        sel = sel[s[sel] != 0]
        sides = s[sel]
    else:  # both sides of every row: shows the general gap between history price and real buys
        sel = np.concatenate([sel, sel]); sides = np.concatenate([np.ones(len(sel) // 2), -np.ones(len(sel) // 2)])
    hp, fills, won, evs = [], [], [], []
    for i, sd in zip(sel, sides):
        oc = 0 if sd > 0 else 1
        tr = trades[int(MID[i])]
        w = tr[(tr[:, 0] > T[i]) & (tr[:, 0] <= T[i] + 6 * 3600) & (tr[:, 2] == oc)]
        hp.append(P[i] if sd > 0 else 1 - P[i]); won.append(OUT[i] if sd > 0 else 1 - OUT[i]); evs.append(EV[i])
        fills.append(w[np.argsort(w[:, 0])][0, 3] if len(w) else np.nan)
    hp, fills, won, evs = map(np.array, (hp, fills, won, evs))
    ok = ~np.isnan(fills)
    if ok.sum() < 50:
        continue
    r = {"bets_in_markets_with_trades": int(len(hp)), "fillable_share": round(float(ok.mean()), 3),
         "median_fill_minus_history_c": round(100 * float(np.median(fills[ok] - hp[ok])), 2),
         "mean_fill_minus_history_c": round(100 * float(np.mean(fills[ok] - hp[ok])), 2),
         "history_price_plus_2c_all": ci(won / np.clip(hp + .02, 0, .999) - 1, evs),
         "history_price_plus_2c_fillable": ci(won[ok] / np.clip(hp[ok] + .02, 0, .999) - 1, evs[ok]),
         "real_fill_plus_half_c": ci(won[ok] / np.clip(fills[ok] + .005, 0.001, .999) - 1, evs[ok])}
    res[name] = r
    print(name, json.dumps(r))
json.dump(res, open("results/trade_verified.json", "w"), indent=1)
