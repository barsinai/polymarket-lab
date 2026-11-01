"""Market making for liquidity rewards: what would a small quoter earn, before risk?

Polymarket splits each market's daily reward pool among resting orders within max_spread of
the midpoint, by a score that falls off with distance: score = ((v - s)/v)^2 * size, with v the
max spread and s the order's distance from mid (both in cents), and orders below min_size not
counting. (Simplified: we score each side's book and use the smaller side for two-sided credit.)
For every reward market in the latest hourly snapshot: competing score on each side, and our
share if we rest q shares on BOTH sides at distance s. Capital tied up ~ q*(1 - 2s) dollars.
Gives reward $/day and reward yield per $ per day. Ignores: being filled and losing on price
moves (adverse selection) - that is the risk that must be measured next.
"""
import glob, gzip, json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import collect  # noqa: E402

rw = {}
for m in collect.read_jsonl_gz(sorted(glob.glob("data/live/rewards/*.jsonl.gz"))[-1]):
    r = m.get("rewards") or {}
    rate = sum(x.get("rewards_daily_rate") or 0 for x in r.get("rates") or [])
    if rate > 0 and r.get("max_spread"):
        rw[m["condition_id"]] = (rate, float(r["max_spread"]), float(r.get("min_size") or 0), m.get("question"))
meta = {}
for f in sorted(glob.glob("data/live/meta/*.jsonl.gz")):
    for m in collect.read_jsonl_gz(f):
        meta[m["id"]] = m
snap = json.load(gzip.open(sorted(glob.glob("data/live/2026-11-0*/*.json.gz"))[-1]))
cols = snap["market_columns"]
print(f"{len(rw)} markets with reward pools; snapshot {snap['iso'][:16]}")


def side_score(levels, mid, v, minsize, is_bid):
    sc = 0.0
    for p, size in levels:
        s = 100 * ((mid - p) if is_bid else (p - mid))
        if 0 <= s < v and size >= minsize:
            sc += ((v - s) / v) ** 2 * size
    return sc


rows = []
for mid_id, r in snap["markets"].items():
    m = meta.get(mid_id)
    if not m or m.get("conditionId") not in rw:
        continue
    rate, v, minsize, q = rw[m["conditionId"]]
    b0 = snap["books"].get(f"{mid_id}:0")
    if not b0 or not b0[2] or not b0[3]:
        continue
    bb, ba = b0[2][0][0], b0[3][0][0]
    mid = (bb + ba) / 2
    if not (0.05 < mid < 0.95):
        continue
    # bids on Yes, and asks on Yes (asks on Yes == bids on No, so one token's book covers both sides)
    sb = side_score(b0[2], mid, v, minsize, True)
    sa = side_score(b0[3], mid, v, minsize, False)
    comp = min(sb, sa) if min(sb, sa) > 0 else max(sb, sa) / 3
    for qq, s in ((max(minsize, 200), 1.0), (max(minsize, 1000), 1.0)):
        ours = ((v - s) / v) ** 2 * qq
        share = ours / (ours + comp)
        capital = qq * (1 - 2 * s / 100)
        rows.append({"market": mid_id, "q": qq, "rate": rate, "max_spread": v, "share": share,
                     "reward_per_day": rate * share, "capital": capital,
                     "yield_per_day": rate * share / capital, "question": q, "volume24h": r[cols.index("volume24hr")] or 0})
print(f"{len(rows)//2} reward markets with a usable book in the snapshot")
for qq_label, pick in (("small quotes (200 shares/side)", 0), ("bigger quotes (1000 shares/side)", 1)):
    sub = [x for k, x in enumerate(rows) if k % 2 == pick]
    y_ = np.array([x["yield_per_day"] for x in sub])
    d_ = np.array([x["reward_per_day"] for x in sub])
    print(f"\n{qq_label}: reward yield per $ per day median {100*np.median(y_):.3f}%, top decile {100*np.percentile(y_, 90):.2f}%")
    top = sorted(sub, key=lambda x: -x["yield_per_day"])[:12]
    for x in top:
        print(f"  {100*x['yield_per_day']:6.2f}%/day  ${x['reward_per_day']:7.2f}/day on ${x['capital']:6.0f}  pool ${x['rate']:6.0f}/day  share {x['share']:.2f}  24h vol ${x['volume24h']:,.0f} | {x['question'][:55]}")
    # a portfolio: the best 20 markets
    best = sorted(sub, key=lambda x: -x["yield_per_day"])[:20]
    cap = sum(x["capital"] for x in best); rew = sum(x["reward_per_day"] for x in best)
    print(f"  portfolio of best 20: ${rew:,.2f}/day on ${cap:,.0f} capital = {100*rew/cap:.2f}%/day before risk")
json.dump(rows, open("results/mm_rewards.json", "w"))
