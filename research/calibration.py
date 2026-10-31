"""Phase 1: are Polymarket prices well calibrated?

Pulls resolved binary markets from the public Gamma API, fetches each market's
price history from the CLOB API, and asks: when the "Yes" side traded at price p
some time before the market closed, how often did "Yes" actually win?

Also scores two naive hold-to-resolution strategies (buy longshots, buy heavy
favorites) at several horizons, as a first hint of where an edge might be.

Caveat: price history is last-trade/mid, not what you could actually have filled
at. Spreads and fees are NOT modeled here; Phase 3's simulator handles that.

Usage: python research/calibration.py --max-markets 3000 --min-volume 10000
"""

import argparse
import json
import math
import os
import sys
import time
from datetime import datetime, timezone

import requests

GAMMA = "https://gamma-api.polymarket.com"
CLOB = "https://clob.polymarket.com"
HORIZONS_H = {"1h": 1, "1d": 24, "7d": 24 * 7, "30d": 24 * 30}
BUCKETS = [0.0, 0.05, 0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90, 0.95, 1.0001]

S = requests.Session()
S.headers["User-Agent"] = "polymarket-lab-research/0.1"


def get(url, params=None, tries=4):
    for i in range(tries):
        try:
            r = S.get(url, params=params, timeout=30)
            if r.status_code == 429:
                time.sleep(2 ** i)
                continue
            r.raise_for_status()
            return r.json()
        except Exception as e:  # noqa: BLE001
            if i == tries - 1:
                print(f"  ! {url} {params} failed: {e}", file=sys.stderr)
                return None
            time.sleep(1 + i)
    return None


def as_list(v):
    if isinstance(v, list):
        return v
    if isinstance(v, str):
        try:
            return json.loads(v)
        except json.JSONDecodeError:
            return []
    return []


def parse_ts(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def fetch_markets(max_markets, min_volume):
    out, offset, page = [], 0, 500
    while len(out) < max_markets:
        batch = get(f"{GAMMA}/markets", {
            "closed": "true", "limit": page, "offset": offset,
            "order": "volumeNum", "ascending": "false",
        })
        if not batch:
            break
        for m in batch:
            outcomes = as_list(m.get("outcomes"))
            prices = as_list(m.get("outcomePrices"))
            tokens = as_list(m.get("clobTokenIds"))
            vol = float(m.get("volumeNum") or m.get("volume") or 0)
            if len(outcomes) != 2 or len(prices) != 2 or len(tokens) != 2:
                continue
            if vol < min_volume:
                continue
            try:
                p = [float(x) for x in prices]
            except ValueError:
                continue
            # keep only cleanly resolved markets (one side settled at ~1)
            if max(p) < 0.99 or min(p) > 0.01:
                continue
            close = parse_ts(m.get("closedTime")) or parse_ts(m.get("endDate"))
            if not close:
                continue
            out.append({
                "id": m.get("id"), "question": m.get("question"),
                "slug": m.get("slug"), "volume": vol, "close_ts": close,
                "token0": tokens[0], "outcome0": outcomes[0],
                "won0": 1 if p[0] > 0.5 else 0,
                "category": m.get("category") or "",
            })
        print(f"scanned offset={offset}, kept {len(out)}")
        offset += page
        if len(batch) < page:
            break
    return out[:max_markets]


def price_history(token, close_ts):
    start = int(close_ts - 35 * 86400)
    data = get(f"{CLOB}/prices-history", {
        "market": token, "startTs": start, "endTs": int(close_ts), "fidelity": 60,
    })
    hist = (data or {}).get("history") or []
    if not hist:
        data = get(f"{CLOB}/prices-history", {"market": token, "interval": "max", "fidelity": 60})
        hist = (data or {}).get("history") or []
    return sorted((int(h["t"]), float(h["p"])) for h in hist if "t" in h and "p" in h)


def price_at(hist, ts, max_gap=6 * 3600):
    """Last observed price at or before ts, if it's recent enough."""
    best = None
    for t, p in hist:
        if t <= ts:
            best = (t, p)
        else:
            break
    if best and ts - best[0] <= max_gap:
        return best[1]
    return None


def bucket_of(p):
    for lo, hi in zip(BUCKETS, BUCKETS[1:]):
        if lo <= p < hi:
            return f"{lo:.2f}-{min(hi, 1):.2f}"
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-markets", type=int, default=3000)
    ap.add_argument("--min-volume", type=float, default=10000)
    ap.add_argument("--out", default="results")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    markets = fetch_markets(a.max_markets, a.min_volume)
    print(f"{len(markets)} resolved binary markets selected")

    obs = []  # (horizon, price_yes, won_yes, market_id)
    for i, m in enumerate(markets):
        hist = price_history(m["token0"], m["close_ts"])
        if i % 100 == 0:
            print(f"history {i}/{len(markets)} (points={len(hist)})")
        for name, h in HORIZONS_H.items():
            p = price_at(hist, m["close_ts"] - h * 3600)
            if p is None or not (0 < p < 1):
                continue
            # Record both sides so the curve is symmetric and uses all info.
            obs.append((name, p, m["won0"], m["id"]))
            obs.append((name, 1 - p, 1 - m["won0"], m["id"]))
        time.sleep(0.05)

    # Calibration table
    calib = {}
    for name in HORIZONS_H:
        rows = {}
        for hz, p, w, _ in obs:
            if hz != name:
                continue
            b = bucket_of(p)
            r = rows.setdefault(b, {"n": 0, "sum_p": 0.0, "wins": 0})
            r["n"] += 1; r["sum_p"] += p; r["wins"] += w
        table = []
        for b in sorted(rows):
            r = rows[b]
            avg_p, rate = r["sum_p"] / r["n"], r["wins"] / r["n"]
            se = math.sqrt(max(rate * (1 - rate), 1e-9) / r["n"])
            table.append({"bucket": b, "n": r["n"], "avg_price": round(avg_p, 4),
                          "win_rate": round(rate, 4), "edge": round(rate - avg_p, 4),
                          "se": round(se, 4)})
        calib[name] = table

    # Naive strategies: $1 stake per market, hold to resolution, no costs.
    strategies = {"longshot (<10c)": (0.0, 0.10), "favorite (90-98c)": (0.90, 0.98),
                  "near-certain (95-99c)": (0.95, 0.99)}
    strat = {}
    for sname, (lo, hi) in strategies.items():
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

    result = {"generated": datetime.now(timezone.utc).isoformat(),
              "markets": len(markets), "observations": len(obs) // 2,
              "calibration": calib, "strategies": strat}
    with open(f"{a.out}/calibration.json", "w") as f:
        json.dump(result, f, indent=2)
    with open(f"{a.out}/markets.json", "w") as f:
        json.dump(markets, f)
    print(json.dumps(result["strategies"], indent=2))


if __name__ == "__main__":
    main()
