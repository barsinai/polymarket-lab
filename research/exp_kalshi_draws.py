"""Soccer draws: Kalshi vs Polymarket.

1. Kalshi on its own: tie price 24h before kick-off (midpoint of best bid/ask) vs how often
   ties happened - does Kalshi underprice draws too?
2. Same games on both sites (matched by kick-off time within 3h + both team names appearing
   in the Polymarket question): at the Polymarket bet moment (1 day before kick-off), compare
   the two prices. When Kalshi prices the draw higher by > threshold, buy the Polymarket draw
   (typical measured costs). Also: is the average of the two prices more accurate?
"""
import glob, gzip, json, os, re
from collections import defaultdict
import numpy as np
os.environ.setdefault("COSTSTAT", "median")
exec(open("research/exp_draws.py").read().split("res = {}")[0])  # Polymarket draw rows: ii, price, won, cost, ret

K = [json.loads(l) for l in gzip.open("data/external/kalshi/ties.jsonl.gz", "rt")]
print(f"{len(K)} Kalshi tie markets with history")


def kmid(c, t, max_gap=3 * 3600):
    best = None
    for ts_, b, a, p, v in c:
        if ts_ is None or ts_ > t:
            continue
        if b is not None and a is not None and 0 < b < a < 1:
            m_ = (b + a) / 2
        elif p is not None:
            m_ = p
        else:
            continue
        best = (ts_, m_)
    return best[1] if best and t - best[0] <= max_gap else None


# 1) Kalshi calibration
kp, ko_, kl = [], [], []
for k in K:
    m_ = kmid(k["candles"], k["kickoff"] - 86400)
    if m_ is not None and 0.03 < m_ < 0.6:
        kp.append(m_); ko_.append(1.0 if k["result"] == "yes" else 0.0); kl.append(k["series"])
kp, ko_, kl = map(np.array, (kp, ko_, kl))
res = {"kalshi_alone": {"games": int(len(kp)), "avg_price": round(float(kp.mean()), 4), "tie_rate": round(float(ko_.mean()), 4)}}
print("Kalshi alone:", res["kalshi_alone"])
by = defaultdict(list)
for s, p, o in zip(kl, kp, ko_):
    by[s].append((p, o))
res["kalshi_by_league"] = {}
for s, v in sorted(by.items(), key=lambda x: -len(x[1]))[:15]:
    a = np.array(v)
    res["kalshi_by_league"][s] = {"games": len(a), "price": round(float(a[:, 0].mean()), 3), "ties": round(float(a[:, 1].mean()), 3)}
    print(f"  {s:24} games={len(a):5} tie price {a[:,0].mean():.3f} happened {a[:,1].mean():.3f}")

# 2) match with Polymarket draw markets
STOP = {"fc", "cf", "afc", "sc", "ac", "cd", "ca", "club", "de", "the", "united", "city", "real", "sporting", "fk", "sk", "if", "bk"}


def toks(s):
    return [w for w in re.findall(r"[a-zà-ÿ]+", s.lower()) if len(w) > 2 and w not in STOP]


byko = defaultdict(list)
for k in K:
    byko[k["kickoff"] // 3600].append(k)
need = set(MID[ii].astype(int)); QQ = {}
for f in glob.glob("data/listing/*.gz"):
    for l in gzip.open(f, "rt"):
        j = l.find('"id":"'); mid = int(l[j + 6:l.index('"', j + 6)])
        if mid in need:
            m = json.loads(l)
            QQ[mid] = (m.get("question") or "", m.get("endDate"))
pairs = []
for n_, i in enumerate(ii):
    q, end = QQ.get(int(MID[i]), ("", None))
    if not end:
        continue
    ko = int(datetime.fromisoformat(end.replace("Z", "+00:00")).timestamp())
    qt = set(toks(q))
    hit = None
    for h in range(ko // 3600 - 3, ko // 3600 + 4):
        for k in byko.get(h, []):
            tt = [toks(t) for t in k["teams"]]
            if len(tt) >= 2 and all(any(w in qt for w in t) for t in tt if t):
                hit = k
                break
        if hit:
            break
    if hit:
        km = kmid(hit["candles"], T[i])
        if km is not None:
            pairs.append((n_, km, hit["ticker"]))
print(f"matched {len(pairs)} Polymarket draw markets to Kalshi")
if pairs:
    nn = np.array([p[0] for p in pairs]); kk = np.array([p[1] for p in pairs])
    pm, wn, cs, rt = price[nn], won[nn], cost[nn], ret[nn]
    res["matched"] = {"games": int(len(nn)), "polymarket_avg": round(float(pm.mean()), 4), "kalshi_avg": round(float(kk.mean()), 4),
                      "tie_rate": round(float(wn.mean()), 4),
                      "brier_polymarket": round(float(np.mean((pm - wn) ** 2)), 5),
                      "brier_kalshi": round(float(np.mean((kk - wn) ** 2)), 5),
                      "brier_average": round(float(np.mean(((pm + kk) / 2 - wn) ** 2)), 5),
                      "profit_all_draws_polymarket": ci(rt, EV[ii][nn])}
    for thr in (0.0, 0.02, 0.04):
        sel = (kk - pm) > thr
        if sel.sum() >= 20:
            res["matched"][f"buy PM draw when Kalshi higher by >{int(thr*100)}c"] = {"bets": int(sel.sum()), "profit_per_$": ci(rt[sel], EV[ii][nn][sel])}
        sel2 = (pm - kk) > thr
        if sel2.sum() >= 20:
            res["matched"][f"(for contrast) buy PM draw when PM higher by >{int(thr*100)}c"] = {"bets": int(sel2.sum()), "profit_per_$": ci(rt[sel2], EV[ii][nn][sel2])}
    print(json.dumps(res["matched"], indent=1))
json.dump(res, open("results/exp_kalshi_draws.json", "w"), indent=1)
