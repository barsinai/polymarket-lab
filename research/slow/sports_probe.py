"""Probe (read-only): how Polymarket lists upcoming games (event/market shape, team names, outcomes) for the main leagues."""
import json, requests
S = requests.Session(); S.headers["User-Agent"] = "polymarket-lab-research/0.1"
for tag in ("nba", "nhl", "nfl", "epl", "soccer", "ucl", "la-liga", "tennis", "ufc"):
    r = S.get("https://gamma-api.polymarket.com/events", params={"tag_slug": tag, "active": "true", "closed": "false", "limit": 5, "order": "startDate", "ascending": "false"}, timeout=25)
    evs = r.json() if r.status_code == 200 else []
    print(f"\n=== tag {tag}: {len(evs)} events (status {r.status_code})")
    for e in evs[:3]:
        print(" EVENT", e.get("slug"), "| start", e.get("startDate"), "| gameStart", (e.get("markets") or [{}])[0].get("gameStartTime"), "| markets", len(e.get("markets") or []))
        for m in (e.get("markets") or [])[:4]:
            print("   ", m.get("question"), "| outcomes", m.get("outcomes"), "| prices", m.get("outcomePrices"), "| type", m.get("sportsMarketType"), "| vol", m.get("volumeNum"))
