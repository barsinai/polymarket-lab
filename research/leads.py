"""Focused re-test of the two leads on the wide (random-order) sample, offline.

Lead 1 - "Yes" / underdog sides of "...by <date>?" questions win more often than priced.
Lead 2 - overreaction: after a big 1-day move, price drifts back.

Each test is run two ways:
  * "close"     - times measured back from when the market actually closed (the original
                  test). Biased for deadline questions: a Yes that happens early closes the
                  market early, so "7 days before close" quietly depends on the outcome.
  * "scheduled" - times measured back from the market's *scheduled* end date, using only
                  markets still trading at that moment. This is what a real bettor could do.
Split by market size (lifetime volume). Uncertainty: bootstrap over whole events.
Prices are last-trade/mid: no spread or fees, so any edge here is an upper bound.

Writes results/leads.json.
"""

import gzip
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone

import numpy as np

DATA, OUT = "data", "results"
H, DAY = 3600, 86400
RNG = np.random.default_rng(11)
TIERS = [("$5k-20k", 5e3, 2e4), ("$20k-100k", 2e4, 1e5), ("$100k-1M", 1e5, 1e6), ("over $1M", 1e6, 1e18)]


def jl(path):
    with gzip.open(path, "rt") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def as_list(v):
    if isinstance(v, list):
        return v
    try:
        return json.loads(v) if isinstance(v, str) else []
    except json.JSONDecodeError:
        return []


def ts(s):
    if not s:
        return None
    s = s.replace(" ", "T").replace("Z", "+00:00")
    if s.endswith("+00"):
        s += ":00"
    try:
        return datetime.fromisoformat(s).timestamp()
    except ValueError:
        return None


markets = {}
paths = sorted(os.path.join(f"{DATA}/listing", f) for f in os.listdir(f"{DATA}/listing") if f.endswith(".jsonl.gz"))
for path in paths + [f"{DATA}/markets_closed.jsonl.gz"]:
    if not os.path.exists(path):
        continue
    for m in jl(path):
        mid = str(m.get("id"))
        if mid in markets:
            continue
        prices, outs = as_list(m.get("outcomePrices")), as_list(m.get("outcomes"))
        if len(prices) != 2 or len(outs) != 2:
            continue
        try:
            p = [float(x) for x in prices]
        except ValueError:
            continue
        if max(p) < 0.99 or min(p) > 0.01:
            continue
        close, end = ts(m.get("closedTime") or m.get("endDate")), ts(m.get("endDate"))
        if close is None:
            continue
        q = (m.get("question") or "").lower()
        ev = (m.get("events") or [{}])[0]
        markets[mid] = {"won": 1 if p[0] > 0.5 else 0, "vol": float(m.get("volumeNum") or 0),
                        "event": str(ev.get("id") or mid), "yes": outs[0] == "Yes",
                        "deadline": " by " in q or " before " in q, "close": close, "end": end}

hist = {}
# --random-only: skip the first run's files (the top-2,100 by final volume, which over-represent
# surprises); keep only the random-order collection in data/prices/parts.
PRICE_DIR = f"{DATA}/prices/parts" if "--random-only" in sys.argv else f"{DATA}/prices"
for root, _, files in os.walk(PRICE_DIR):
    for fn in files:
        if fn.endswith(".jsonl.gz"):
            for r in jl(os.path.join(root, fn)):
                mid = r["market_id"]
                if mid in markets and mid not in hist and r["tokens"] and r["tokens"][0]["history"]:
                    a = np.array(r["tokens"][0]["history"], dtype=float)
                    hist[mid] = (a[:, 0], a[:, 1])
ids = [i for i in markets if i in hist]
print(f"{len(markets)} resolved binary markets listed, {len(ids)} with price history", flush=True)


def price_at(mid, t, max_gap=6 * H):
    t_, p_ = hist[mid]
    j = np.searchsorted(t_, t, side="right") - 1
    if j < 0 or t - t_[j] > max_gap:
        return None
    p = p_[j]
    return p if 0 < p < 1 else None


def anchor(mid, mode):
    m = markets[mid]
    return m["close"] if mode == "close" else m["end"]


def open_at(mid, t):
    return t < markets[mid]["close"] - H


def summarize(by_event, kind):
    """by_event: event -> list of values. kind 'resid' (won - price) or 'roi' via (p, w)."""
    groups = [g for g in by_event.values() if g]
    if len(groups) < 10:
        return None
    if kind == "bet":
        vals = [[(1 / p - 1) if w else -1.0 for p, w in g] for g in groups]
        wins = [[w for _, w in g] for g in groups]
        price = float(np.mean([p for g in groups for p, _ in g]))
    else:
        vals = groups
    s = np.array([sum(v) for v in vals]); n = np.array([len(v) for v in vals])
    idx = RNG.integers(0, len(s), (1000, len(s)))
    boot = s[idx].sum(1) / n[idx].sum(1)
    out = {"n": int(n.sum()), "events": len(groups), "mean": float(s.sum() / n.sum()),
           "lo": float(np.percentile(boot, 2.5)), "hi": float(np.percentile(boot, 97.5))}
    if kind == "bet":
        out["avg_price"] = price
        out["win_rate"] = float(sum(map(sum, wins)) / n.sum())
    return out


def lead1(subset, mode, hrs=168, lo=0.05, hi=0.20):
    """Bet the cheap side (5-20c) of each market `hrs` before close/end; hold to the end."""
    be = defaultdict(list)
    for i in subset:
        a = anchor(i, mode)
        if a is None:
            continue
        t = a - hrs * H
        if mode == "scheduled" and not open_at(i, t):
            continue
        p = price_at(i, t)
        if p is None:
            continue
        w = markets[i]["won"]
        for sp, sw in ((p, w), (1 - p, 1 - w)):
            if lo <= sp < hi:
                be[markets[i]["event"]].append((sp, sw))
    return summarize(be, "bet")


def yes_gap(subset, mode, hrs=168):
    """Average (did Yes win) - (Yes price): positive = Yes was too cheap."""
    be = defaultdict(list)
    for i in subset:
        if not markets[i]["yes"]:
            continue
        a = anchor(i, mode)
        if a is None:
            continue
        t = a - hrs * H
        if mode == "scheduled" and not open_at(i, t):
            continue
        p = price_at(i, t)
        if p is not None:
            be[markets[i]["event"]].append(markets[i]["won"] - p)
    return summarize(be, "resid")


def lead2(subset, mode, thr=0.15):
    """After a 1-day move of more than `thr`, how far does price end up from the outcome?
    Positive 'mean' = the side that just jumped was still too cheap (momentum);
    negative = it had overshot (overreaction)."""
    up = defaultdict(list)
    for i in subset:
        a = anchor(i, mode)
        if a is None:
            continue
        m = markets[i]
        for d in range(2, 31):
            t = a - d * DAY
            if mode == "scheduled" and not open_at(i, t):
                continue
            pn, pp = price_at(i, t), price_at(i, t - DAY)
            if pn is None or pp is None or not (0.03 < pn < 0.97):
                continue
            if pn - pp > thr:      # Yes side jumped
                up[m["event"]].append(m["won"] - pn)
            elif pp - pn > thr:    # No side jumped
                up[m["event"]].append(pn - m["won"])
    return summarize(up, "resid")


R = {"generated": datetime.now(timezone.utc).isoformat(), "markets_with_history": len(ids),
     "random_only": "--random-only" in sys.argv,
     "markets_listed": len(markets)}
groups = {"all": ids,
          "deadline": [i for i in ids if markets[i]["deadline"]],
          "other": [i for i in ids if not markets[i]["deadline"]]}
for lab, lo, hi in TIERS:
    groups[f"all {lab}"] = [i for i in ids if lo <= markets[i]["vol"] < hi]
    groups[f"deadline {lab}"] = [i for i in groups["deadline"] if lo <= markets[i]["vol"] < hi]
for name, f in [("lead1_underdog_7d", lead1), ("yes_gap_7d", yes_gap), ("lead2_after_big_move", lead2)]:
    R[name] = {}
    for g, sub in groups.items():
        R[name][g] = {mode: f(sub, mode) for mode in ("close", "scheduled")}
        print(name, g, json.dumps(R[name][g]), flush=True)
os.makedirs(OUT, exist_ok=True)
with open(f"{OUT}/leads{'_random' if '--random-only' in sys.argv else ''}.json", "w") as fh:
    json.dump(R, fh, indent=1)
