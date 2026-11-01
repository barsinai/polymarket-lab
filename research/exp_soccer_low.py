"""Hypothesis: in soccer, 'few goals' outcomes are underpriced on Polymarket.
Test every soccer market of these types, ONE bet per market (1 day before the scheduled
kick-off), buying the 'few goals' side, at real measured costs:
  O/U 0.5 -> Under (0-0), O/U 1.5 -> Under, O/U 2.5 -> Under, 'Exact Score: X 0 - 0 Y?' -> Yes,
  'end in a draw?' -> Yes, 'Both Teams to Score?' -> No
Shown separately for training-period (before May) and test-period (Jun-Oct) markets."""
import glob, gzip, json, re
import numpy as np
src = open("research/rescore_costs.py").read().split("sc = StandardScaler()")[0]
exec(src)
ids = set(MID.astype(int)); info_q = {}
for f in glob.glob("data/listing/*.gz"):
    for l in gzip.open(f, "rt"):
        i = l.find('"id":"'); mid = int(l[i + 6:l.index('"', i + 6)])
        if mid in ids:
            m = json.loads(l); info_q[mid] = (m.get("question") or "", json.loads(m.get("outcomes") or "[]"))
TYPES = [("O/U 0.5 -> Under", r"o/u 0\.5\b", "Under"), ("O/U 1.5 -> Under", r"o/u 1\.5\b", "Under"),
         ("O/U 2.5 -> Under", r"o/u 2\.5\b", "Under"), ("Exact score 0-0 -> Yes", r"exact score: .* 0 - 0 ", "Yes"),
         ("Draw -> Yes", r"end in a draw", "Yes"), ("Both teams to score -> No", r"both teams to score", "No")]
res = {}
for name, rx, want in TYPES:
    for period, mask in (("before May (training period)", TR), ("Jun-Oct (test period)", VA | LB)):
        sel = []
        for i in np.where(mask & (DAYS == 1))[0]:
            q, outs = info_q.get(int(MID[i]), ("", []))
            if re.search(rx, q.lower()) and want in outs:
                sel.append((i, outs.index(want)))
        if len(sel) < 30:
            continue
        ii = np.array([a for a, _ in sel]); sd = np.array([b for _, b in sel])
        price = np.where(sd == 0, P[ii], 1 - P[ii]); won = np.where(sd == 0, OUT[ii], 1 - OUT[ii])
        cost = np.array([cost_of(p, i) for p, i in zip(price, ii)])
        r = ci(won / np.clip(price + cost, 0, .999) - 1, EV[ii])
        res[f"{name} | {period}"] = {"markets": len(ii), "avg_price": round(float(price.mean()), 3),
                                     "actual_win_rate": round(float(won.mean()), 3), "avg_cost_c": round(100 * float(cost.mean()), 2),
                                     "profit_per_$": r}
        print(f"{name:28} {period:30} markets={len(ii):5} price {price.mean():.3f} actually won {won.mean():.3f}  profit/$ {r}")
json.dump(res, open("results/exp_soccer_low.json", "w"), indent=1)
