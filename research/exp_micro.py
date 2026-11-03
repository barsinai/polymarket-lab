"""Hourly-book microstructure for the market-making universe (reward markets, recorded hourly).

Questions, each a possible rule for the quoter:
 1. Book imbalance / microprice -> does it predict the next hour's mid move?  (quote lean)
 2. Does the last hour's move continue or reverse?                            (lean / pause)
 3. Competition (depth inside the reward band) by market age, hour of day, weekday.
    Where and when is the reward pool least crowded?                          (timing / new markets)
 4. Size of hourly moves by category and hour of day.                        (when to stand aside)
Output: results/exp_micro.json
"""
import glob, gzip, json
from collections import defaultdict
from datetime import datetime, timezone
import numpy as np
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import collect  # noqa: E402

meta = {}
for f in sorted(glob.glob("data/live/meta/*.jsonl.gz")):
    for m in collect.read_jsonl_gz(f):
        meta[m["id"]] = m
rw = {}
for f in sorted(glob.glob("data/live/rewards/*.jsonl.gz")):
    for m in collect.read_jsonl_gz(f):
        r = m.get("rewards") or {}
        rate = sum(x.get("rewards_daily_rate") or 0 for x in r.get("rates") or [])
        if rate > 0 and r.get("max_spread"):
            tags = [t for t in collect.as_list(m.get("tags")) or [] if isinstance(t, str)]
            rw[m["condition_id"]] = (rate, float(r["max_spread"]), float(r.get("min_size") or 0), tags, m.get("taker_base_fee"))
print(f"{len(meta)} meta, {len(rw)} reward markets", flush=True)

CAT = ["Politics", "Sports", "Crypto", "Geopolitics", "Business", "Finance", "Pop Culture", "Science", "Weather", "Economy", "Tech"]


def cat_of(tags):
    for c in CAT:
        if any(c.lower() == t.lower() for t in tags):
            return c
    return "Other"


def ts(s):
    if not s:
        return None
    s = s.replace(" ", "T").replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(s).timestamp()
    except ValueError:
        return None


rows = []  # per (market, hour)
snaps = sorted(glob.glob("data/live/20*/*.json.gz"))
for f in snaps:
    d = json.load(gzip.open(f))
    if "market_columns" not in d:
        continue
    now = d["ts"]
    for mid, r in d["markets"].items():
        m = meta.get(mid)
        if not m or m.get("conditionId") not in rw:
            continue
        b = d["books"].get(f"{mid}:0")
        if not b or not b[2] or not b[3]:
            continue
        bids, asks = b[2], b[3]
        bb, ba = bids[0][0], asks[0][0]
        if ba - bb > 0.10 or not (0.05 < (bb + ba) / 2 < 0.95):
            continue
        rate, v, minsize, tags, fee = rw[m["conditionId"]]
        midp = (bb + ba) / 2
        vb = v / 100
        db2 = sum(s for p, s in bids if midp - p <= 0.02); da2 = sum(s for p, s in asks if p - midp <= 0.02)
        dbv = sum(s for p, s in bids if midp - p <= vb and s >= minsize); dav = sum(s for p, s in asks if p - midp <= vb and s >= minsize)
        sb, sa = bids[0][1], asks[0][1]
        micro = (bb * sa + ba * sb) / (sa + sb) if sa + sb > 0 else midp
        age = (now - (ts(m.get("createdAt")) or now)) / 86400
        tte = ((ts(m.get("endDate")) or now) - now) / 86400
        rows.append((m["conditionId"], now, midp, ba - bb, db2, da2, dbv, dav, micro, age, tte, rate, cat_of(tags)))
print(f"{len(rows)} market-hours", flush=True)

# index by market -> sorted hours
by = defaultdict(list)
for r in rows:
    by[r[0]].append(r)
X = []  # imbalance, micro-mid, dmid_prev, dmid_next, spread, cat, hour, weekday, age, tte, comp, rate
for cid, rs in by.items():
    rs.sort(key=lambda r: r[1])
    for i in range(1, len(rs) - 1):
        p, c, n = rs[i - 1], rs[i], rs[i + 1]
        if not (3000 <= c[1] - p[1] <= 4200 and 3000 <= n[1] - c[1] <= 4200):
            continue
        imb = (c[4] - c[5]) / (c[4] + c[5]) if c[4] + c[5] > 0 else 0.0
        dt = datetime.fromtimestamp(c[1], timezone.utc)
        X.append((imb, c[8] - c[2], c[2] - p[2], n[2] - c[2], c[3], c[12], dt.hour, dt.weekday(), c[9], c[10], c[6] + c[7], c[11], c[2]))
cats = [x[5] for x in X]
A = np.array([x[:5] + x[6:] for x in X], dtype=float)
imb, dmic, dprev, dnext, spr, hour, wday, age, tte, comp, rate, midp = A.T
print(f"{len(A)} usable hours", flush=True)
out = {"market_hours": len(A)}


def by_decile(sig, y, k=10):
    q = np.quantile(sig, np.linspace(0, 1, k + 1)); res = []
    for a, b in zip(q[:-1], q[1:]):
        s = (sig >= a) & (sig <= b)
        res.append({"lo": round(float(a), 4), "hi": round(float(b), 4), "n": int(s.sum()), "mean_cents": round(float(y[s].mean() * 100), 3)})
    return res


# 1. imbalance & microprice
out["imbalance"] = {"corr_next": round(float(np.corrcoef(imb, dnext)[0, 1]), 4), "deciles": by_decile(imb, dnext)}
out["microprice"] = {"corr_next": round(float(np.corrcoef(dmic, dnext)[0, 1]), 4),
                     "mse_mid": round(float((dnext ** 2).mean() * 1e4), 4), "mse_micro": round(float(((dnext - dmic) ** 2).mean() * 1e4), 4),
                     "mse_half_micro": round(float(((dnext - 0.5 * dmic) ** 2).mean() * 1e4), 4)}
# tight books only (where we quote): spread <= 4c
t = spr <= 0.04
out["imbalance_tight"] = {"n": int(t.sum()), "corr_next": round(float(np.corrcoef(imb[t], dnext[t])[0, 1]), 4), "deciles": by_decile(imb[t], dnext[t], 5)}
# 2. momentum / reversal
out["momentum"] = {"corr_prev_next": round(float(np.corrcoef(dprev, dnext)[0, 1]), 4), "deciles": by_decile(dprev, dnext)}
big = np.abs(dprev) >= 0.03
out["after_big_move_3c"] = {"n": int(big.sum()), "mean_continuation_cents": round(float((np.sign(dprev[big]) * dnext[big]).mean() * 100), 3)}
# 3. competition
def group(keys, vals, fn=np.median):
    res = {}
    for k in sorted(set(keys.tolist() if hasattr(keys, "tolist") else keys)):
        s = np.array([x == k for x in keys]) if not hasattr(keys, "tolist") else keys == k
        res[str(k)] = {"n": int(s.sum()), "median_comp_shares": round(float(np.median(vals[s]))), "median_reward_per_1k_comp": round(float(np.median(rate[s] / np.maximum(vals[s], 1) * 1000)), 3)}
    return res
age_b = np.digitize(age, [1, 3, 7, 14, 30, 90])
out["competition_by_age_days"] = {["<1", "1-3", "3-7", "7-14", "14-30", "30-90", ">90"][k]: v for k, v in zip(range(7), group(age_b, comp).values())}
out["competition_by_hour_utc"] = group(hour.astype(int), comp)
out["competition_by_weekday"] = group(wday.astype(int), comp)
catarr = np.array(cats)
out["competition_by_category"] = group(catarr, comp)
# 4. move size
out["abs_move_by_category_cents"] = {c: round(float(np.abs(dnext[catarr == c]).mean() * 100), 3) for c in sorted(set(cats))}
out["abs_move_by_hour_cents"] = {int(h): round(float(np.abs(dnext[hour == h]).mean() * 100), 3) for h in range(24)}
out["abs_move_by_age"] = {["<1", "1-3", "3-7", "7-14", "14-30", "30-90", ">90"][k]: round(float(np.abs(dnext[age_b == k]).mean() * 100), 3) for k in range(7) if (age_b == k).any()}
json.dump(out, open("results/exp_micro.json", "w"), indent=1)
print(json.dumps({k: out[k] for k in ("imbalance", "microprice", "momentum", "after_big_move_3c")}, indent=1))
print("imbalance tight:", out["imbalance_tight"]["corr_next"], out["imbalance_tight"]["deciles"])
for k in ("competition_by_age_days", "competition_by_hour_utc", "competition_by_weekday", "competition_by_category", "abs_move_by_category_cents", "abs_move_by_age"):
    print(k, json.dumps(out[k]))
