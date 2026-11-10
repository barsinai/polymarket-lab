"""Settle the paper windows: fetch the official result (priceToBeat / finalPrice / winner) for every window slug the
bot has seen and store it in data/fast/results_meta.json. Read-only against Polymarket (Gamma events by slug).

This is the results half of wallets.py without the trade tape, so it runs in a minute and adds nothing heavy to git.
Windows that are not resolved yet (outcome prices not at 0.99+) stay unsettled and are retried next time.
"""
import json, time
from concurrent.futures import ThreadPoolExecutor
import requests

D = "data/fast"
S = requests.Session(); S.headers["User-Agent"] = "polymarket-lab-research/0.1"
GAMMA = "https://gamma-api.polymarket.com"
try:
    meta = json.load(open(f"{D}/results_meta.json"))
except OSError:
    meta = {}


def get(url, params, tries=4):
    for i in range(tries):
        try:
            r = S.get(url, params=params, timeout=20)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 429:
                time.sleep(2 + 2 * i); continue
            return None
        except Exception:  # noqa: BLE001
            time.sleep(1 + i)
    return None


def fetch_meta(slug):
    ev = get(f"{GAMMA}/events", {"slug": slug})
    if not ev:
        return slug, None
    e = ev[0]; m = e["markets"][0]; md = e.get("eventMetadata") or {}
    pr = [float(x) for x in json.loads(m["outcomePrices"])]
    w = {"5m": 300, "15m": 900, "4h": 14400}.get(slug.split("-")[2], 300)
    return slug, {"cid": m["conditionId"], "tokens": json.loads(m.get("clobTokenIds") or "[]"), "up": bool(pr[0] > pr[1]) if max(pr) >= 0.99 else None,
                  "ptb": md.get("priceToBeat"), "final": md.get("finalPrice"), "start": int(slug.rsplit("-", 1)[1]),
                  "window": w, "volume": float(m.get("volumeNum") or 0)}


slugs = set()
for f in ("windows.jsonl", "trades.jsonl", "tokens.jsonl"):
    try:
        for line in open(f"{D}/{f}"):
            try:
                slugs.add(json.loads(line)["slug"])
            except (ValueError, KeyError):
                pass
    except OSError:
        pass
now = time.time()
todo = sorted(s for s in slugs if (s not in meta or meta[s].get("up") is None)
              and int(s.rsplit("-", 1)[1]) + {"5m": 300, "15m": 900, "4h": 14400}.get(s.split("-")[2], 300) + 120 < now)
print("slugs", len(slugs), "already settled", sum(1 for s in slugs if meta.get(s, {}).get("up") is not None), "to fetch", len(todo), flush=True)
n_ok = 0
with ThreadPoolExecutor(6) as ex:
    for slug, md in ex.map(fetch_meta, todo):
        if md:
            meta[slug] = md; n_ok += md["up"] is not None
json.dump(meta, open(f"{D}/results_meta.json", "w"))
print("fetched", len(todo), "newly settled", n_ok, "meta total", len(meta), "settled total", sum(1 for v in meta.values() if v.get("up") is not None))
