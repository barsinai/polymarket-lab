"""Phase 2b: wide live recording - things that can't be downloaded after the fact.

Every run (hourly):
  data/live/YYYY-MM-DD/HHMM.json.gz
    "markets": Gamma stats for EVERY open market above --min-volume (volume so far,
               24h/1w volume, liquidity, best bid/ask, spread, recent price changes...),
               so "how big was the market at the moment of the bet" is known going forward.
    "books":   order book of every outcome token of those markets, levels within
               --band of the best price (what a small trader can actually trade), with
               the size further out summarized.
With --holders (once a day):
  data/live/holders/YYYY-MM-DD.jsonl.gz  top holders of each market (only ever available
               as "right now"), for "what are the big / successful wallets doing" features.

Complements record_books.py (busiest ~450 markets, every 15 min, wider price band).
"""

import argparse
import gzip
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import collect  # noqa: E402  (pagination helpers)
from record_books import books_for, trim  # noqa: E402

DATA_API = "https://data-api.polymarket.com"
KEEP = ("id", "conditionId", "question", "slug", "startDate", "endDate", "outcomes", "outcomePrices",
        "clobTokenIds", "bestBid", "bestAsk", "spread", "lastTradePrice", "volumeNum", "volume24hr",
        "volume1wk", "volume1mo", "liquidityNum", "oneHourPriceChange", "oneDayPriceChange",
        "oneWeekPriceChange", "oneMonthPriceChange", "competitive", "negRisk", "acceptingOrders",
        "orderPriceMinTickSize", "orderMinSize", "rewardsMinSize", "rewardsMaxSpread",
        "umaResolutionStatus", "createdAt", "updatedAt")


def active_markets(min_volume):
    now = datetime.now(timezone.utc)
    got = collect.paginate_windows("markets", {"closed": "false", "active": "true",
                                               "volume_num_min": min_volume}, min_volume,
                                   "volumeNum", now - timedelta(days=120), now + timedelta(days=4 * 365))
    out = {}
    for m in got:
        ev = (m.get("events") or [{}])[0]
        out[str(m["id"])] = {**{k: m.get(k) for k in KEEP}, "event_id": ev.get("id"),
                             "event_title": ev.get("title")}
    return list(out.values())


def parallel_books(tokens, workers=6):
    chunks = [tokens[i:i + 500] for i in range(0, len(tokens), 500)]
    got = {}
    with ThreadPoolExecutor(workers) as ex:
        for part in ex.map(books_for, chunks):
            got.update(part)
    return got


def holders(cid):
    r = collect.get(f"{DATA_API}/holders", {"market": cid, "limit": 20}, tries=3)
    return {"conditionId": cid, "holders": r}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-volume", type=float, default=5000)
    ap.add_argument("--band", type=float, default=0.05)
    ap.add_argument("--holders", action="store_true")
    a = ap.parse_args()
    now = datetime.now(timezone.utc)
    t0 = time.time()

    mk = active_markets(a.min_volume)
    tokens = [str(t) for m in mk if m.get("acceptingOrders", True) for t in collect.as_list(m.get("clobTokenIds"))]
    t1 = time.time()
    books = {k: trim(v, a.band) for k, v in parallel_books(tokens).items()}
    t2 = time.time()
    snap = {"ts": int(now.timestamp()), "iso": now.isoformat(), "min_volume": a.min_volume,
            "band": a.band, "markets": mk, "books": books,
            "list_seconds": round(t1 - t0, 1), "book_seconds": round(t2 - t1, 1)}
    os.makedirs(f"data/live/{now:%Y-%m-%d}", exist_ok=True)
    path = f"data/live/{now:%Y-%m-%d}/{now:%H%M}.json.gz"
    with gzip.open(path, "wt") as f:
        json.dump(snap, f, separators=(",", ":"))
    print(f"{now.isoformat()}: {len(mk)} markets, {len(books)}/{len(tokens)} books, list {t1-t0:.0f}s, "
          f"books {t2-t1:.0f}s, saved {os.path.getsize(path)/1e6:.2f} MB", flush=True)

    if a.holders:
        cids = [m["conditionId"] for m in mk if m.get("conditionId")]
        os.makedirs("data/live/holders", exist_ok=True)
        hp = f"data/live/holders/{now:%Y-%m-%d}.jsonl.gz"
        with ThreadPoolExecutor(8) as ex:
            rows = list(ex.map(holders, cids))
        ok = sum(1 for r in rows if r["holders"])
        collect.write_jsonl_gz(hp, [{"ts": int(now.timestamp()), **r} for r in rows])
        print(f"holders: {ok}/{len(cids)} markets, {time.time()-t2:.0f}s, "
              f"saved {os.path.getsize(hp)/1e6:.2f} MB", flush=True)

    if len(books) < 0.5 * max(len(tokens), 1):
        sys.exit("fewer than half the books fetched")


if __name__ == "__main__":
    main()
