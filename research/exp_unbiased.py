"""Re-test the leading strategies WITHOUT the final-volume selection bias.

Problem: our market list keeps markets whose FINAL volume >= $5k. Surprising/dramatic outcomes
attract extra trading, so they are over-represented (Kalshi draws: 12% in the least-traded
games vs 32% in the most-traded, at the same ~25% price).
Fix: keep only rows whose market had ALREADY traded >= $X before the bet moment (from real
trades, trades sample). Any such market is in our list regardless of how it ended, so this
subset is free of the bias. Compare each strategy on (a) all rows of the trades sample and
(b) only rows with >= $X traded before the bet."""
import json, os
import numpy as np
os.environ.setdefault("COSTSTAT", "median")
src = open("research/rescore_costs.py").read().split("sc = StandardScaler()")[0]
exec(src)
tf = np.load("derived/trade_feats.npz")
idx, TFX, TFN = tf["idx"], tf["F"], list(tf["names"])
usd_before = np.full(len(y), np.nan); usd_before[idx] = np.expm1(TFX[:, TFN.index("log_usd_so_far")])
insample = ~np.isnan(usd_before)
m2 = HistGradientBoostingRegressor(**GB).fit(X[TR], y[TR]).predict(X)
ch1, ch7 = c("chg_1d"), c("chg_7d")
draw = np.array([False] * len(y))
import glob, gzip, re
need = set(MID[insample].astype(int)); Qd = {}
for f in glob.glob("data/listing/*.gz"):
    for l in gzip.open(f, "rt"):
        j = l.find('"id":"'); mid = int(l[j + 6:l.index('"', j + 6)])
        if mid in need:
            m = json.loads(l); q = (m.get("question") or "").lower()
            if "end in a draw" in q:
                Qd[mid] = json.loads(m.get("outcomes") or "[]").index("Yes") if "Yes" in (m.get("outcomes") or "") else None
dside = np.zeros(len(y))
for i in np.where(insample & (DAYS == 1))[0]:
    s_ = Qd.get(int(MID[i]))
    if s_ is not None:
        dside[i] = 1 if s_ == 0 else -1
STRATS = {"model (boosted) edge>3c": side_from_edge(m2, .03), "model (boosted) edge>6c": side_from_edge(m2, .06),
          "fade 7-day move >25c": np.where(ch7 > .25, -1, np.where(ch7 < -.25, 1, 0)),
          "fade 1-day jump >15c": np.where(ch1 > .15, -1, np.where(ch1 < -.15, 1, 0)),
          "long shot 5-20c, 7 days out": np.where((DAYS == 7) & (P >= .05) & (P < .2), 1, np.where((DAYS == 7) & (P > .8) & (P <= .95), -1, 0)),
          "soccer draw, 1 day out": dside,
          "every side of every row (baseline)": None}
res = {}
for period, pm in (("all periods", np.ones(len(y), bool)), ("Jun-Oct (test)", VA | LB)):
    for name, s in STRATS.items():
        for lab, mask in (("trades sample, any volume", insample & pm & ACTIVE),
                          (">= $5k traded BEFORE the bet", insample & pm & ACTIVE & (usd_before >= 5000)),
                          (">= $20k traded BEFORE the bet", insample & pm & ACTIVE & (usd_before >= 20000))):
            if s is None:
                sel = np.where(mask)[0]; sel = np.concatenate([sel, sel]); sd = np.r_[np.ones(len(sel) // 2), -np.ones(len(sel) // 2)]
            else:
                sel = np.where(mask & (s != 0))[0]; sd = s[sel]
            if len(sel) < 40:
                continue
            price = np.where(sd > 0, P[sel], 1 - P[sel]); won = np.where(sd > 0, OUT[sel], 1 - OUT[sel])
            cost = np.array([cost_of(p, i) for p, i in zip(price, sel)])
            r = ci(won / np.clip(price + cost, 0, .999) - 1, EV[sel])
            g = ci(won - price, EV[sel])
            res[f"{period} | {name} | {lab}"] = {"bets": len(sel), "win_minus_price_c": [round(100 * v, 2) for v in g], "profit_per_$": r}
            print(f"{period:15} {name:36} {lab:32} n={len(sel):6} won-price {100*g[0]:+5.1f}c ({100*g[1]:+.1f},{100*g[2]:+.1f})  profit/$ {r}")
json.dump(res, open("results/exp_unbiased.json", "w"), indent=1)
