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


# 2. closed mention events: fields
now = dt.datetime.now(dt.timezone.utc)
for TAG in ("mention-markets", "earnings-calls", "weather", "mrbeast", "trump-mentions", "mentions-markets", "what-will-they-say"):
  ev = get(f"{G}/events", {"tag_slug": TAG, "closed": "true", "limit": 20, "order": "endDate", "ascending": "false",
                         "end_date_min": (now - dt.timedelta(days=12)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                         "end_date_max": (now - dt.timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%SZ")}) or []
  print("=====", TAG, "events fetched", len(ev), [e.get("slug") for e in ev[:5]])
  if ev and TAG in ("mention-markets", "earnings-calls", "weather"):
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

