"""Probe (read-only): resolution rules and buckets of the daily highest-temperature markets."""
import json, requests, datetime as dt
S = requests.Session(); S.headers["User-Agent"] = "polymarket-lab-research/0.1"
d = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=1)).strftime("%B-%-d-%Y").lower()
seen = 0
r = S.get("https://gamma-api.polymarket.com/public-search", params={"q": "highest temperature", "limit_per_type": 50, "events_status": "active"}, timeout=25)
evs = r.json().get("events") or []
print("events found", len(evs), "slugs:", sorted({e["slug"].rsplit("-on-", 1)[0].replace("highest-temperature-in-", "") for e in evs}))
for e in evs:
    if seen >= 3:
        break
    full = S.get("https://gamma-api.polymarket.com/events", params={"slug": e["slug"]}, timeout=25).json()[0]
    seen += 1
    print("\n=====", full["slug"], "end", full.get("endDate"), "negRisk", full.get("negRisk"))
    print("DESCRIPTION:", (full.get("description") or "")[:2500])
    print("resolutionSource:", full.get("resolutionSource"))
    for m in full.get("markets") or []:
        print(f"  {m.get('groupItemTitle')!s:22} prices {m.get('outcomePrices')} bestAsk {m.get('bestAsk')} bestBid {m.get('bestBid')} vol {float(m.get('volumeNum') or 0):9,.0f} | {m.get('question')}")
# how many cities / dates are open, and total volume per day
by = {}
for e in evs:
    city, date = e["slug"].replace("highest-temperature-in-", "").rsplit("-on-", 1)
    by.setdefault(date, []).append((city, float(e.get("volume") or 0)))
for date, L in sorted(by.items()):
    print(date, len(L), "cities, volume", f"{sum(v for _, v in L):,.0f}")
