"""Robustness of the leading model (boosted trees, edge > 3c / 6c) in cheap-to-trade markets,
typical costs: month by month in Jun-Oct, by market kind, by price level of the side bought,
and by days before end."""
import json, os
import numpy as np
from datetime import datetime, timezone
from collections import defaultdict
os.environ.setdefault("COSTSTAT", "median")
src = open("research/rescore_costs.py").read().split("sc = StandardScaler()")[0]
exec(src)
cost_row = np.array([cost_of(P[i], i) for i in range(len(y))]); cheap = cost_row <= 0.015
e = HistGradientBoostingRegressor(**GB).fit(X[TR], y[TR]).predict(X)
res = {}
for thr in (0.03, 0.06):
    sd = side_from_edge(e, thr)
    sel = np.where((VA | LB) & ACTIVE & cheap & (sd != 0))[0]
    price = np.where(sd[sel] > 0, P[sel], 1 - P[sel]); won = np.where(sd[sel] > 0, OUT[sel], 1 - OUT[sel])
    cost = np.array([cost_of(p, i) for p, i in zip(price, sel)])
    ret = won / np.clip(price + cost, 0, .999) - 1
    groups = defaultdict(list)
    for k, i in enumerate(sel):
        groups["month " + datetime.fromtimestamp(T[i], timezone.utc).strftime("%Y-%m")].append(k)
        groups["kind " + K[i]].append(k)
        pb = price[k]; groups["bought " + ("<10c" if pb < .1 else "10-30c" if pb < .3 else "30-70c" if pb < .7 else ">70c")].append(k)
        groups[f"days {int(DAYS[i])}"].append(k)
        groups["side " + ("first (Yes)" if sd[i] > 0 else "second (No)")].append(k)
    print(f"\n== edge > {int(thr*100)}c: {len(sel)} bets, overall {ci(ret, EV[sel])}")
    for g in sorted(groups):
        kk = np.array(groups[g])
        if len(kk) >= 100:
            r = ci(ret[kk], EV[sel][kk]); res[f"edge>{int(thr*100)}c | {g}"] = {"bets": len(kk), "profit_per_$": r}
            print(f"  {g:22} bets={len(kk):6} profit/$ {r}")
json.dump(res, open("results/exp_model_robust.json", "w"), indent=1)
