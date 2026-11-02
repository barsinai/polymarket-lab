"""Toxic flow: after a taker trade, does the price keep going the trade's way (informed flow,
bad for a market maker who was on the other side) or come back (noise, good)?

For each market in the trades sample with a price history: take every trade of >= $20
(buys of side 0 as +1, sells / buys of side 1 as -1), and measure the mid-price move in the
trade's direction over the next 1h, 6h and 24h from the hourly price history. A market
maker filled by that trade loses roughly that drift (minus the half-spread earned).
Reported by: market kind, hour of day (UTC), days to end, trade size, and reward-programme
membership proxy (question template). Output: results/toxicity.json
"""
import glob, gzip, json, os, re
from collections import defaultdict
from datetime import datetime, timezone
import numpy as np
exec(open("research/costs.py").read().split("meta = {}")[0].split("def main")[0])  # kind(), tier(), band()

hist, info = {}, {}
need = set()
for f in glob.glob("data/trades/parts/*.jsonl.gz"):
    for line in gzip.open(f, "rt"):
        i = line.find('"market_id":"'); need.add(line[i + 13:line.index('"', i + 13)])
for f in glob.glob("data/listing/*.gz"):
    for line in gzip.open(f, "rt"):
        i = line.find('"id":"'); mid = line[i + 6:line.index('"', i + 6)]
        if mid in need:
            m = json.loads(line)
            try:
                end = datetime.fromisoformat(m["endDate"].replace("Z", "+00:00")).timestamp()
            except (KeyError, ValueError, AttributeError):
                continue
            info[mid] = (kind((m.get("question") or "").lower()), end, float(m.get("volumeNum") or 0))
for root, _, files in os.walk("data/prices"):
    for fn in files:
        if fn.endswith(".jsonl.gz"):
            for line in gzip.open(os.path.join(root, fn), "rt"):
                r = json.loads(line)
                if r["market_id"] in info and r["tokens"] and r["tokens"][0]["history"] and r["market_id"] not in hist:
                    a = np.array(r["tokens"][0]["history"], float); hist[r["market_id"]] = (a[:, 0], a[:, 1])
print(f"{len(hist)} markets with trades + history", flush=True)


def px(h, t):
    t_, p_ = h
    j = np.searchsorted(t_, t, side="right") - 1
    return p_[j] if j >= 0 and t - t_[j] <= 3 * 3600 else None


acc = defaultdict(lambda: {"n": 0, "d1": 0.0, "d6": 0.0, "d24": 0.0, "usd": 0.0})
H = 3600
for f in glob.glob("data/trades/parts/*.jsonl.gz"):
    for line in gzip.open(f, "rt"):
        r = json.loads(line); mid = r["market_id"]
        if mid not in hist:
            continue
        h = hist[mid]; k, end, vol = info[mid]
        for t in r["trades"]:
            ts_, side, oc, price, size = t[0], t[1], t[2], t[3], t[4]
            usd = price * size
            if usd < 20 or end - ts_ < 2 * H:
                continue
            d = 1 if (side == 1) == (oc == 0) else -1  # pressure on side 0's price
            p0 = px(h, ts_)
            if p0 is None or not (0.03 < p0 < 0.97):
                continue
            p1, p6, p24 = px(h, ts_ + H), px(h, ts_ + 6 * H), px(h, ts_ + 24 * H)
            if p1 is None or p6 is None:
                continue
            p24 = p24 if p24 is not None else p6
            dd = end - ts_
            keys = [("kind", k), ("hour_utc", f"{datetime.fromtimestamp(ts_, timezone.utc).hour:02d}"),
                    ("days_to_end", "<1d" if dd < 86400 else "1-3d" if dd < 3 * 86400 else "3-7d" if dd < 7 * 86400 else "7-30d" if dd < 30 * 86400 else ">30d"),
                    ("trade_usd", "$20-100" if usd < 100 else "$100-500" if usd < 500 else "$500-2k" if usd < 2000 else ">$2k"),
                    ("price", band(p0)), ("all", "all")]
            for g, v in keys:
                a = acc[(g, v)]
                a["n"] += 1; a["usd"] += usd
                a["d1"] += d * (p1 - p0); a["d6"] += d * (p6 - p0); a["d24"] += d * (p24 - p0)
out = {}
for (g, v), a in sorted(acc.items()):
    if a["n"] >= 200:
        out[f"{g} | {v}"] = {"trades": a["n"], "drift_1h_c": round(100 * a["d1"] / a["n"], 2),
                             "drift_6h_c": round(100 * a["d6"] / a["n"], 2), "drift_24h_c": round(100 * a["d24"] / a["n"], 2)}
json.dump(out, open("results/toxicity.json", "w"), indent=1)
print(f"{'group':28} {'trades':>8}  after 1h   6h   24h  (cents the price moved in the trade's direction)")
for k_, v in out.items():
    print(f"{k_:28} {v['trades']:8}  {v['drift_1h_c']:+5.2f} {v['drift_6h_c']:+5.2f} {v['drift_24h_c']:+5.2f}")
