"""Read-only look at public combo (parlay) data: SDK public-client methods and model fields, then the raw endpoints
(combo markets, combo activity, combo positions, biggest winners) without keys. No orders, no quote requests."""
import os, re, subprocess, sys, json, inspect, time
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "polymarket-client"], check=False)
import requests
try:
    import polymarket
except Exception as e:  # noqa: BLE001
    print("import failed", e); sys.exit(0)
d = os.path.dirname(polymarket.__file__)
print("clients:", [n for n in dir(polymarket) if "Client" in n])


def show(path, a, b):
    try:
        lines = open(os.path.join(d, path), encoding="utf-8").read().split("\n")
        print(f"\n--- {path} [{a}:{b}]")
        for i in range(a - 1, min(b, len(lines))):
            print(f"{i + 1:5}: {lines[i][:200]}")
    except Exception as e:  # noqa: BLE001
        print("  cannot show", path, e)


show("_internal/actions/data.py", 155, 180)
show("_internal/actions/data.py", 248, 295)
show("_internal/actions/data.py", 590, 640)
show("_internal/actions/rfq.py", 60, 90)
# model fields
for root, _, fs in os.walk(os.path.join(d, "models")):
    for f in fs:
        p = os.path.join(root, f)
        src = open(p, encoding="utf-8", errors="ignore").read()
        for cls in ("ComboTradeActivity", "ComboPosition", "ComboPositionLeg", "ComboMarket", "ComboBiggestWinner", "ComboActivity"):
            m = re.search(rf"class {cls}\b[^\n]*\n((?:    [^\n]*\n|\n){{1,45}})", src)
            if m:
                print(f"\n--- {os.path.relpath(p, d)} class {cls}\n{m.group(1)[:1800]}")
S = requests.Session(); S.headers["User-Agent"] = "polymarket-lab-research/0.1"


def raw(url, params=None):
    try:
        r = S.get(url, params=params, timeout=30)
        print(f"\nGET {url} {params} -> {r.status_code} {len(r.content)} bytes\n{r.text[:1800]}")
        return r.json() if r.status_code == 200 else None
    except Exception as e:  # noqa: BLE001
        print("  !", url, e); return None


cm = raw("https://combos-rfq-api.polymarket.com/v1/rfq/combo-markets", {"limit": 3})
act = raw("https://data-api.polymarket.com/v2/activity/combos", {"limit": 5})
pos = raw("https://data-api.polymarket.com/v2/positions/combos", {"limit": 5})
for path in ("/v2/biggest-winners", "/v2/winners", "/biggest-winners", "/v2/leaderboard/biggest-winners"):
    raw("https://data-api.polymarket.com" + path, {"limit": 3})
