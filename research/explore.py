"""Broad exploratory analysis of the saved Polymarket data (offline).

Writes results/explore.json (chart data + stats) and prints headline numbers.
Every statistic that pools many markets reports an uncertainty that resamples whole
*events* (bootstrap), because markets in one event move together and treating them as
independent would overstate confidence.
"""

import gzip
import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone

import numpy as np

DATA, OUT = "data", "results"
RNG = np.random.default_rng(7)
H = 3600
DAY = 24 * H


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


CATS = [  # first match wins
    ("Sports", {"Sports", "Games", "Soccer", "NBA", "NFL (All)", "Esports", "Tennis", "Basketball"}),
    ("Crypto", {"Crypto", "Crypto Prices", "Bitcoin", "Ethereum"}),
    ("Geopolitics", {"Geopolitics", "World", "Iran", "Middle East", "Israel", "Ukraine", "Foreign Policy"}),
    ("Elections & politics", {"Politics", "Elections", "Global Elections", "US Election", "Trump",
                              "Trump Presidency", "U.S. Politics", "World Elections"}),
    ("Economy & business", {"Economy", "Finance", "Fed Rates", "Fed", "Business", "Tech", "Big Tech",
                            "Economic Policy", "AI", "Oil"}),
    ("Culture & social media", {"Culture", "Tweet Markets", "Elon Musk"}),
]


def category(tags):
    labels = {t.get("label") for t in tags or []}
    for name, keys in CATS:
        if labels & keys:
            return name
    return "Other"


def bootstrap(groups, stat, n=2000):
    """groups: list of per-event arrays/tuples; stat: fn(list_of_groups) -> float."""
    k = len(groups)
    if k < 5:
        return (float("nan"), float("nan"))
    vals = []
    for _ in range(n):
        idx = RNG.integers(0, k, k)
        vals.append(stat([groups[i] for i in idx]))
    return tuple(float(x) for x in np.nanpercentile(vals, [2.5, 97.5]))


# ---------------------------------------------------------------- load
events = {str(e["id"]): e for e in jl(f"{DATA}/events_closed.jsonl.gz")}
markets = {}
for m in jl(f"{DATA}/markets_closed.jsonl.gz"):
    prices, outs = as_list(m.get("outcomePrices")), as_list(m.get("outcomes"))
    if len(prices) != 2 or len(outs) != 2:
        continue
    try:
        p = [float(x) for x in prices]
    except ValueError:
        continue
    if max(p) < 0.99 or min(p) > 0.01:
        continue
    ev = (m.get("events") or [{}])[0]
    eid = str(ev.get("id") or m["id"])
    close = m.get("closedTime") or m.get("endDate")
    try:
        close_ts = datetime.fromisoformat(close.replace(" ", "T").replace("Z", "+00:00")
                                          .replace("+00", "+00:00") if close.endswith("+00") else
                                          close.replace("Z", "+00:00")).timestamp()
    except Exception:  # noqa: BLE001
        continue
    def ts(s):
        try:
            return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
        except Exception:  # noqa: BLE001
            return None
    markets[str(m["id"])] = {
        "won": 1 if p[0] > 0.5 else 0, "volume": float(m.get("volumeNum") or 0),
        "event": eid, "event_title": ev.get("title") or m.get("question"),
        "category": category(events.get(eid, {}).get("tags")),
        "question": m.get("question"), "outcome0": outs[0], "close_ts": close_ts,
        "end_ts": ts(m.get("endDate") or ""), "start_ts": ts(m.get("startDate") or ""),
        "year": datetime.fromtimestamp(close_ts, timezone.utc).year,
    }

hist = {}
for root, _, files in os.walk(f"{DATA}/prices"):
    for fn in files:
        if fn.endswith(".jsonl.gz"):
            for r in jl(os.path.join(root, fn)):
                mid = r["market_id"]
                if mid in markets and r["tokens"] and r["tokens"][0]["history"] and mid not in hist:
                    a = np.array(r["tokens"][0]["history"], dtype=float)
                    hist[mid] = (a[:, 0], a[:, 1])
ids = [i for i in markets if i in hist]
print(f"{len(ids)} resolved binary markets with price history")


def price_at(mid, t, max_gap=6 * H):
    ts_, ps = hist[mid]
    j = np.searchsorted(ts_, t, side="right") - 1
    if j < 0 or t - ts_[j] > max_gap:
        return None
    p = ps[j]
    return p if 0 < p < 1 else None


def side_obs(mid, hours):
    """Both sides of the market at `hours` before close: [(price, won), ...]."""
    m = markets[mid]
    p = price_at(mid, m["close_ts"] - hours * H)
    if p is None:
        return []
    return [(p, m["won"]), (1 - p, 1 - m["won"])]


R = {"generated": datetime.now(timezone.utc).isoformat()}

# ---------------------------------------------------------------- 1. overview
cat_n, cat_vol, year_n = Counter(), Counter(), Counter()
for i in ids:
    m = markets[i]
    cat_n[m["category"]] += 1; cat_vol[m["category"]] += m["volume"]; year_n[m["year"]] += 1
vols = np.array([markets[i]["volume"] for i in ids])
durations = np.array([(markets[i]["close_ts"] - markets[i]["start_ts"]) / DAY for i in ids
                      if markets[i]["start_ts"]])
R["overview"] = {
    "markets": len(ids), "events": len({markets[i]["event"] for i in ids}),
    "total_volume": float(vols.sum()), "median_volume": float(np.median(vols)),
    "min_volume": float(vols.min()),
    "price_points": int(sum(len(hist[i][0]) for i in ids)),
    "median_duration_days": float(np.median(durations)),
    "by_category": [{"category": c, "markets": n, "volume": cat_vol[c]} for c, n in cat_n.most_common()],
    "by_year": [{"year": y, "markets": year_n[y]} for y in sorted(year_n)],
}

# ---------------------------------------------------------------- 2. calibration
edges = [0, .05, .10, .20, .30, .40, .50, .60, .70, .80, .90, .95, 1.0001]
R["calibration"] = {}
for name, hrs in {"1 day": 24, "7 days": 168, "30 days": 720}.items():
    rows = []
    by_event = defaultdict(list)
    for i in ids:
        for p, w in side_obs(i, hrs):
            by_event[markets[i]["event"]].append((p, w))
    allobs = [x for g in by_event.values() for x in g]
    for lo, hi in zip(edges, edges[1:]):
        sel = [(p, w) for p, w in allobs if lo <= p < hi]
        if len(sel) < 10:
            continue
        groups = [[(p, w) for p, w in g if lo <= p < hi] for g in by_event.values()]
        groups = [g for g in groups if g]
        ci = bootstrap(groups, lambda gs: np.mean([w for g in gs for _, w in g]), 800)
        rows.append({"bucket": f"{lo*100:.0f}-{min(hi,1)*100:.0f}c", "n": len(sel),
                     "price": float(np.mean([p for p, _ in sel])),
                     "won": float(np.mean([w for _, w in sel])), "lo": ci[0], "hi": ci[1]})
    R["calibration"][name] = rows

# ---------------------------------------------------------------- 3. accuracy vs time to close
acc = []
for hrs in [1, 3, 6, 12, 24, 48, 72, 168, 336, 720, 1440]:
    b, fav, n = [], [], 0
    for i in ids:
        p = price_at(i, markets[i]["close_ts"] - hrs * H)
        if p is None:
            continue
        w = markets[i]["won"]
        b.append((p - w) ** 2)
        if abs(p - 0.5) > 1e-9:
            fav.append(1 if (p > 0.5) == (w == 1) else 0)
    if len(b) > 50:
        acc.append({"hours": hrs, "label": f"{hrs}h" if hrs < 48 else f"{hrs//24}d", "n": len(b),
                    "brier": float(np.mean(b)), "favorite_won": float(np.mean(fav)),
                    "skill_vs_coinflip": float(1 - np.mean(b) / 0.25)})
R["accuracy_by_horizon"] = acc

# ---------------------------------------------------------------- 4. underdog effect
def underdog_stats(subset, hrs=168, lo=0.05, hi=0.20):
    by_event = defaultdict(list)
    for i in subset:
        for p, w in side_obs(i, hrs):
            if lo <= p < hi:
                by_event[markets[i]["event"]].append((p, w))
    groups = list(by_event.values())
    obs = [x for g in groups for x in g]
    if len(obs) < 15:
        return None
    price, won = float(np.mean([p for p, _ in obs])), float(np.mean([w for _, w in obs]))
    roi = lambda gs: np.mean([(1 / p - 1) if w else -1 for g in gs for p, w in g])
    ci = bootstrap(groups, lambda gs: np.mean([w for g in gs for _, w in g]), 1500)
    rci = bootstrap(groups, roi, 1500)
    return {"bets": len(obs), "events": len(groups), "avg_price": price, "win_rate": won,
            "win_lo": ci[0], "win_hi": ci[1], "roi": float(roi(groups)), "roi_lo": rci[0], "roi_hi": rci[1]}

U = {"overall_7d": underdog_stats(ids)}
U["by_horizon"] = []
for lab, hrs in [("1d", 24), ("3d", 72), ("7d", 168), ("14d", 336), ("30d", 720)]:
    s = underdog_stats(ids, hrs)
    if s:
        U["by_horizon"].append({"horizon": lab, **s})
U["by_category"] = []
for c, _ in cat_n.most_common():
    s = underdog_stats([i for i in ids if markets[i]["category"] == c])
    if s:
        U["by_category"].append({"category": c, **s})
qs = np.quantile(vols, [1 / 3, 2 / 3])
tiers = [("lower third", lambda v: v < qs[0]), ("middle third", lambda v: qs[0] <= v < qs[1]),
         ("top third", lambda v: v >= qs[1])]
U["volume_cutoffs"] = [float(x) for x in qs]
U["by_volume"] = []
for lab, f in tiers:
    s = underdog_stats([i for i in ids if f(markets[i]["volume"])])
    if s:
        U["by_volume"].append({"tier": lab, **s})
U["by_year"] = []
for y in sorted(year_n):
    s = underdog_stats([i for i in ids if markets[i]["year"] == y])
    if s:
        U["by_year"].append({"year": y, **s})
U["by_price_band"] = []
for lo, hi in [(0.01, 0.05), (0.05, 0.10), (0.10, 0.20), (0.20, 0.30), (0.30, 0.40)]:
    s = underdog_stats(ids, 168, lo, hi)
    if s:
        U["by_price_band"].append({"band": f"{lo*100:.0f}-{hi*100:.0f}c", **s})
R["underdog"] = U

# ---------------------------------------------------------------- 5. momentum vs overreaction
# At daily checkpoints from 30d to 2d before close: past 24h move vs. (outcome - price).
bins = [-1, -0.15, -0.05, -0.02, 0.02, 0.05, 0.15, 1]
labels = ["fell >15c", "fell 5-15c", "fell 2-5c", "flat (±2c)", "rose 2-5c", "rose 5-15c", "rose >15c"]
mo = defaultdict(lambda: defaultdict(list))  # bin -> event -> [(future residual)]
for i in ids:
    m = markets[i]
    for d in range(2, 31):
        t = m["close_ts"] - d * DAY
        p_now, p_prev = price_at(i, t), price_at(i, t - DAY)
        if p_now is None or p_prev is None or not (0.03 < p_now < 0.97):
            continue
        # both sides: the No side moved by -delta and has residual -(won - p)
        for d_move, resid in ((p_now - p_prev, m["won"] - p_now), (p_prev - p_now, p_now - m["won"])):
            k = int(np.digitize(d_move, bins)) - 1
            mo[k][m["event"]].append(resid)
R["momentum"] = []
for k, lab in enumerate(labels):
    groups = list(mo[k].values())
    obs = [x for g in groups for x in g]
    if len(obs) < 30:
        continue
    ci = bootstrap(groups, lambda gs: np.mean([x for g in gs for x in g]), 800)
    R["momentum"].append({"move": lab, "n": len(obs), "events": len(groups),
                          "mispricing": float(np.mean(obs)), "lo": ci[0], "hi": ci[1]})

# ---------------------------------------------------------------- 6. favorites / late convergence
fav = []
for lab, hrs in [("6h", 6), ("1d", 24), ("3d", 72), ("7d", 168), ("14d", 336), ("30d", 720)]:
    by_event = defaultdict(list)
    for i in ids:
        for p, w in side_obs(i, hrs):
            if 0.90 <= p < 0.99:
                by_event[markets[i]["event"]].append((p, w))
    groups = list(by_event.values())
    obs = [x for g in groups for x in g]
    if len(obs) < 15:
        continue
    roi = lambda gs: np.mean([(1 / p - 1) if w else -1 for g in gs for p, w in g])
    r = float(roi(groups)); ci = bootstrap(groups, roi, 1500)
    fav.append({"horizon": lab, "days": hrs / 24, "bets": len(obs), "avg_price": float(np.mean([p for p, _ in obs])),
                "hit_rate": float(np.mean([w for _, w in obs])), "roi": r, "roi_lo": ci[0], "roi_hi": ci[1]})
R["favorites"] = fav

# "Yes" side bias: is the first-listed outcome (usually "Yes", the thing happening) mispriced?
def yes_bias(subset, hrs=168):
    by_event = defaultdict(list)
    for i in subset:
        p = price_at(i, markets[i]["close_ts"] - hrs * H)
        if p is not None and markets[i]["outcome0"] == "Yes":
            by_event[markets[i]["event"]].append(markets[i]["won"] - p)
    groups = list(by_event.values())
    obs = [x for g in groups for x in g]
    if len(obs) < 20:
        return None
    ci = bootstrap(groups, lambda gs: np.mean([x for g in gs for x in g]), 1500)
    return {"markets": len(obs), "events": len(groups), "yes_underpriced_by": float(np.mean(obs)),
            "lo": ci[0], "hi": ci[1]}

deadline = lambda q: (" by " in (q or "").lower()) or (" before " in (q or "").lower())
R["yes_bias"] = [{"group": "All Yes/No markets", **(yes_bias(ids) or {})},
                 {"group": "\"...by <date>?\" deadline questions",
                  **(yes_bias([i for i in ids if deadline(markets[i]["question"])]) or {})},
                 {"group": "Other Yes/No questions",
                  **(yes_bias([i for i in ids if not deadline(markets[i]["question"])]) or {})}]
for c, _ in cat_n.most_common():
    yb = yes_bias([i for i in ids if markets[i]["category"] == c])
    if yb:
        R["yes_bias"].append({"group": c, **yb})
R["underdog"]["deadline_vs_other"] = [
    {"group": "deadline questions", **(underdog_stats([i for i in ids if deadline(markets[i]["question"])]) or {})},
    {"group": "other questions", **(underdog_stats([i for i in ids if not deadline(markets[i]["question"])]) or {})}]

# biggest upsets: side priced >= 90c 7 days out that lost
ups = []
for i in ids:
    m = markets[i]
    p = price_at(i, m["close_ts"] - 7 * DAY)
    if p is None:
        continue
    for side_p, w, name in [(p, m["won"], m["outcome0"]), (1 - p, 1 - m["won"], "other side")]:
        if side_p >= 0.90 and not w:
            ups.append({"question": m["question"], "side": name, "price_7d": float(side_p),
                        "volume": m["volume"], "category": m["category"]})
R["upsets_7d"] = sorted(ups, key=lambda x: -x["price_7d"])[:12]
R["upsets_7d_count"] = len(ups)

# comebacks: winners that traded at or below 10c in the final 30 days
cb = Counter()
for i in ids:
    m = markets[i]
    ts_, ps = hist[i]
    sel = (ts_ >= m["close_ts"] - 30 * DAY) & (ts_ <= m["close_ts"] - 6 * H)
    if sel.sum() < 24:
        continue
    win_path = ps[sel] if m["won"] else 1 - ps[sel]
    cb["n"] += 1
    for thr in (0.10, 0.20, 0.30):
        if win_path.min() <= thr:
            cb[thr] += 1
R["comebacks"] = {"markets": cb["n"], **{f"winner_was_below_{int(t*100)}c": cb[t] / cb["n"]
                                         for t in (0.10, 0.20, 0.30)}}

# resolution lag: scheduled end -> actually closed
lag = np.array([(markets[i]["close_ts"] - markets[i]["end_ts"]) / H for i in ids if markets[i]["end_ts"]])
R["resolution_lag_hours"] = {"median": float(np.median(lag)), "p90": float(np.percentile(lag, 90)),
                             "closed_early_share": float(np.mean(lag < -1))}

# ---------------------------------------------------------------- 7. order books (live)
snaps = []
for root, _, files in os.walk(f"{DATA}/books"):
    for fn in sorted(files):
        if fn.endswith(".json.gz"):
            with gzip.open(os.path.join(root, fn), "rt") as f:
                snaps.append(json.load(f))
snaps.sort(key=lambda s: s["ts"])


def lv(levels):
    return [(float(x["price"]), float(x["size"])) if isinstance(x, dict) else (float(x[0]), float(x[1]))
            for x in levels or []]


def cost_to_buy(asks, dollars):
    """Average fill price for spending `dollars` walking the ask side; None if too thin."""
    spent, shares = 0.0, 0.0
    for p, s in sorted(asks):
        take = min(s * p, dollars - spent)
        spent += take; shares += take / p
        if spent >= dollars - 1e-9:
            return spent / shares
    return None


band_rows = defaultdict(lambda: defaultdict(list))
spreads = []
for s in snaps:
    for tok, bk in s["books"].items():
        bids, asks = lv(bk.get("bids")), lv(bk.get("asks"))
        if not bids or not asks:
            continue
        bb, ba = max(p for p, _ in bids), min(p for p, _ in asks)
        mid = (bb + ba) / 2
        if not (0.01 < mid < 0.99) or ba <= bb:
            continue
        spreads.append(ba - bb)
        band = next(lab for lab, lo, hi in [("1-5c", 0, .05), ("5-20c", .05, .20), ("20-40c", .20, .40),
                                            ("40-60c", .40, .60), ("60-80c", .60, .80), ("80-95c", .80, .95),
                                            ("95-99c", .95, 1.0)] if lo <= mid < hi)
        band_rows[band]["spread_pct"].append((ba - bb) / mid)
        for d in (100, 1000, 10000):
            c = cost_to_buy(asks, d)
            band_rows[band][f"cost_{d}"].append((c - mid) / mid if c else np.nan)
order = ["1-5c", "5-20c", "20-40c", "40-60c", "60-80c", "80-95c", "95-99c"]
R["books"] = {"snapshots": len(snaps), "first": snaps[0]["iso"] if snaps else None,
              "last": snaps[-1]["iso"] if snaps else None,
              "median_spread_c": float(np.median(spreads) * 100) if spreads else None,
              "by_band": [{"band": b, "books": len(band_rows[b]["spread_pct"]),
                           "spread_pct": float(np.median(band_rows[b]["spread_pct"])),
                           **{f"cost_{d}": float(np.nanmedian(band_rows[b][f"cost_{d}"]))
                              for d in (100, 1000, 10000)},
                           "fillable_10000": float(np.mean(~np.isnan(band_rows[b]["cost_10000"])))}
                          for b in order if band_rows[b]["spread_pct"]]}

# multi-outcome events in the latest snapshot: do "Yes" prices add up to 100%?
if snaps:
    act = {str(m["id"]): m for m in jl(f"{DATA}/markets_active.jsonl.gz")}
    last = snaps[-1]
    groups = defaultdict(list)
    for m in act.values():
        if m.get("negRisk") and m.get("events"):
            groups[str(m["events"][0]["id"])].append(m)
    sums = []
    for eid, ms in groups.items():
        if len(ms) < 3:
            continue
        asks = [float(m["bestAsk"]) for m in ms if m.get("bestAsk") not in (None, "")]
        bids = [float(m["bestBid"]) for m in ms if m.get("bestBid") not in (None, "")]
        if len(asks) != len(ms):
            continue
        sums.append({"event": ms[0]["events"][0].get("title"), "outcomes": len(ms),
                     "sum_best_ask": sum(asks), "sum_best_bid": sum(bids)})
    full = [x for x in sums if x["sum_best_bid"] >= 0.90]  # likely all outcomes present
    R["multi_outcome_complete"] = {"events": len(full),
                                   "ask_sum_below_100": sum(1 for x in full if x["sum_best_ask"] < 1),
                                   "bid_sum_above_100": sum(1 for x in full if x["sum_best_bid"] > 1),
                                   "rows": sorted(full, key=lambda x: x["sum_best_ask"])}
    R["multi_outcome"] = {"events_checked": len(sums),
                          "sum_ask_below_100": sum(1 for x in sums if x["sum_best_ask"] < 1),
                          "sum_bid_above_100": sum(1 for x in sums if x["sum_best_bid"] > 1),
                          "median_sum_ask": float(np.median([x["sum_best_ask"] for x in sums])) if sums else None,
                          "examples": sorted(sums, key=lambda x: x["sum_best_ask"])[:8],
                          "note": "only open markets in our top-2,000 snapshot; events with outcomes "
                                  "outside it are skipped, which can miss cheap long-tail outcomes"}

os.makedirs(OUT, exist_ok=True)
with open(f"{OUT}/explore.json", "w") as f:
    json.dump(R, f, indent=1, default=float)

print(json.dumps({k: R[k] for k in ("overview", "accuracy_by_horizon", "comebacks", "resolution_lag_hours")},
                 indent=1, default=float)[:3000])
print("UNDERDOG", json.dumps(U, indent=1, default=float)[:6000])
print("MOMENTUM", json.dumps(R["momentum"], indent=1))
print("FAV", json.dumps(R["favorites"], indent=1))
print("BOOKS", json.dumps(R["books"], indent=1))
print("MULTI", json.dumps(R.get("multi_outcome"), indent=1, default=float)[:2500])
print("YES", json.dumps(R["yes_bias"], indent=1))
print("DEADLINE", json.dumps(R["underdog"]["deadline_vs_other"], indent=1))
print("MULTI_FULL", json.dumps({k: v for k, v in R.get("multi_outcome_complete", {}).items() if k != "rows"}),
      [(x["outcomes"], round(x["sum_best_ask"], 3), round(x["sum_best_bid"], 3)) for x in R.get("multi_outcome_complete", {}).get("rows", [])[:12]])
print("UPSETS", R["upsets_7d_count"], json.dumps(R["upsets_7d"][:6], indent=1))
