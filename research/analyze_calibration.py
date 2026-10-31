"""Phase 1 analysis (offline): are Polymarket prices well calibrated?

Reads only the saved files in data/ (see collect.py); never touches the network.

Question: when one side of a resolved binary market traded at price p some time
before close, how often did it actually win? Also scores naive hold-to-resolution
strategies. Price history is last-trade/mid, so spreads and fees are NOT modeled;
treat any "edge" here as an upper bound.

Usage: python research/analyze_calibration.py [--min-volume 10000]
"""

import argparse
import gzip
import json
import math
import os
from datetime import datetime, timezone

DATA = "data"
HORIZONS_H = {"1h": 1, "1d": 24, "7d": 24 * 7, "30d": 24 * 30}
BUCKETS = [0.0, 0.02, 0.05, 0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90, 0.95, 0.98, 1.0001]
STRATEGIES = {"longshot (<10c)": (0.0, 0.10), "favorite (90-98c)": (0.90, 0.98),
              "near-certain (95-99c)": (0.95, 0.99)}


def read_jsonl_gz(path):
    with gzip.open(path, "rt") as f:
        return [json.loads(line) for line in f if line.strip()]


def all_closed_markets():
    """Closed markets from data/listing/ (full listing) plus the first run's file, deduped."""
    seen = set()
    paths = [os.path.join(f"{DATA}/listing", f) for f in sorted(os.listdir(f"{DATA}/listing"))
             if f.endswith(".jsonl.gz")] if os.path.isdir(f"{DATA}/listing") else []
    paths.append(f"{DATA}/markets_closed.jsonl.gz")
    for path in paths:
        if os.path.exists(path):
            for m in read_jsonl_gz(path):
                if str(m.get("id")) not in seen:
                    seen.add(str(m.get("id")))
                    yield m


def as_list(v):
    if isinstance(v, list):
        return v
    try:
        return json.loads(v) if isinstance(v, str) else []
    except json.JSONDecodeError:
        return []


def price_at(hist, ts, max_gap=6 * 3600):
    best = None
    for t, p in hist:
        if t <= ts:
            best = (t, p)
        else:
            break
    return best[1] if best and ts - best[0] <= max_gap else None


def bucket_of(p):
    for lo, hi in zip(BUCKETS, BUCKETS[1:]):
        if lo <= p < hi:
            return f"{lo:.2f}-{min(hi, 1):.2f}"
    return None


def load(min_volume):
    meta = {}
    for m in all_closed_markets():
        prices, outcomes = as_list(m.get("outcomePrices")), as_list(m.get("outcomes"))
        if len(prices) != 2 or len(outcomes) != 2:
            continue
        try:
            p = [float(x) for x in prices]
        except ValueError:
            continue
        if max(p) < 0.99 or min(p) > 0.01:  # not cleanly resolved
            continue
        if float(m.get("volumeNum") or 0) < min_volume:
            continue
        meta[str(m["id"])] = {"won": [1 if x > 0.5 else 0 for x in p],
                              "category": m.get("category") or "", "question": m.get("question")}
    rows = []
    for root, _, files in os.walk(f"{DATA}/prices"):
        for fn in sorted(files):
            if fn.endswith(".jsonl.gz"):
                with gzip.open(os.path.join(root, fn), "rt") as f:
                    for line in f:
                        r = json.loads(line)
                        if r["market_id"] in meta and r["tokens"]:
                            # only the first token is needed; drop the rest to save memory
                            r["tokens"] = r["tokens"][:1]
                            rows.append(r)
    seen = set()
    rows = [r for r in rows if not (r["market_id"] in seen or seen.add(r["market_id"]))]
    return meta, rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-volume", type=float, default=10000)
    ap.add_argument("--out", default="results")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    meta, rows = load(a.min_volume)

    obs = []  # (horizon, price, won, market_id)
    for r in rows:
        tok = r["tokens"][0]
        if not tok["history"]:
            continue
        won0 = meta[r["market_id"]]["won"][0]
        for name, h in HORIZONS_H.items():
            p = price_at(tok["history"], r["close_ts"] - h * 3600)
            if p is None or not (0 < p < 1):
                continue
            obs += [(name, p, won0, r["market_id"]), (name, 1 - p, 1 - won0, r["market_id"])]

    calib = {}
    for name in HORIZONS_H:
        acc = {}
        for hz, p, w, _ in obs:
            if hz == name:
                b = acc.setdefault(bucket_of(p), [0, 0.0, 0])
                b[0] += 1; b[1] += p; b[2] += w
        calib[name] = []
        for k in sorted(acc):
            n, sp, wins = acc[k]
            rate = wins / n
            calib[name].append({"bucket": k, "n": n, "avg_price": round(sp / n, 4),
                                "win_rate": round(rate, 4), "edge": round(rate - sp / n, 4),
                                "se": round(math.sqrt(max(rate * (1 - rate), 1e-9) / n), 4)})

    strat = {}
    for sname, (lo, hi) in STRATEGIES.items():
        for name in HORIZONS_H:
            picks = [(p, w) for hz, p, w, _ in obs if hz == name and lo <= p < hi]
            if not picks:
                continue
            rets = [((1 - p) / p) if w else -1.0 for p, w in picks]
            mean = sum(rets) / len(rets)
            sd = math.sqrt(sum((x - mean) ** 2 for x in rets) / max(len(rets) - 1, 1))
            strat.setdefault(sname, {})[name] = {
                "bets": len(rets), "avg_return_per_$": round(mean, 4),
                "se": round(sd / math.sqrt(len(rets)), 4),
                "hit_rate": round(sum(w for _, w in picks) / len(picks), 4)}

    res = {"generated": datetime.now(timezone.utc).isoformat(), "min_volume": a.min_volume,
           "markets_with_history": sum(1 for r in rows if r["tokens"][0]["history"]),
           "markets_eligible": len(meta), "calibration": calib, "strategies": strat}
    with open(f"{a.out}/calibration.json", "w") as f:
        json.dump(res, f, indent=2)
    print(json.dumps({k: v for k, v in res.items() if k != "calibration"}, indent=2))


if __name__ == "__main__":
    main()
