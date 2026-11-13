"""Outcomes for the markets in data/research/books_ids.json (markets seen in the 15-min order-book snapshots whose end date
has passed): Gamma /markets/{id} -> closed, outcomePrices, umaResolutionStatus, feesEnabled-ish fields, gameStartTime.
Writes data/research/books_outcomes.json {id: {...}}; keeps what it already has (re-run to fill gaps)."""
import json, os, time
import requests
S = requests.Session(); S.headers["User-Agent"] = "polymarket-lab-research/0.1"
OUT = "data/research/books_outcomes.json"
ids = json.load(open("data/research/books_ids.json"))
have = json.load(open(OUT)) if os.path.exists(OUT) else {}
keep = ("closed", "outcomePrices", "outcomes", "umaResolutionStatus", "endDate", "closedTime", "gameStartTime", "eventStartTime",
        "feesEnabled", "feeSchedule", "makerBaseFee", "takerBaseFee", "category", "sportsMarketType", "resolutionSource", "events")
t0 = time.time(); n = 0
for i in ids:
    if i in have and have[i].get("closed"):
        continue
    for k in range(3):
        try:
            r = S.get(f"https://gamma-api.polymarket.com/markets/{i}", timeout=20)
            if r.status_code == 429:
                time.sleep(2 + k * 3); continue
            m = r.json() if r.status_code == 200 else {}
            break
        except Exception:  # noqa: BLE001
            time.sleep(1); m = {}
    d = {k: m.get(k) for k in keep if k in m}
    if "events" in d and isinstance(d["events"], list) and d["events"]:
        e = d["events"][0]; d["events"] = {"slug": e.get("slug"), "title": e.get("title"), "seriesSlug": e.get("seriesSlug"),
                                            "tags": [t.get("slug") for t in (e.get("tags") or []) if isinstance(t, dict)]}
    have[i] = d; n += 1
    if n % 500 == 0:
        json.dump(have, open(OUT, "w")); print(n, "fetched", round(time.time() - t0), "s", flush=True)
    if time.time() - t0 > 3000:
        break
json.dump(have, open(OUT, "w"))
print("done", n, "fetched; closed:", sum(1 for v in have.values() if v.get("closed")), "of", len(have))
