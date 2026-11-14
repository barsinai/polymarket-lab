"""Read-only probe: the global trade feed of the data API (filters by cash size / user), for a forward paper tracker of big
taker orders. Also prints the SDK's trade-listing parameters. No keys."""
import os, re, subprocess, sys, json, time
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "polymarket-client"], check=False)
import requests
try:
    import polymarket
    d = os.path.dirname(polymarket.__file__)
    src = open(os.path.join(d, "_internal/actions/data.py"), encoding="utf-8").read().split("\n")
    for i, ln in enumerate(src):
        if re.search(r"def list_trades_spec|def list_activity_spec", ln):
            print("\n".join(f"{j + 1:5}: {src[j][:170]}" for j in range(i, min(i + 55, len(src)))))
except Exception as e:  # noqa: BLE001
    print("sdk look failed", e)
S = requests.Session(); S.headers["User-Agent"] = "polymarket-lab-research/0.1"
DA = "https://data-api.polymarket.com"


def raw(params):
    try:
        r = S.get(DA + "/v2/trades", params=params, timeout=30)
        d = r.json() if r.headers.get("content-type", "").startswith("application/json") else None
        rows = (d or {}).get("data") if isinstance(d, dict) else None
        if rows is None:
            print(f"GET /v2/trades {params} -> {r.status_code} {r.text[:300]}"); return
        now = time.time()
        print(f"GET /v2/trades {params} -> {r.status_code} rows {len(rows)}; usd sizes {[round(float(x['size']) * float(x['price'])) for x in rows[:12]]}; "
              f"age s {[round(now - float(x['timestamp'])) for x in rows[:6]]}; titles {[x.get('title', '')[:30] for x in rows[:3]]}; pagination {d.get('pagination')}")
    except Exception as e:  # noqa: BLE001
        print("  !", params, e)


raw({"limit": 20})
raw({"limit": 20, "filter_type": "CASH", "filter_amount": 1000})
raw({"limit": 20, "filterType": "CASH", "filterAmount": 1000})
raw({"limit": 20, "min_usdc_size": 1000})
raw({"limit": 20, "user": "0x2b9653d5e0a68b4867eacfa26cfa04c3802831b1"})
raw({"limit": 20, "event_slug": "what-will-trump-say-during-60-minutes-extended-interview"})
raw({"limit": 20, "taker_only": "true", "side": "BUY", "filter_type": "CASH", "filter_amount": 2000})
