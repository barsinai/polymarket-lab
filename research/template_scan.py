"""Lead finder: which kinds of question (templates) are consistently mispriced?

Template = question text with numbers -> #, capitalised words (names) -> X, so e.g.
"Will the highest temperature in Dallas be between 70-71F on November 1?" becomes
"will the highest temperature in X be between #-#f on X #?".
For every template with enough markets, one row per market at each horizon (1, 3, 7 days
before scheduled end): average (did the first side win) - (its price). Templates are FOUND on
the training period (before May 2026) and only those passing there are CONFIRMED on the test
period (Jun-Oct, unseen events), with real measured costs, betting the side that was cheap.
Output: results/template_scan.json
"""
import glob, gzip, json, re
from collections import defaultdict
import numpy as np
src = open("research/rescore_costs.py").read().split("sc = StandardScaler()")[0]
exec(src)


def template(q):
    q = re.sub(r"\d+([.,]\d+)?", "#", q)
    q = re.sub(r"\b[A-Z][\w'.&-]*", "X", q)
    q = re.sub(r"(X[\s.,]*)+X", "X", q)
    return q.lower().strip()


ids = set(MID.astype(int)); TPL = {}
for f in glob.glob("data/listing/*.gz"):
    for l in gzip.open(f, "rt"):
        i = l.find('"id":"'); mid = int(l[i + 6:l.index('"', i + 6)])
        if mid in ids:
            TPL[mid] = template(json.loads(l).get("question") or "")
tp = np.array([TPL.get(int(m), "") for m in MID])

res = {"found": [], "confirmed": []}
for d in (1, 3, 7):
    rows = DAYS == d
    for period_mask, key in ((TR, "found"),):
        groups = defaultdict(list)
        for i in np.where(rows & period_mask & ACTIVE)[0]:
            groups[tp[i]].append(i)
        for t, ii in groups.items():
            if len(ii) < 150 or not t:
                continue
            ii = np.array(ii)
            err = OUT[ii] - P[ii]
            lo, hi = ci(err, EV[ii])[1:]
            if lo > 0.01 or hi < -0.01:  # first side consistently too cheap / too expensive
                side = 1 if lo > 0 else -1
                res["found"].append({"template": t, "days": d, "markets": len(ii), "events": int(len(np.unique(EV[ii]))),
                                     "first_side_mispriced_by_c": round(100 * float(err.mean()), 2), "buy": "first" if side > 0 else "second"})
                # confirm on the test period
                jj = np.where(rows & (VA | LB) & ACTIVE & (tp == t))[0]
                if len(jj) < 50:
                    continue
                price = P[jj] if side > 0 else 1 - P[jj]
                won = OUT[jj] if side > 0 else 1 - OUT[jj]
                cost = np.array([cost_of(p, i) for p, i in zip(price, jj)])
                r = ci(won / np.clip(price + cost, 0, .999) - 1, EV[jj])
                res["confirmed"].append({"template": t, "days": d, "buy": "first" if side > 0 else "second",
                                         "train_mispricing_c": round(100 * float(err.mean()), 2),
                                         "test_markets": len(jj), "test_events": int(len(np.unique(EV[jj]))),
                                         "test_avg_price": round(float(price.mean()), 3), "test_win_rate": round(float(won.mean()), 3),
                                         "test_avg_cost_c": round(100 * float(cost.mean()), 2), "test_profit_per_$": r})
json.dump(res, open("results/template_scan.json", "w"), indent=1)
print(f"{len(res['found'])} template/horizon combos mispriced in training; {len(res['confirmed'])} testable")
for r in sorted(res["confirmed"], key=lambda r: -r["test_profit_per_$"][1]):
    flag = "PASS" if r["test_profit_per_$"][1] > 0 else "    "
    print(f"{flag} d={r['days']} buy {r['buy']:6} train {r['train_mispricing_c']:+5.1f}c | test n={r['test_markets']:5} ev={r['test_events']:4} "
          f"price {r['test_avg_price']:.2f} won {r['test_win_rate']:.2f} cost {r['test_avg_cost_c']:.1f}c profit {r['test_profit_per_$']} | {r['template'][:80]}")
