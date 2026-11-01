"""Crypto 'Will <coin> be above $X on <date>?' markets vs a simple fair value.

Fair value at moment t (using only exchange prices from >= LAG_H hours before t, so the
exchange price is never fresher than the market price it is compared with) (1, 2, 3, 5, 7 days before the scheduled end): chance the exchange
price ends above X, assuming log-price moves randomly with the volatility seen over the past
7 days: P = N( ln(S/X) / (sigma_hourly * sqrt(hours left)) ). No drift.
Compares accuracy (Brier score: lower = better) of the market price vs the fair value, and a
strategy that buys whichever side the fair value says is cheap by more than a threshold,
at typical measured costs. Split before May (look) / Jun-Oct (confirm).
"""
import glob, gzip, json, math, os, re
import numpy as np
os.environ.setdefault("COSTSTAT", "median")
src = open("research/rescore_costs.py").read().split("sc = StandardScaler()")[0]
exec(src)
from math import erf, sqrt
Phi = lambda z: 0.5 * (1 + erf(z / sqrt(2)))  # noqa: E731

COIN = {"bitcoin": "BTC", "btc": "BTC", "ethereum": "ETH", "eth": "ETH", "solana": "SOL", "sol": "SOL",
        "xrp": "XRP", "dogecoin": "DOGE", "doge": "DOGE"}
px = {}
for c in set(COIN.values()):
    f = f"data/external/crypto/{c}.json.gz"
    if os.path.exists(f):
        a = np.array(json.load(gzip.open(f, "rt")), dtype=float)
        px[c] = (a[:, 0], a[:, 4])
print("coins with prices:", sorted(px))
RX = re.compile(r"(bitcoin|btc|ethereum|eth|solana|sol|xrp|dogecoin|doge)\b.*?\babove \$?([\d,]+(?:\.\d+)?)\s*(k)?\b.*?\bon\b", re.I)
ids = set(MID.astype(int)); Q = {}
for f in glob.glob("data/listing/*.gz"):
    for l in gzip.open(f, "rt"):
        i = l.find('"id":"'); mid = int(l[i + 6:l.index('"', i + 6)])
        if mid in ids:
            m = json.loads(l); q = m.get("question") or ""
            mm = RX.search(q)
            outs = json.loads(m.get("outcomes") or "[]")
            if mm and outs[:1] == ["Yes"]:
                strike = float(mm.group(2).replace(",", "")) * (1000 if mm.group(3) else 1)
                end = m.get("endDate")
                Q[mid] = (COIN[mm.group(1).lower()], strike, datetime.fromisoformat(end.replace("Z", "+00:00")).timestamp(), q)
print(f"{len(Q)} 'above $X on date' crypto markets in the table")
LAG_H = float(os.environ.get("LAG_H", "1"))  # use only exchange candles that CLOSED this many hours before t
rows = []
for i in np.where(np.isin(MID.astype(int), list(Q)))[0]:
    coin, K_, end, q = Q[int(MID[i])]
    if coin not in px:
        continue
    t_, c_ = px[coin]
    # candle timestamps are candle START; a candle starting at s closes at s+1h
    j = np.searchsorted(t_, T[i] - LAG_H * 3600 - 3600, side="right") - 1
    if j < 168 or (T[i] - LAG_H * 3600 - 3600) - t_[j] > 2 * 3600:
        continue
    S_ = c_[j]
    r = np.diff(np.log(c_[j - 168:j + 1]))
    sig = r.std()
    hrs = max((end - T[i]) / 3600, 1)
    fair = Phi(math.log(S_ / K_) / (sig * math.sqrt(hrs)))
    rows.append((i, min(max(fair, 0.001), 0.999)))
ii = np.array([a for a, _ in rows]); fair = np.array([b for _, b in rows])
mkt, out = P[ii], OUT[ii]
res = {"markets_rows": len(ii)}
for name, m in (("before May", TR[ii]), ("Jun-Oct", (VA | LB)[ii]), ("all", np.ones(len(ii), bool))):
    if m.sum() < 30:
        continue
    r = {"rows": int(m.sum()), "brier_market": round(float(np.mean((mkt[m] - out[m]) ** 2)), 4),
         "brier_fair_value": round(float(np.mean((fair[m] - out[m]) ** 2)), 4),
         "brier_average_of_both": round(float(np.mean(((mkt[m] + fair[m]) / 2 - out[m]) ** 2)), 4)}
    for thr in (0.03, 0.06, 0.10):
        edge = fair - mkt
        s = np.where(edge > thr, 1, np.where(edge < -thr, -1, 0))
        sel = m & (s != 0)
        if sel.sum() < 20:
            continue
        price = np.where(s[sel] > 0, mkt[sel], 1 - mkt[sel]); won = np.where(s[sel] > 0, out[sel], 1 - out[sel])
        cost = np.array([cost_of(p, i) for p, i in zip(price, ii[sel])])
        r[f"bet when fair differs >{int(thr*100)}c"] = {"bets": int(sel.sum()), "events": int(len(np.unique(EV[ii][sel]))),
                                                        "profit_per_$": ci(won / np.clip(price + cost, 0, .999) - 1, EV[ii][sel])}
    res[name] = r
    print(name, json.dumps(r))
res["lag_hours"] = LAG_H
json.dump(res, open(f"results/exp_crypto_lag{int(LAG_H)}.json", "w"), indent=1)
