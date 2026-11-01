"""Give the model each question template's past mispricing (from training rows only, shrunk
toward 0: sum(error)/(n+200)) as a feature, plus the template's first-side price level.
Boosted trees with vs without it; test Jun-Oct (unseen events), typical costs; all and
cheap-to-trade rows."""
import glob, gzip, json, os, re
from collections import defaultdict
import numpy as np
os.environ.setdefault("COSTSTAT", "median")
src = open("research/rescore_costs.py").read().split("sc = StandardScaler()")[0]
exec(src)
tsrc = open("research/template_scan.py").read()
exec(tsrc[tsrc.index("def template"):tsrc.index("res = {")])
# encode: per (template, horizon bucket) mean error on TRAIN rows, shrunk
hb = np.where(DAYS <= 3, 0, np.where(DAYS <= 7, 1, 2))
key = np.array([f"{t}|{h}" for t, h in zip(tp, hb)])
s, n = defaultdict(float), defaultdict(int)
for k, e in zip(key[TR], (OUT - P)[TR]):
    s[k] += e; n[k] += 1
enc = np.array([s[k] / (n[k] + 200) for k in key], dtype=np.float32)
cnt = np.array([np.log1p(n[k]) for k in key], dtype=np.float32)
# for TRAIN rows use leave-one-out to avoid the row seeing its own outcome
loo = np.array([(s[k] - e) / (n[k] - 1 + 200) for k, e in zip(key, OUT - P)], dtype=np.float32)
enc_tr = np.where(TR, loo, enc)
X2 = np.column_stack([X, enc_tr, cnt])
cost_row = np.array([cost_of(P[i], i) for i in range(len(y))]); cheap = cost_row <= 0.015
TEST = (VA | LB) & ACTIVE
m_base = HistGradientBoostingRegressor(**GB).fit(X[TR], y[TR]).predict(X)
m_tpl = HistGradientBoostingRegressor(**GB).fit(X2[TR], y[TR]).predict(X2)
res = {}
for name, e in (("boosted, price features", m_base), ("boosted + template track record", m_tpl)):
    for seg, mask in (("all", TEST), ("cheap to trade", TEST & cheap)):
        for thr in (0.03, 0.06):
            sd = side_from_edge(e, thr); sel = np.where(mask & (sd != 0))[0]
            if len(sel) < 50:
                continue
            price = np.where(sd[sel] > 0, P[sel], 1 - P[sel]); won = np.where(sd[sel] > 0, OUT[sel], 1 - OUT[sel])
            cost = np.array([cost_of(p, i) for p, i in zip(price, sel)])
            r = ci(won / np.clip(price + cost, 0, .999) - 1, EV[sel])
            k = f"{name} | {seg} | edge>{int(thr*100)}c"
            res[k] = {"bets": len(sel), "events": int(len(np.unique(EV[sel]))), "cost_c": round(100 * cost.mean(), 2), "profit_per_$": r}
            print(f"{k:62} bets={len(sel):6} ev={res[k]['events']:5} cost {100*cost.mean():.1f}c profit/$ {r}")
    print(f"{name}: test corr {np.corrcoef(e[TEST], y[TEST])[0,1]:+.4f}")
json.dump(res, open("results/exp_template_feature.json", "w"), indent=1)
