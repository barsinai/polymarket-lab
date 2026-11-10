"""Probe (read-only): can the runner read Kalshi's public market data, and what is there to match against Polymarket?
Prints counts by category and a sample of liquid open markets with prices."""
import json, requests, collections
S = requests.Session(); S.headers["User-Agent"] = "polymarket-lab-research/0.1"
base = "https://api.elections.kalshi.com/trade-api/v2"
out = []; cursor = None
for i in range(15):
    params = {"limit": 1000, "status": "open"}
    if cursor: params["cursor"] = cursor
    r = S.get(f"{base}/markets", params=params, timeout=30)
    print("status", r.status_code, flush=True)
    if r.status_code != 200:
        print(r.text[:300]); break
    d = r.json(); out += d.get("markets", []); cursor = d.get("cursor")
    if not cursor: break
print("open markets", len(out))
cat = collections.Counter(m.get("category") or m.get("event_ticker", "")[:6] for m in out); print(cat.most_common(25))
liq = sorted(out, key=lambda m: -float(m.get("volume_24h") or m.get("volume") or 0))[:60]
for m in liq:
    print(f"{m.get('ticker'):40} vol24 {m.get('volume_24h')} yes_bid {m.get('yes_bid')} yes_ask {m.get('yes_ask')} close {m.get('close_time','')[:10]} | {m.get('title','')[:80]}")
json.dump(out, open("data/slow/kalshi_markets.json", "w"))
