"""One-off probe (read-only): which assets have Up/Down markets, what the price-to-beat endpoint returns,
and whether the RTDS feed delivers Chainlink + TWAP messages."""
import json, os, sys, time
import requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
S = requests.Session(); S.headers["User-Agent"] = "Mozilla/5.0 polymarket-lab-research"
now = int(time.time()); st = now // 300 * 300 - 300; end = st + 300
iso = lambda t: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t))

for a in ("btc", "eth", "sol", "xrp", "doge", "bnb"):
    for w in ("5m", "15m"):
        slug = f"{a}-updown-{w}-{st}"
        try:
            ev = S.get("https://gamma-api.polymarket.com/events", params={"slug": slug}, timeout=10).json()
            print(slug, "->", ev[0]["markets"][0]["question"] if ev else "NONE")
        except Exception as e:  # noqa: BLE001
            print(slug, "err", str(e)[:80])

variants = [
    {"symbol": "BTC", "variant": "five", "eventStartTime": iso(st), "endDate": iso(end)},
    {"symbol": "BTC", "variant": "five", "eventStartTime": st, "endDate": end},
    {"symbol": "BTC", "variant": "five", "eventStartTime": st * 1000, "endDate": end * 1000},
    {"symbol": "BTC", "variant": "fifteen", "eventStartTime": iso(now // 900 * 900 - 900), "endDate": iso(now // 900 * 900)},
]
for v in variants:
    try:
        r = S.get("https://polymarket.com/api/crypto/crypto-price", params=v, timeout=10)
        print("crypto-price", v, "->", r.status_code, r.text[:400].replace("\n", " "))
    except Exception as e:  # noqa: BLE001
        print("crypto-price", v, "err", str(e)[:100])

import rtds  # noqa: E402
stop = rtds.start()
time.sleep(75)
print("stats", json.dumps(rtds.stats))
for k, v in sorted(rtds.latest.items()):
    print("latest", k, v)
for k in (("crypto_prices_twap_sixty", "btc/usd"), ("crypto_prices_chainlink", "btc/usd")):
    pts = rtds.series(k[0], k[1], 0, 1e12)
    print(k, "points", len(pts), pts[:3], pts[-3:])
stop.set()
# raw sample lines
import gzip, glob  # noqa: E402
for f in sorted(glob.glob("data/fast/rtds/*.jsonl.gz"))[-1:]:
    with gzip.open(f, "rt") as fh:
        for i, line in enumerate(fh):
            if i < 12:
                print("raw", line.strip()[:300])
