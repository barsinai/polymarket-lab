"""Soccer draws by league (from Polymarket event tags) - is the underpricing everywhere?"""
import glob, gzip, json, os
from collections import Counter, defaultdict
import numpy as np
os.environ.setdefault("COSTSTAT", "median")
exec(open("research/exp_draws.py").read().split("res = {}")[0])
tags = {}
for e in gzip.open("data/events_closed.jsonl.gz", "rt"):
    e = json.loads(e)
    tags[int(e["id"])] = [t.get("label") for t in e.get("tags") or []]
GENERIC = {"Sports", "Soccer", "Games", "Football", "All", "Hide From New", "Recurring", "Weekly", "Daily"}
lg = []
for i in ii:
    t = [x for x in tags.get(int(EV[i]), []) if x and x not in GENERIC]
    lg.append(t[0] if t else "unknown")
lg = np.array(lg)
print("tag coverage:", np.mean(lg != "unknown").round(3))
res = {}
for name, cnt in Counter(lg).most_common(25):
    m = lg == name
    if m.sum() < 60:
        continue
    r = {"markets": int(m.sum()), "price": round(float(price[m].mean()), 3), "won": round(float(won[m].mean()), 3),
         "gap_c": round(100 * float((won[m] - price[m]).mean()), 1), "profit_per_$": ci(ret[m], EV[ii][m])}
    res[name] = r
    print(f"{name:28} n={r['markets']:5} draw price {r['price']:.3f} happened {r['won']:.3f} gap {r['gap_c']:+5.1f}c profit/$ {r['profit_per_$']}")
json.dump(res, open("results/exp_draws_league.json", "w"), indent=1)
