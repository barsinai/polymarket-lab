"""Probe (read-only) before the maker-vs-taker tape census: tag vocabulary, event/market fields of a closed mention event,
the shape of the public trade tape rows, and how many closed events per tag and week exist."""
import json, time, collections, datetime as dt
import requests
S = requests.Session(); S.headers["User-Agent"] = "polymarket-lab-research/0.1"
G = "https://gamma-api.polymarket.com"; DA = "https://data-api.polymarket.com"


def get(url, params=None):
    for k in range(4):
        try:
            r = S.get(url, params=params, timeout=30)
            if r.status_code == 429:
                time.sleep(2 + 2 * k); continue
            if r.status_code != 200:
                print("  !", r.status_code, url, str(params)[:150], r.text[:200]); return None
            return r.json()
        except Exception as e:  # noqa: BLE001
            print("  !", url, e); time.sleep(1 + k)
    return None


# 1. tags
tags = []
for off in range(0, 12000, 500):
    d = get(f"{G}/tags", {"limit": 500, "offset": off})
    if not d:
        break
    tags += d
    if len(d) < 500:
        break
print("tags", len(tags))
KW = ("mention", "earn", "tweet", "elon", "weather", "culture", "movie", "music", "award", "grammy", "oscar", "youtube", "mrbeast", "box",
      "rotten", "tv", "celeb", "econ", "fed", "inflation", "ai", "tech", "sport", "nba", "nfl", "soccer", "esport", "tennis", "crypto",
      "politic", "geopol", "world", "election", "finance", "stock", "business", "science", "trump", "netflix", "spotify", "billboard",
      "chart", "views", "game", "recurring", "daily", "weekly")
hit = sorted({(t.get("slug") or "") for t in tags if any(k in (t.get("slug") or "") for k in KW)})
print("matching slugs", len(hit)); print(hit[:400])

# 2. closed mention events: fields
now = dt.datetime.now(dt.timezone.utc)
ev = get(f"{G}/events", {"tag_slug": "mentions", "closed": "true", "limit": 20, "order": "endDate", "ascending": "false",
                         "end_date_max": (now - dt.timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%SZ")}) or []
print("mention events fetched", len(ev))
if ev:
    e = max(ev, key=lambda e: float(e.get("volume") or 0))
    print("EVENT keys", sorted(e.keys()))
    print({k: str(e.get(k))[:120] for k in e if k not in ("markets", "description")})
    print("tags of the event", [t.get("slug") for t in e.get("tags") or []])
    m = max(e.get("markets") or [{}], key=lambda m: float(m.get("volumeNum") or 0))
    print("MARKET keys", sorted(m.keys()))
    print({k: str(m.get(k))[:140] for k in m if k not in ("description",)})
    cid = m.get("conditionId")
    # 3. trade tape rows
    d = get(f"{DA}/v2/trades", {"condition_id": cid, "limit": 500})
    rows = (d or {}).get("data") if isinstance(d, dict) else d
    print("v2 trades:", type(d).__name__, (list(d.keys()) if isinstance(d, dict) else None), "rows", len(rows or []))
    if rows:
        print("ROW keys", sorted(rows[0].keys())); print(rows[0]); print(rows[-1])
        print("side x outcome", collections.Counter((r.get("side"), r.get("outcome_index")) for r in rows))
        print("pagination", (d or {}).get("pagination") if isinstance(d, dict) else None)
    d1 = get(f"{DA}/trades", {"market": cid, "limit": 5, "takerOnly": "false"})
    print("v1 trades takerOnly=false:", str(d1)[:600])
    d2 = get(f"{DA}/v2/trades", {"condition_id": cid, "limit": 5, "taker_only": "false"})
    print("v2 taker_only=false:", str(d2)[:600])

# 4. how many closed events per tag per week (last 8 weeks)
for tag in ("mentions", "earnings-calls", "weather", "pop-culture", "culture", "movies", "music", "awards", "tweet-markets", "elon-tweets",
            "economy", "ai", "tech", "esports", "nba", "tennis", "crypto-prices", "politics", "geopolitics", "youtube", "mrbeast"):
    out = []
    for w in range(1, 7):
        a = now - dt.timedelta(days=7 * w + 3); b = now - dt.timedelta(days=7 * (w - 1) + 3)
        n = 0; nm = 0; vol = 0.0
        for off in range(0, 2000, 100):
            page = get(f"{G}/events", {"tag_slug": tag, "closed": "true", "limit": 100, "offset": off,
                                       "end_date_min": a.strftime("%Y-%m-%dT%H:%M:%SZ"), "end_date_max": b.strftime("%Y-%m-%dT%H:%M:%SZ")})
            if not page:
                break
            n += len(page); nm += sum(len(e.get("markets") or []) for e in page); vol += sum(float(e.get("volume") or 0) for e in page)
            if len(page) < 100:
                break
        out.append((n, nm, round(vol / 1000)))
    print(f"{tag:16} per week (events, markets, $k volume): {out}", flush=True)
