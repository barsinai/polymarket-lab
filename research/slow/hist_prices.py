"""Pre-resolution price paths for the candidates in data/research/hist_cands.json (sports moneylines: hours before the game
start; non-sports: hours before the end date), from the CLOB prices-history endpoint (hourly). Read-only.
Writes data/research/hist_prices.json {id: [[t, p_token0], ...]} for t in [ref - 50 h, ref + 1 h]."""
import json, os, time
import requests
S = requests.Session(); S.headers["User-Agent"] = "polymarket-lab-research/0.1"
C = json.load(open("data/research/hist_cands.json"))
OUT = "data/research/hist_prices.json"
have = json.load(open(OUT)) if os.path.exists(OUT) else {}
t0 = time.time(); n = 0
for x in C:
    if x["id"] in have:
        continue
    ref = int(x["ref"])
    for k in range(3):
        try:
            r = S.get("https://clob.polymarket.com/prices-history", params={"market": x["tok"], "startTs": ref - 50 * 3600, "endTs": ref + 3600,
                      "fidelity": 60}, timeout=20)
            if r.status_code == 429:
                time.sleep(2 + 3 * k); continue
            h = (r.json() or {}).get("history") or [] if r.status_code == 200 else []
            break
        except Exception:  # noqa: BLE001
            time.sleep(1); h = []
    have[x["id"]] = [[int(p["t"]), float(p["p"])] for p in h if "t" in p and "p" in p]
    n += 1
    if n % 1000 == 0:
        json.dump(have, open(OUT, "w"), separators=(",", ":")); print(n, "fetched", round(time.time() - t0), "s", flush=True)
    if time.time() - t0 > 3200:
        print("time cap"); break
json.dump(have, open(OUT, "w"), separators=(",", ":"))
print("done", n, "fetched; with data:", sum(1 for v in have.values() if v), "of", len(have))
