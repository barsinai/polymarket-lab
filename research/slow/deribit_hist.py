"""Deribit public history for the order-book period (read-only): BTC and ETH index price (5-min closes) and the DVOL
implied-volatility index (hourly), 10-29..now. Used to price the daily crypto price markets in the 15-min book snapshots
with a lognormal at implied vol (a cheap stand-in for the full smile of options_probe.py).
Output: data/research/deribit_hist.json {"BTC": {"px": [[t, close], ...], "dvol": [[t, close], ...]}, "ETH": {...}}"""
import json, time
import requests
S = requests.Session(); S.headers["User-Agent"] = "polymarket-lab-research/0.1"
B = "https://www.deribit.com/api/v2/public"
start = int(time.mktime(time.strptime("2026-10-29", "%Y-%m-%d"))) * 1000; end = int(time.time() * 1000)
out = {}
for cur in ("BTC", "ETH"):
    px = []; t = start
    while t < end:
        t2 = min(t + 5 * 86400 * 1000, end)
        r = S.get(f"{B}/get_tradingview_chart_data", params={"instrument_name": f"{cur}-PERPETUAL", "start_timestamp": t,
                  "end_timestamp": t2, "resolution": "5"}, timeout=30).json().get("result") or {}
        px += [[ti // 1000, c] for ti, c in zip(r.get("ticks", []), r.get("close", []))]
        t = t2; time.sleep(0.2)
    dv = []; t = start
    while t < end:
        t2 = min(t + 10 * 86400 * 1000, end)
        r = S.get(f"{B}/get_volatility_index_data", params={"currency": cur, "start_timestamp": t, "end_timestamp": t2,
                  "resolution": "3600"}, timeout=30).json().get("result") or {}
        dv += [[row[0] // 1000, row[4]] for row in r.get("data", [])]
        t = t2; time.sleep(0.2)
    out[cur] = {"px": sorted(set(map(tuple, px))), "dvol": sorted(set(map(tuple, dv)))}
    print(cur, "px", len(out[cur]["px"]), "dvol", len(out[cur]["dvol"]), flush=True)
json.dump(out, open("data/research/deribit_hist.json", "w"))
