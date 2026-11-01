"""Soccer draws deep dive: where is the 'draw is underpriced' gap biggest?
One row per market (1 day before kick-off), buy 'Yes' on draw. Split by draw price
(lopsided match = cheap draw vs even match), market size, and period; typical (median) costs."""
import glob, gzip, json, os, re
import numpy as np
os.environ.setdefault("COSTSTAT", "median")
src = open("research/rescore_costs.py").read().split("sc = StandardScaler()")[0]
exec(src)
ids = set(MID.astype(int)); Q = {}
for f in glob.glob("data/listing/*.gz"):
    for l in gzip.open(f, "rt"):
        i = l.find('"id":"'); mid = int(l[i + 6:l.index('"', i + 6)])
        if mid in ids:
            m = json.loads(l); Q[mid] = ((m.get("question") or "").lower(), json.loads(m.get("outcomes") or "[]"))
rows = []
for i in np.where(DAYS == 1)[0]:
    q, outs = Q.get(int(MID[i]), ("", []))
    if "end in a draw" in q and "Yes" in outs:
        rows.append((i, outs.index("Yes")))
ii = np.array([a for a, _ in rows]); sd = np.array([b for _, b in rows])
price = np.where(sd == 0, P[ii], 1 - P[ii]); won = np.where(sd == 0, OUT[ii], 1 - OUT[ii])
cost = np.array([cost_of(p, i) for p, i in zip(price, ii)])
ret = won / np.clip(price + cost, 0, .999) - 1
res = {}
def show(name, m):
    if m.sum() < 40:
        return
    r = {"markets": int(m.sum()), "price": round(float(price[m].mean()), 3), "won": round(float(won[m].mean()), 3),
         "gap_c": round(100 * float((won[m] - price[m]).mean()), 2), "profit_per_$": ci(ret[m], EV[ii][m])}
    res[name] = r
    print(f"{name:34} n={r['markets']:5} price {r['price']:.3f} won {r['won']:.3f} gap {r['gap_c']:+5.1f}c profit/$ {r['profit_per_$']}")
show("all", np.ones(len(ii), bool))
for nm, m in (("before May", TR[ii]), ("Jun-Oct", (VA | LB)[ii])):
    show(nm, m)
for lo, hi in ((0, .2), (.2, .25), (.25, .3), (.3, .4)):
    show(f"draw priced {lo:.2f}-{hi:.2f}", (price >= lo) & (price < hi))
for lo, hi, lab in ((0, 2e4, "<$20k"), (2e4, 1e5, "$20-100k"), (1e5, 1e13, ">$100k")):
    show(f"market size {lab}", (VOL[ii] >= lo) & (VOL[ii] < hi))
show("active only", ACTIVE[ii])
json.dump(res, open("results/exp_draws.json", "w"), indent=1)
