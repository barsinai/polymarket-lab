"""Download hourly exchange prices (Coinbase, public API) for the coins Polymarket lists,
so crypto markets' fair value can be computed offline. Saves data/external/crypto/<COIN>.json.gz
as [[unix_ts, open, high, low, close], ...] hourly, from 2024-01-01."""
import gzip, json, os, time
from datetime import datetime, timezone
import requests
COINS = ["BTC", "ETH", "SOL", "XRP", "DOGE"]
S = requests.Session(); S.headers["User-Agent"] = "polymarket-lab-research/0.1"
os.makedirs("data/external/crypto", exist_ok=True)
start = int(datetime(2024, 1, 1, tzinfo=timezone.utc).timestamp())
now = int(time.time())
for coin in COINS:
    out, t = {}, start
    while t < now:
        end = min(t + 300 * 3600, now)
        for k in range(5):
            r = S.get(f"https://api.exchange.coinbase.com/products/{coin}-USD/candles",
                      params={"granularity": 3600, "start": datetime.fromtimestamp(t, timezone.utc).isoformat(),
                              "end": datetime.fromtimestamp(end, timezone.utc).isoformat()}, timeout=30)
            if r.status_code == 200:
                break
            print(coin, r.status_code, r.text[:200], flush=True); time.sleep(2 ** k)
        if r.status_code == 200:
            for ts_, low, high, open_, close, vol in r.json():
                out[ts_] = [ts_, open_, high, low, close]
        t = end
        time.sleep(0.35)
    rows = [out[k] for k in sorted(out)]
    with gzip.open(f"data/external/crypto/{coin}.json.gz", "wt") as f:
        json.dump(rows, f)
    print(f"{coin}: {len(rows)} hours", flush=True)
