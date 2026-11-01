"""Experiment battery on the saved table (derived/rows.npz from model.py build).

Honest-testing setup
  train      : moments before 2026-05-01
  validation : 2026-06-01 .. 2026-09-01, events never seen in training   <- all experiments
  lockbox    : from 2026-09-01, events never seen before                  <- only for finalists
Profit is per $1 staked, with an assumed trading cost per share (1c/2c/3c), and a 95%
interval from resampling whole events. Results are also shown on "active" rows only
(the price actually changed in >=10 of the last 168 hours and isn't parked at 50c),
because quiet markets' history prices are often not real buyable prices.

Two kinds of strategy:
  hold   - buy one side and hold to resolution (payout $1 or $0)
  swing  - buy one side and sell after 1 day at the then-price (pays the cost twice)

Usage: python research/experiments.py [--lockbox]   -> results/experiments.json
"""
import json
import sys
from datetime import datetime, timezone

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.preprocessing import StandardScaler

D = np.load("derived/rows.npz")
X, y, info, F, FUT = D["X"], D["y"], D["info"], list(D["feats"]), D["fut"]
MID, EV, T, DAYS, VOL = info.T
c = lambda name: X[:, F.index(name)]  # noqa: E731
P = c("p")
OUT = y + P  # 1 if the first side won
day = lambda s: datetime.fromisoformat(s).replace(tzinfo=timezone.utc).timestamp()  # noqa: E731
TR = T < day("2026-05-01")
seen = np.isin(EV, np.unique(EV[TR]))
VA = (T >= day("2026-06-01")) & (T < day("2026-09-01")) & ~seen
LB = (T >= day("2026-09-01")) & ~seen & ~np.isin(EV, np.unique(EV[VA]))
ACTIVE = (c("n_moves_7d") >= 10) & (c("at_half") == 0)
RNG = np.random.default_rng(1)
print(f"rows {len(y)}: train {TR.sum()}, validation {VA.sum()}, lockbox {LB.sum()}; active share {ACTIVE.mean():.2f}")


def ci(v, ev):
    u, inv = np.unique(ev, return_inverse=True)
    s, n = np.bincount(inv, v, len(u)), np.bincount(inv, None, len(u))
    idx = RNG.integers(0, len(u), (400, len(u)))
    b = s[idx].sum(1) / n[idx].sum(1)
    return round(float(v.mean()), 4), round(float(np.percentile(b, 2.5)), 4), round(float(np.percentile(b, 97.5)), 4)


def score_hold(side, mask):
    """side: +1 buy first side, -1 buy other side, 0 no bet (array over all rows)."""
    out = {}
    for seg, m in (("all", mask), ("active", mask & ACTIVE)):
        sel = m & (side != 0)
        if sel.sum() < 100:
            out[seg] = None
            continue
        price = np.where(side[sel] > 0, P[sel], 1 - P[sel])
        won = np.where(side[sel] > 0, OUT[sel], 1 - OUT[sel])
        r = {"bets": int(sel.sum()), "events": int(len(np.unique(EV[sel]))), "avg_price": round(float(price.mean()), 3)}
        for cost in (0.01, 0.02, 0.03):
            r[f"cost{int(cost*100)}c"] = ci(won / np.clip(price + cost, 0.001, 0.999) - 1, EV[sel])
        out[seg] = r
    return out


def score_swing(side, mask, k=1):
    """buy now, sell after 1 day (FUT[:,1]); profit per $1 = (exit - cost)/(entry + cost) - 1."""
    out = {}
    fut = FUT[:, k]
    for seg, m in (("all", mask), ("active", mask & ACTIVE)):
        sel = m & (side != 0) & ~np.isnan(fut)
        if sel.sum() < 100:
            out[seg] = None
            continue
        entry = np.where(side[sel] > 0, P[sel], 1 - P[sel])
        exit_ = np.where(side[sel] > 0, fut[sel], 1 - fut[sel])
        r = {"trades": int(sel.sum()), "events": int(len(np.unique(EV[sel])))}
        for cost in (0.01, 0.02, 0.03):
            r[f"cost{int(cost*100)}c"] = ci(np.clip(exit_ - cost, 0, 1) / np.clip(entry + cost, 0.001, 0.999) - 1, EV[sel])
        out[seg] = r
    return out


def side_from_edge(edge, thr):
    return np.where(edge > thr, 1, np.where(edge < -thr, -1, 0))


def lin_design(Xm):
    p = Xm[:, F.index("p")]
    ex = [p * Xm[:, F.index(n)] for n in ("chg_1d", "chg_7d", "deadline", "log_days_left")]
    ex += [p ** 2, (p < 0.2) * 1.0, (p > 0.8) * 1.0]
    return np.column_stack([Xm] + ex)


GB = dict(max_iter=300, learning_rate=0.05, max_leaf_nodes=31, min_samples_leaf=500, l2_regularization=1.0, random_state=0)
EXPS = {}


def model_edges():
    """Each returns predicted error (first side) for every row; trained on TR only."""
    E = {}
    sc = StandardScaler().fit(lin_design(X[TR]))
    E["M1 ridge (linear)"] = Ridge(alpha=1000).fit(sc.transform(lin_design(X[TR])), y[TR]).predict(sc.transform(lin_design(X)))
    E["M2 boosted trees"] = HistGradientBoostingRegressor(**GB).fit(X[TR], y[TR]).predict(X)
    clf = HistGradientBoostingClassifier(**GB).fit(X[TR], OUT[TR].astype(int))
    E["M3 boosted classifier (win chance)"] = clf.predict_proba(X)[:, 1] - P
    lr = LogisticRegression(C=0.1, max_iter=2000).fit(sc.transform(lin_design(X[TR])), OUT[TR].astype(int))
    E["M4 logistic (win chance)"] = lr.predict_proba(sc.transform(lin_design(X)))[:, 1] - P
    sp = c("cat_Sports") == 1
    e = np.zeros(len(y))
    for g in (sp, ~sp):
        e[g] = HistGradientBoostingRegressor(**GB).fit(X[TR & g], y[TR & g]).predict(X[g])
    E["M5 separate models: sports / rest"] = e
    short = DAYS <= 3
    e = np.zeros(len(y))
    for g in (short, ~short):
        e[g] = HistGradientBoostingRegressor(**GB).fit(X[TR & g], y[TR & g]).predict(X[g])
    E["M6 separate models: <=3 days / longer"] = e
    E["M7 boosted, trained on active rows only"] = HistGradientBoostingRegressor(**GB).fit(X[TR & ACTIVE], y[TR & ACTIVE]).predict(X)
    return E


def rules():
    ch1, ch7, d = c("chg_1d"), c("chg_7d"), DAYS
    R = {}
    R["R1 fade 1-day jump >15c"] = np.where(ch1 > .15, -1, np.where(ch1 < -.15, 1, 0))
    R["R2 fade 1-day jump >25c"] = np.where(ch1 > .25, -1, np.where(ch1 < -.25, 1, 0))
    R["R3 fade 7-day move >25c"] = np.where(ch7 > .25, -1, np.where(ch7 < -.25, 1, 0))
    R["R4 follow 7-day move >25c (momentum)"] = -R["R3 fade 7-day move >25c"]
    R["R5 long shot 5-20c, 7 days out"] = np.where((d == 7) & (P >= .05) & (P < .2), 1,
                                                   np.where((d == 7) & (P > .8) & (P <= .95), -1, 0))
    R["R6 favorite 80-95c, 1 day out"] = np.where((d == 1) & (P >= .8) & (P <= .95), 1,
                                                  np.where((d == 1) & (P >= .05) & (P <= .2), -1, 0))
    R["R7 'No' on 'by <date>?' questions 7d out"] = np.where((c("deadline") == 1) & (d == 7) & (c("yes_no") == 1), -1, 0)
    return R


def main(lockbox=False):
    res = {"setup": {"train": int(TR.sum()), "validation": int(VA.sum()), "lockbox": int(LB.sum())}, "hold": {}, "swing": {}}
    E = model_edges()
    for name, e in E.items():
        for thr in (0.03, 0.06):
            res["hold"][f"{name}, edge>{int(thr*100)}c"] = score_hold(side_from_edge(e, thr), VA)
    for name, s in rules().items():
        res["hold"][name] = score_hold(s, VA)

    # swing: predict the 1-day price change instead of the final result
    dp = FUT[:, 1] - P
    ok = TR & ~np.isnan(dp)
    pred = HistGradientBoostingRegressor(**GB).fit(X[ok], dp[ok]).predict(X)
    for thr in (0.03, 0.06):
        res["swing"][f"S1 boosted 1-day move, edge>{int(thr*100)}c"] = score_swing(side_from_edge(pred, thr), VA)
    for name, s in list(rules().items())[:4]:
        res["swing"][f"{name} (exit after 1 day)"] = score_swing(s, VA)

    if lockbox:
        res["lockbox"] = {}
        for name, e in E.items():
            res["lockbox"][f"{name}, edge>3c"] = score_hold(side_from_edge(e, 0.03), LB)
        for name, s in rules().items():
            res["lockbox"][name] = score_hold(s, LB)
        res["lockbox"]["S1 swing edge>3c"] = score_swing(side_from_edge(pred, 0.03), LB)

    json.dump(res, open("results/experiments.json", "w"), indent=1)
    for kind in ("hold", "swing") + (("lockbox",) if lockbox else ()):
        print(f"\n== {kind}   [profit per $1 at 2c cost: mean (95% range)]   all rows | active rows")
        for name, r in res[kind].items():
            cell = lambda z: "-" if not z else f"{z['cost2c'][0]:+.3f} ({z['cost2c'][1]:+.3f},{z['cost2c'][2]:+.3f}) n={z.get('bets', z.get('trades'))}"  # noqa: E731
            print(f"{name:52} {cell(r['all']):38} | {cell(r['active'])}")


if __name__ == "__main__":
    main("--lockbox" in sys.argv)
