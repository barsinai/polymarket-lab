"""Phase 2: record live order book snapshots, going forward.

Each run picks the markets worth watching (highest 24h volume, plus liquid markets
closing within 3 days, which is where late-convergence strategies trade) and saves
the full order book of every outcome token (all levels, both sides), plus the
Gamma summary fields (best bid/ask, last price, volume) at that moment.

Output: data/books/YYYY-MM-DD/HHMM.json.gz, one file per snapshot (separate files keep
git history small: nothing already committed is ever rewritten).
"""

import argparse
import gzip
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone

import requests

GAMMA = "https://gamma-api.polymarket.com"
CLOB = "https://clob.polymarket.com"
S = requests.Session()
S.headers["User-Agent"] = "polymarket-lab-recorder/0.1"


def req(method, url, **kw):
    for i in range(4):
        try:
            r = S.request(method, url, timeout=30, **kw)
            if r.status_code == 429 or r.status_code >= 500:
                time.sleep(2 ** i); continue
            if r.status_code >= 400:
                print(f"  ! {r.status_code} {url}: {r.text[:200]}", flush=True)
                return None
            return r.json()
        except Exception as e:  # noqa: BLE001
            print(f"  ! {url}: {e}", flush=True); time.sleep(1 + i)
    return None


def as_list(v):
    if isinstance(v, list):
        return v
    try:
        return json.loads(v) if isinstance(v, str) else []
    except json.JSONDecodeError:
        return []


def active_markets(params, cap):
    out, offset = [], 0
    while len(out) < cap:
        b = req("GET", f"{GAMMA}/markets", params={**params, "limit": 100, "offset": offset})
        if not b:
            break
        out += b
        offset += 100
        if len(b) < 100:
            break
    return out[:cap]


def trim(bk, band=0.20):
    """Keep levels within `band` of the best price on each side (that's all a small
    trader can realistically trade against); summarize the rest so nothing is silently lost."""
    bids = [(float(x["price"]), float(x["size"])) for x in bk.get("bids") or []]
    asks = [(float(x["price"]), float(x["size"])) for x in bk.get("asks") or []]
    bb = max((p for p, _ in bids), default=None)
    ba = min((p for p, _ in asks), default=None)
    kb = sorted([l for l in bids if bb is not None and l[0] >= bb - band - 1e-9], reverse=True)
    ka = sorted([l for l in asks if ba is not None and l[0] <= ba + band + 1e-9])
    out = {k: bk.get(k) for k in ("market", "asset_id", "timestamp", "hash", "min_order_size",
                                  "tick_size", "neg_risk", "last_trade_price")}
    out["bids"], out["asks"] = kb, ka  # [[price, size], ...], best first
    out["far_bid_size"] = round(sum(s for _, s in bids) - sum(s for _, s in kb), 2)
    out["far_ask_size"] = round(sum(s for _, s in asks) - sum(s for _, s in ka), 2)
    return out


def books_for(tokens):
    """Batch endpoint first; fall back to one request per token."""
    got = {}
    for i in range(0, len(tokens), 50):
        chunk = tokens[i:i + 50]
        res = req("POST", f"{CLOB}/books", json=[{"token_id": t} for t in chunk])
        if isinstance(res, list):
            for bk in res:
                got[str(bk.get("asset_id"))] = bk
        else:
            for t in chunk:
                bk = req("GET", f"{CLOB}/book", params={"token_id": t})
                if bk:
                    got[t] = bk
                time.sleep(0.05)
    return got


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=300)
    ap.add_argument("--closing", type=int, default=150)
    a = ap.parse_args()
    now = datetime.now(timezone.utc)

    base = {"closed": "false", "active": "true"}
    top = active_markets({**base, "order": "volume24hr", "ascending": "false"}, a.top)
    soon = active_markets({**base, "order": "endDate", "ascending": "true",
                           "end_date_min": now.isoformat(),
                           "end_date_max": (now + timedelta(days=3)).isoformat(),
                           "volume_num_min": 10000}, a.closing)
    markets = {str(m["id"]): m for m in top + soon if m.get("enableOrderBook", True)}

    keep = ("id", "conditionId", "question", "slug", "endDate", "outcomes", "outcomePrices",
            "clobTokenIds", "bestBid", "bestAsk", "spread", "lastTradePrice", "volume24hr",
            "volumeNum", "liquidityNum", "negRisk", "orderPriceMinTickSize", "orderMinSize")
    summary, tokens = [], []
    for m in markets.values():
        summary.append({k: m.get(k) for k in keep})
        tokens += [str(t) for t in as_list(m.get("clobTokenIds"))]

    t0 = time.time()
    books = {k: trim(v) for k, v in books_for(tokens).items()}
    snap = {"ts": int(now.timestamp()), "iso": now.isoformat(), "markets": summary,
            "books": books, "fetch_seconds": round(time.time() - t0, 1)}

    os.makedirs(f"data/books/{now:%Y-%m-%d}", exist_ok=True)
    path = f"data/books/{now:%Y-%m-%d}/{now:%H%M}.json.gz"
    with gzip.open(path, "wt") as f:
        json.dump(snap, f, separators=(",", ":"))
    print(f"{now.isoformat()}: {len(markets)} markets, {len(books)}/{len(tokens)} books, "
          f"{snap['fetch_seconds']}s, saved {os.path.getsize(path)/1e6:.2f} MB")
    if len(books) < 0.5 * max(len(tokens), 1):
        sys.exit("fewer than half the books fetched")


if __name__ == "__main__":
    main()
