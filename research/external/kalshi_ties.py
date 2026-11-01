"""For every settled Kalshi soccer 'Tie is the result' market: hourly price history over the
3 days before kick-off (public candlesticks endpoint), plus the team names of that game
(from the sibling 'X wins' markets of the same event).
Saves data/external/kalshi/ties.jsonl.gz: {ticker, event, series, kickoff, result, teams,
candles: [[ts, yes_bid_close, yes_ask_close, price_close, volume], ...]}. Incremental."""
import gzip, json, os, time
from collections import defaultdict
from datetime import datetime
import requests

BASE = "https://api.elections.kalshi.com/trade-api/v2"
S = requests.Session(); S.headers["User-Agent"] = "polymarket-lab-research/0.1"
OUT = "data/external/kalshi/ties.jsonl.gz"
BUDGET_S = float(os.environ.get("BUDGET_MIN", "200")) * 60
t0 = time.time()

teams, ties = defaultdict(list), []
for l in gzip.open("data/external/kalshi/markets.jsonl.gz", "rt"):
    m = json.loads(l)
    ev = m.get("event_ticker") or ""
    if "GAME" not in ev.split("-")[0]:
        continue
    if m.get("yes_sub_title") == "Tie":
        if m.get("status") in ("finalized", "settled") and m.get("result") in ("yes", "no") and m.get("occurrence_datetime"):
            ties.append(m)
    elif m.get("yes_sub_title"):
        teams[ev].append(m["yes_sub_title"])
done = set()
old = []
if os.path.exists(OUT):
    for l in gzip.open(OUT, "rt"):
        r = json.loads(l); done.add(r["ticker"]); old.append(r)
print(f"{len(ties)} settled tie markets, {len(done)} already fetched", flush=True)


def get(url, params):
    for k in range(5):
        try:
            r = S.get(url, params=params, timeout=30)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 429:
                time.sleep(2 ** k); continue
            return None
        except requests.RequestException:
            time.sleep(1 + k)
    return None


new = []
for n, m in enumerate(ties):
    if m["ticker"] in done:
        continue
    if time.time() - t0 > BUDGET_S:
        print("time budget reached", flush=True); break
    ko = int(datetime.fromisoformat(m["occurrence_datetime"].replace("Z", "+00:00")).timestamp())
    series = m["event_ticker"].split("-")[0]
    d = get(f"{BASE}/series/{series}/markets/{m['ticker']}/candlesticks",
            {"start_ts": ko - 3 * 86400, "end_ts": ko, "period_interval": 60})
    c = []
    for x in (d or {}).get("candlesticks") or []:
        def num(o, k):
            v = (o or {}).get(k)
            try:
                return float(v) if v is not None else None
            except (TypeError, ValueError):
                return None
        yb, ya, pr = x.get("yes_bid") or {}, x.get("yes_ask") or {}, x.get("price") or {}
        c.append([x.get("end_period_ts"), num(yb, "close_dollars") or num(yb, "close"),
                  num(ya, "close_dollars") or num(ya, "close"), num(pr, "close_dollars") or num(pr, "close"),
                  num(x, "volume_fp") or num(x, "volume")])
    new.append({"ticker": m["ticker"], "event": m["event_ticker"], "series": series, "kickoff": ko,
                "result": m["result"], "teams": teams.get(m["event_ticker"], []), "candles": c})
    if len(new) == 1:
        print("first candle sample:", json.dumps((d or {}).get("candlesticks", [])[:1])[:800], flush=True)
    if len(new) % 500 == 0:
        print(f"{len(new)} fetched", flush=True)
        with gzip.open(OUT, "wt") as f:
            for r in old + new:
                f.write(json.dumps(r) + "\n")
    time.sleep(0.08)
with gzip.open(OUT, "wt") as f:
    for r in old + new:
        f.write(json.dumps(r) + "\n")
print(f"saved {len(old) + len(new)} tie markets ({len(new)} new)")
