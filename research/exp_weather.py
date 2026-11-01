"""Weather markets ("Will the highest temperature in <city> be <range> on <date>?") vs a
forecast-based fair value.

Forecast: the daily max of the hourly forecast made 2 days earlier (Open-Meteo previous runs),
so it was public before any bet placed 1+ day ahead. Per city, how far real outcomes fall from
that forecast (bias b, spread s) is FITTED on training-period markets (before May 2026) by
maximum likelihood on their actual Yes/No results. Fair chance of a range [lo, hi] (station
reports whole degrees): N((hi+.5-mu)/s) - N((lo-.5-mu)/s), mu = forecast + b.
Test: Jun-Oct markets; compare accuracy (Brier) with the market price, and bet whichever side
the fair value says is cheap by > threshold, at typical measured costs.
"""
import glob, gzip, json, math, os, re
from collections import defaultdict
from datetime import datetime, timedelta
import numpy as np
os.environ.setdefault("COSTSTAT", "median")
src = open("research/rescore_costs.py").read().split("sc = StandardScaler()")[0]
exec(src)
from math import erf, sqrt
Phi = np.vectorize(lambda z: 0.5 * (1 + erf(z / sqrt(2))))

# ---- forecasts: city -> {date: forecast max (C)}
FC = {}
for f in glob.glob("data/external/weather/*.json.gz"):
    city = os.path.basename(f)[:-8]
    d = json.load(gzip.open(f, "rt"))
    mx = defaultdict(list)
    for t, v in zip(d["time"], d["t2"]):
        if v is not None:
            mx[t[:10]].append(v)
    FC[city] = {k: max(v) for k, v in mx.items() if len(v) >= 20}
print(f"forecasts for {len(FC)} cities")

RX = re.compile(r"highest temperature in (.+?) be (?:between )?(-?\d+)(?:\s*-\s*(-?\d+))?\s*°\s*([CF])(?: (or higher|or below))? on (\w+ \d+)", re.I)
ids = set(MID.astype(int)); W = {}
for f in glob.glob("data/listing/*.gz"):
    for l in gzip.open(f, "rt"):
        if "temperature" not in l:
            continue
        i = l.find('"id":"'); mid = int(l[i + 6:l.index('"', i + 6)])
        if mid not in ids:
            continue
        m = json.loads(l); q = m.get("question") or ""
        mm = RX.search(q)
        if not mm or json.loads(m.get("outcomes") or "[]")[:1] != ["Yes"]:
            continue
        city, a, b, unit, tail, md = mm.groups()
        end = datetime.fromisoformat(m["endDate"].replace("Z", "+00:00"))
        try:
            day = datetime.strptime(f"{md} {end.year}", "%B %d %Y")
        except ValueError:
            continue
        if day.month == 12 and end.month == 1:
            day = day.replace(year=end.year - 1)
        a = int(a); b = int(b) if b else a
        lo, hi = (a, math.inf) if tail and "higher" in tail.lower() else (-math.inf, a) if tail else (a, b)
        W[mid] = (city, day.strftime("%Y-%m-%d"), lo, hi, unit.upper())
print(f"{len(W)} parsed temperature markets in the table")

rows = []
for i in np.where(np.isin(MID.astype(int), list(W)) & (DAYS <= 3))[0]:
    city, day, lo, hi, unit = W[int(MID[i])]
    f_ = FC.get(city, {}).get(day)
    if f_ is None:
        continue
    rows.append((i, city, f_, lo, hi, unit))
print(f"{len(rows)} rows with a forecast")
ii = np.array([r[0] for r in rows]); cities = np.array([r[1] for r in rows])
fc = np.array([r[2] for r in rows]); LO = np.array([r[3] for r in rows], float); HI = np.array([r[4] for r in rows], float)
unitF = np.array([r[5] == "F" for r in rows])


def fair(b, s, idx):
    mu = fc[idx] + b
    muU = np.where(unitF[idx], mu * 9 / 5 + 32, mu); sU = np.where(unitF[idx], s * 9 / 5, s)
    up = np.where(np.isinf(HI[idx]), 1.0, Phi((HI[idx] + 0.5 - muU) / sU))
    dn = np.where(np.isinf(LO[idx]), 0.0, Phi((LO[idx] - 0.5 - muU) / sU))
    return np.clip(up - dn, 0.002, 0.998)


# ---- fit bias and spread per city on training rows (1 day before), by likelihood of outcomes
par = {}
trn = TR[ii] & (DAYS[ii] == 1)
for city in np.unique(cities):
    idx = np.where(trn & (cities == city))[0]
    if len(idx) < 60:
        continue
    best = None
    for b in np.arange(-3, 3.01, 0.25):
        for s in np.arange(0.5, 4.01, 0.25):
            p = fair(b, s, idx); o = OUT[ii][idx]
            ll = np.sum(o * np.log(p) + (1 - o) * np.log(1 - p))
            if best is None or ll > best[0]:
                best = (ll, b, s)
    par[city] = best[1:]
print(f"fitted {len(par)} cities, e.g. {list(par.items())[:5]}")

res = {"cities_fitted": {c: [float(b), float(s)] for c, (b, s) in par.items()}}
use = np.array([c in par for c in cities])
fv = np.full(len(ii), np.nan)
for c, (b, s) in par.items():
    idx = np.where(cities == c)[0]
    fv[idx] = fair(b, s, idx)
mkt, out = P[ii], OUT[ii]
for name, m in (("training period (fit)", TR[ii] & use), ("Jun-Oct (test)", (VA | LB)[ii] & use)):
    for d in (1, 2, 3):
        mm_ = m & (DAYS[ii] == d)
        if mm_.sum() < 50:
            continue
        r = {"rows": int(mm_.sum()), "brier_market": round(float(np.mean((mkt[mm_] - out[mm_]) ** 2)), 4),
             "brier_fair": round(float(np.mean((fv[mm_] - out[mm_]) ** 2)), 4),
             "brier_blend": round(float(np.mean(((mkt[mm_] + fv[mm_]) / 2 - out[mm_]) ** 2)), 4)}
        for thr in (0.05, 0.10, 0.20):
            e = fv - mkt
            sd = np.where(e > thr, 1, np.where(e < -thr, -1, 0))
            sel = mm_ & (sd != 0)
            if sel.sum() < 20:
                continue
            price = np.where(sd[sel] > 0, mkt[sel], 1 - mkt[sel]); won = np.where(sd[sel] > 0, out[sel], 1 - out[sel])
            cost = np.array([cost_of(p, i) for p, i in zip(price, ii[sel])])
            r[f"fair differs >{int(thr*100)}c"] = {"bets": int(sel.sum()), "events": int(len(np.unique(EV[ii][sel]))),
                                                   "cost_c": round(100 * float(cost.mean()), 2),
                                                   "profit_per_$": ci(won / np.clip(price + cost, 0, .999) - 1, EV[ii][sel])}
        res[f"{name} | {d} day(s) before"] = r
        print(f"{name} | {d}d", json.dumps(r))
json.dump(res, open("results/exp_weather.json", "w"), indent=1)
