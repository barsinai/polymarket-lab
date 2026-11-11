"""Probe (read-only): are there Polymarket weather/temperature markets, how liquid, and can the runner reach a free
forecast API (Open-Meteo)? Prints events and a sample forecast."""
import json, requests
S = requests.Session(); S.headers["User-Agent"] = "polymarket-lab-research/0.1"
for q in ("highest temperature", "temperature", "weather"):
    r = S.get("https://gamma-api.polymarket.com/public-search", params={"q": q, "limit_per_type": 20, "events_status": "active"}, timeout=25)
    print(q, r.status_code)
    if r.status_code == 200:
        for e in (r.json().get("events") or [])[:20]:
            ms = e.get("markets") or []
            print(f"  {e.get('slug')[:70]:70} markets {len(ms):3} vol {float(e.get('volume') or 0):10,.0f} liq {float(e.get('liquidity') or 0):9,.0f} end {str(e.get('endDate'))[:10]}")
r = S.get("https://gamma-api.polymarket.com/events", params={"tag_slug": "weather", "active": "true", "closed": "false", "limit": 50}, timeout=25)
print("tag weather", r.status_code, len(r.json()) if r.status_code == 200 else r.text[:200])
if r.status_code == 200:
    for e in r.json()[:30]:
        print(f"  {e.get('slug')[:70]:70} markets {len(e.get('markets') or []):3} vol {float(e.get('volume') or 0):10,.0f} end {str(e.get('endDate'))[:10]}")
r = S.get("https://api.open-meteo.com/v1/forecast", params={"latitude": 40.78, "longitude": -73.97, "daily": "temperature_2m_max", "temperature_unit": "fahrenheit", "timezone": "America/New_York", "forecast_days": 3}, timeout=25)
print("open-meteo", r.status_code, r.text[:300])
r = S.get("https://ensemble-api.open-meteo.com/v1/ensemble", params={"latitude": 40.78, "longitude": -73.97, "daily": "temperature_2m_max", "temperature_unit": "fahrenheit", "models": "gfs_seamless", "forecast_days": 2}, timeout=25)
print("open-meteo ensemble", r.status_code, r.text[:300])
