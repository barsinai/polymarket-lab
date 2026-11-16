"""c22 check for charts_paper.py (LESSONS 10): are there chart events at all, and when do they end? Read-only."""
import requests, re, datetime as dt, json
G = "https://gamma-api.polymarket.com"; PAT = re.compile(r"netflix|app store|play store|spotify|billboard|hot 100", re.I)
now = dt.datetime.now(dt.timezone.utc); seen = {}
for q in ("netflix", "app store", "spotify", "billboard", "hot 100", "top free app", "#1 song"):
    r = requests.get(f"{G}/public-search", params={"q": q, "events_status": "active", "limit_per_type": 50}, timeout=30).json()
    for e in r.get("events", []) or []:
        seen[e["id"]] = (q, e.get("title"), e.get("endDate"), bool(PAT.search(e.get("title") or "")), len(e.get("markets") or []))
for tag in ("pop-culture", "music", "apps", "netflix", "spotify"):
    for e in requests.get(f"{G}/events", params={"tag_slug": tag, "active": "true", "closed": "false", "limit": 100}, timeout=30).json() or []:
        if PAT.search(e.get("title") or ""):
            seen.setdefault(e["id"], ("tag:" + tag, e.get("title"), e.get("endDate"), True, len(e.get("markets") or [])))
for k, v in sorted(seen.items(), key=lambda x: x[1][2] or ""):
    print(k, v)
print("now", now.isoformat(), "n", len(seen))
