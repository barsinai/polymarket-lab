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
        "umaResolutionStatus", "createdAt", "updatedAt", "feesEnabled", "gameStartTime")


def active_markets(min_volume):
    now = datetime.now(timezone.utc)
    got = collect.paginate_windows("markets", {"closed": "false", "active": "true",
                                               "volume_num_min": min_volume}, min_volume,
                                   "volumeNum", now - timedelta(days=120), now + timedelta(days=4 * 365))
    # plus markets ending within 4 days that haven't reached min_volume yet (e.g. soccer side
    # markets before kick-off: most of their volume comes near/during the game)
    got += collect.paginate_windows("markets", {"closed": "false", "active": "true", "volume_num_min": 500}, 500,
                                    "volumeNum", now, now + timedelta(days=4))
    out = {}
    for m in got:
        ev = (m.get("events") or [{}])[0]
        out[str(m["id"])] = {**{k: m.get(k) for k in KEEP}, "event_id": ev.get("id"),
                             "event_title": ev.get("title")}
    return list(out.values())


STATIC = ("id", "conditionId", "question", "slug", "startDate", "endDate", "outcomes", "clobTokenIds",
          "negRisk", "orderPriceMinTickSize", "orderMinSize", "rewardsMinSize", "rewardsMaxSpread",
          "createdAt", "event_id", "event_title", "feesEnabled", "gameStartTime")
DYNAMIC = [k for k in KEEP if k not in STATIC]  # stored hourly as compact rows


def parallel_books(tokens, workers=6):
    chunks = [tokens[i:i + 500] for i in range(0, len(tokens), 500)]
    got = {}
    with ThreadPoolExecutor(workers) as ex:
        for part in ex.map(books_for, chunks):
            got.update(part)
    return got


def open_interest(cids):
    """Open interest (money currently held in positions) per market; batch of condition ids,
    falling back to one request each if the batch form isn't accepted."""
    r = collect.get(f"{DATA_API}/oi", {"market": ",".join(cids)}, tries=3)
    if not isinstance(r, list) or (len(cids) > 1 and len(r) <= 1):
        r = []
        for c in cids:
            x = collect.get(f"{DATA_API}/oi", {"market": c}, tries=2)
            r += x if isinstance(x, list) else []
    return {str(x.get("market")): x.get("value") for x in r if isinstance(x, dict)}


def holders(cid):
    """Top holders per outcome, slimmed to [wallet, outcomeIndex, amount] (no names/profiles)."""
    r = collect.get(f"{DATA_API}/holders", {"market": cid, "limit": 20}, tries=3)
    rows = None
    if isinstance(r, list):
        rows = [[h.get("proxyWallet"), h.get("outcomeIndex"), round(float(h.get("amount") or 0), 2)]
                for tok in r for h in (tok.get("holders") or [])]
    return {"conditionId": cid, "holders": rows}


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
    raw = parallel_books(tokens)
    t2 = time.time()
    # compact: book key "<market id>:<outcome index>" -> [ts_ms, last, bids, asks, far_bid, far_ask]
    books = {}
    for m in mk:
        for j, t in enumerate(collect.as_list(m.get("clobTokenIds"))):
            if str(t) in raw:
                b = trim(raw[str(t)], a.band)
                books[f"{m['id']}:{j}"] = [b.get("timestamp"), b.get("last_trade_price"), b["bids"], b["asks"],
                                           b["far_bid_size"], b["far_ask_size"]]
    cids = [m["conditionId"] for m in mk if m.get("conditionId")]
    oi = {}
    with ThreadPoolExecutor(6) as ex:
        for part in ex.map(open_interest, [cids[i:i + 50] for i in range(0, len(cids), 50)]):
            oi.update(part)
    t3 = time.time()
    snap = {"ts": int(now.timestamp()), "open_interest": oi, "oi_seconds": round(t3 - t2, 1), "iso": now.isoformat(), "min_volume": a.min_volume,
            "band": a.band, "market_columns": DYNAMIC, "markets": {m["id"]: [m.get(k) for k in DYNAMIC] for m in mk},
            "book_columns": ["ts_ms", "last", "bids", "asks", "far_bid_size", "far_ask_size"], "books": books,
            "list_seconds": round(t1 - t0, 1), "book_seconds": round(t2 - t1, 1)}
    os.makedirs(f"data/live/{now:%Y-%m-%d}", exist_ok=True)
    path = f"data/live/{now:%Y-%m-%d}/{now:%H%M}.json.gz"
    with gzip.open(path, "wt") as f:
        json.dump(snap, f, separators=(",", ":"))
    print(f"{now.isoformat()}: {len(mk)} markets, {len(books)}/{len(tokens)} books, list {t1-t0:.0f}s, "
          f"books {t2-t1:.0f}s, open interest {len(oi)} ({t3-t2:.0f}s), saved {os.path.getsize(path)/1e6:.2f} MB", flush=True)

    try:  # paper trading never blocks the recording
        import paper
        n = paper.run(mk, raw, now.timestamp())
        resolved, signalled = paper.score()
        with open("data/paper/report.json", "w") as fh:  # running scoreboard
            json.dump({"updated": now.isoformat(), "resolved_markets": resolved, "signalled_markets": signalled,
                       "strategies": paper.report()}, fh, indent=1)
        print(f"paper: {n} signals this hour; {resolved}/{signalled} signalled markets resolved; "
              f"{json.dumps(paper.report())}", flush=True)
    except Exception as e:  # noqa: BLE001
        import traceback
        print(f"paper trading error: {e}\n{traceback.format_exc()[-1500:]}", flush=True)

    if a.holders:  # once a day: static market info (questions, token ids...) and top holders
        os.makedirs("data/live/meta", exist_ok=True)
        collect.write_jsonl_gz(f"data/live/meta/{now:%Y-%m-%d}.jsonl.gz", [{k: m.get(k) for k in STATIC} for m in mk])
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
