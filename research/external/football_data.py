"""Download football-data.co.uk season files (results + bookmaker odds, incl. Pinnacle closing
odds PSCH/PSCD/PSCA) for the leagues Polymarket lists. Saves data/external/football/<season>_<div>.csv"""
import os, time
import requests
BASE = "https://www.football-data.co.uk/mmz4281"
SEASONS = ["2526", "2627"]
DIVS = ["E0", "E1", "SP1", "I1", "D1", "F1", "N1", "P1"]
OUT = "data/external/football"
os.makedirs(OUT, exist_ok=True)
S = requests.Session(); S.headers["User-Agent"] = "polymarket-lab-research/0.1"
for season in SEASONS:
    for div in DIVS:
        for k in range(3):
            try:
                r = S.get(f"{BASE}/{season}/{div}.csv", timeout=60)
                if r.status_code == 200 and len(r.content) > 500:
                    open(f"{OUT}/{season}_{div}.csv", "wb").write(r.content)
                    print(season, div, len(r.content), "bytes", flush=True)
                    break
                print(season, div, r.status_code, len(r.content), flush=True)
                if r.status_code == 404:
                    break
            except Exception as e:  # noqa: BLE001
                print(season, div, "error", e, flush=True)
            time.sleep(2 ** k)
        time.sleep(0.5)
