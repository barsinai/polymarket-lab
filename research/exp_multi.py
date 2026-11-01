"""Multi-option events (exactly one option wins, e.g. 'Who will win X?').
At each horizon, for events where we have prices for options covering >= 90% of probability:
  sum = total of all options' Yes prices (should be ~1).
  normalised price = price / sum.
Does the normalised price predict better (Brier)? And: when sum > 1 + margin, buy 'No' on the
options whose price is most above their normalised value; typical costs; Jun-Oct test."""
import json, os
from collections import defaultdict
import numpy as np
os.environ.setdefault("COSTSTAT", "median")
src = open("research/rescore_costs.py").read().split("sc = StandardScaler()")[0]
exec(src)
neg = c("neg_risk") == 1
grp = defaultdict(list)
for i in np.where(neg & (EV > 0))[0]:
    grp[(int(EV[i]), int(DAYS[i]))].append(i)
rows, sums = [], []
for (ev, d), ii in grp.items():
    if len(ii) < 3:
        continue
    s = P[ii].sum()
    if s < 0.9 or s > 1.5:
        continue
    # one option per market id (keep first)
    for i in ii:
        rows.append((i, s, len(ii)))
ii = np.array([r[0] for r in rows]); S_ = np.array([r[1] for r in rows]); n_ = np.array([r[2] for r in rows])
pn = P[ii] / S_
res = {"rows": len(ii), "events": int(len(np.unique(EV[ii])))}
for name, m in (("before May", TR[ii]), ("Jun-Oct", (VA | LB)[ii])):
    r = {"rows": int(m.sum()), "avg_sum": round(float(S_[m].mean()), 3),
         "brier_price": round(float(np.mean((P[ii][m] - OUT[ii][m]) ** 2)), 5),
         "brier_normalised": round(float(np.mean((pn[m] - OUT[ii][m]) ** 2)), 5)}
    for marg in (0.03, 0.08):
        sel = m & (S_ > 1 + marg) & ((P[ii] - pn) > 0.01)  # buy No on options priced above their share
        if sel.sum() < 30:
            continue
        price = 1 - P[ii][sel]; won = 1 - OUT[ii][sel]
        cost = np.array([cost_of(p, i) for p, i in zip(price, ii[sel])])
        r[f"sum > {1+marg:.2f}: buy No on over-share options"] = {"bets": int(sel.sum()), "events": int(len(np.unique(EV[ii][sel]))),
                                                                  "profit_per_$": ci(won / np.clip(price + cost, 0, .999) - 1, EV[ii][sel])}
    res[name] = r
    print(name, json.dumps(r))
json.dump(res, open("results/exp_multi.json", "w"), indent=1)
