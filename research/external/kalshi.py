"""Download Kalshi's public market list (settled + open) so questions can be matched with
Polymarket's. Saves data/external/kalshi/markets.jsonl.gz (slim records). Public endpoints,
no account needed."""
import gzip, json, os, time
import requests
BASE = "https://api.elections.kalshi.com/trade-api/v2"
S = requests.Session(); S.headers["User-Agent"] = "polymarket-lab-research/0.1"
os.makedirs("data/external/kalshi", exist_ok=True)
KEEP = ("ticker", "event_ticker", "series_ticker", "title", "subtitle", "yes_sub_title", "no_sub_title", "status",
        "result", "open_time", "close_time", "expiration_time", "settlement_value", "last_price", "yes_bid", "yes_ask",
        "volume", "open_interest", "liquidity", "category", "rules_primary", "strike_type", "floor_strike", "cap_strike")
out = []
for status in ("settled", "open"):
    cursor, n = None, 0
    while True:
        params = {"limit": 1000, "status": status}
        if cursor:
            params["cursor"] = cursor
        for k in range(5):
            r = S.get(f"{BASE}/markets", params=params, timeout=60)
            if r.status_code == 200:
                break
            print(status, r.status_code, r.text[:200], flush=True); time.sleep(2 ** k)
        if r.status_code != 200:
            break
        d = r.json()
        ms = d.get("markets") or []
        out += [{k: m.get(k) for k in KEEP} for m in ms if (m.get("volume") or 0) >= 1000]
        n += len(ms)
        cursor = d.get("cursor")
        if n % 20000 < 1000:
            print(f"{status}: {n} seen, {len(out)} kept", flush=True)
        if not cursor or not ms:
            break
        time.sleep(0.2)
    print(f"{status}: {n} markets seen", flush=True)
with gzip.open("data/external/kalshi/markets.jsonl.gz", "wt") as f:
    for m in out:
        f.write(json.dumps(m) + "\n")
print(f"saved {len(out)} Kalshi markets with volume >= 1000")
