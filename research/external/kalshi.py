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
        "volume", "open_interest", "liquidity", "category", "rules_primary", "strike_type", "floor_strike", "cap_strike",
        "occurrence_datetime", "expected_expiration_time", "market_type", "settlement_ts", "created_time")
out = []
for status in ("settled", "open"):
    cursor, n = None, 0
    while True:
        # exclude auto-generated combination ("multivariate") markets: millions of tiny parlays
        params = {"limit": 1000, "status": status, "mve_filter": "exclude",
                  "min_close_ts": 1735689600}  # closing from 2025-01-01
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
        if n == 0 and ms:  # log the real field names once (the API has renamed fields before)
            print("sample market keys:", sorted(ms[0].keys()), flush=True)
            print("sample market:", json.dumps(ms[0])[:1500], flush=True)
        def vol(m):
            for k in ("volume", "volume_fp", "volume_24h", "dollar_volume", "notional_value"):
                try:
                    v = float(m.get(k) or 0)
                except (TypeError, ValueError):
                    v = 0
                if v:
                    return v
            return 0.0
        out += [{**{k: m.get(k) for k in KEEP}, "_vol": vol(m),
                 **{k: m[k] for k in m if k.endswith("_dollars") or k.endswith("_fp")}}
                for m in ms if vol(m) >= 1000]
        n += len(ms)
        cursor = d.get("cursor")
        if n % 20000 < 1000:
            print(f"{status}: {n} seen, {len(out)} kept", flush=True)
            with gzip.open("data/external/kalshi/markets.jsonl.gz", "wt") as f:  # save as we go
                for m in out:
                    f.write(json.dumps(m) + "\n")
        if not cursor or not ms:
            break
        time.sleep(0.2)
    print(f"{status}: {n} markets seen", flush=True)
with gzip.open("data/external/kalshi/markets.jsonl.gz", "wt") as f:
    for m in out:
        f.write(json.dumps(m) + "\n")
print(f"saved {len(out)} Kalshi markets with volume >= 1000")
