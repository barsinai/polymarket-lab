"""Read-only probe: status filters of /v2/positions/combos (the default listing hides redeemed winners) and the row shapes of
/v2/activity/combos, for one maker wallet seen in the census. No keys, no orders."""
import json, collections
import requests
S = requests.Session(); S.headers["User-Agent"] = "polymarket-lab-research/0.1"
DA = "https://data-api.polymarket.com"
W = "0x2b9653d5e0a68b4867eacfa26cfa04c3802831b1"


def raw(path, params, show=600):
    try:
        r = S.get(DA + path, params=params, timeout=30)
        try:
            d = r.json()
        except Exception:  # noqa: BLE001
            d = None
        rows = (d or {}).get("data") if isinstance(d, dict) else None
        print(f"GET {path} {params} -> {r.status_code} rows {len(rows) if rows is not None else '-'} {'' if rows else r.text[:show]}")
        return rows
    except Exception as e:  # noqa: BLE001
        print("  !", path, e); return None


for st in ("OPEN", "REDEEMABLE", "RESOLVED_WIN", "RESOLVED_LOSS", "RESOLVED", "REDEEMED", "CLOSED", "PARTIAL", "ALL", "WON", "bogus"):
    rows = raw("/v2/positions/combos", {"user": W, "limit": 3, "status": st})
    if rows:
        print("   statuses:", collections.Counter(r.get("status") for r in rows), "sample:", json.dumps({k: v for k, v in rows[0].items() if k != "legs"})[:500])
for extra in ({"size_threshold": 0}, {"sizeThreshold": 0}, {"include_dust": "true"}, {"sort_by": "bogus"}):
    rows = raw("/v2/positions/combos", dict({"user": W, "limit": 3}, **extra))
    if rows:
        print("   statuses:", collections.Counter(r.get("status") for r in rows))
rows = raw("/v2/activity/combos", {"user": W, "limit": 1000})
if rows:
    print("activity types:", collections.Counter((r.get("type"), r.get("side"), r.get("outcome_index")) for r in rows))
    seen = set()
    for r in rows:
        k = (r.get("type"), r.get("side"))
        if k not in seen:
            seen.add(k); print("  ", json.dumps({kk: vv for kk, vv in r.items() if kk not in ("icon", "image")})[:900])
    ts = [r.get("timestamp") for r in rows if r.get("timestamp")]
    print("  time span of 1000 rows:", min(ts), max(ts))
raw("/v2/activity", {"user": W, "limit": 3})
