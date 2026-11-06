"""Idea 3 (perps funding): Polymarket Perps vs Hyperliquid funding rates, same underlying.
A new venue's funding often sits far from the established venues' (one-sided flow). If the gap is
persistent and larger than fees, holding the opposite perp on each venue earns it with no price risk.
Read-only public data. Output: data/perps/pm_instruments.json, pm_funding.jsonl.gz, hl_funding.jsonl.gz
"""
import gzip, json, os, time
from datetime import datetime, timezone, timedelta
import requests

OUT = "data/perps"; os.makedirs(OUT, exist_ok=True)
DAYS = int(os.environ.get("DAYS", "60"))
start = datetime.now(timezone.utc) - timedelta(days=DAYS)


def dump(o):
    for f in ("model_dump", "dict"):
        if hasattr(o, f):
            try:
                return getattr(o, f)(mode="json") if f == "model_dump" else getattr(o, f)()
            except TypeError:
                return getattr(o, f)()
    return repr(o)


from polymarket import PublicClient  # noqa: E402
pc = PublicClient()
inst = [dump(i) for i in pc.fetch_perps_instruments()]
json.dump(inst, open(f"{OUT}/pm_instruments.json", "w"), indent=1, default=str)
print(len(inst), "instruments; sample:", json.dumps(inst[0], default=str)[:600], flush=True)
try:
    tick = [dump(t) for t in pc.fetch_perps_tickers()]
    json.dump(tick, open(f"{OUT}/pm_tickers.json", "w"), indent=1, default=str)
    print("ticker sample:", json.dumps(tick[0], default=str)[:600], flush=True)
except Exception as e:  # noqa: BLE001
    print("tickers failed", e)
n = 0
with gzip.open(f"{OUT}/pm_funding.jsonl.gz", "wt") as fh:
    for i in inst:
        iid = i.get("instrument_id") or i.get("id")
        sym = i.get("symbol") or i.get("name") or i.get("base_asset")
        try:
            for f in pc.list_perps_funding_history(instrument_id=int(iid), start=start).iter_items():
                d = dump(f); d["_iid"] = iid; d["_sym"] = sym
                fh.write(json.dumps(d, default=str) + "\n"); n += 1
        except Exception as e:  # noqa: BLE001
            print("funding failed", iid, sym, str(e)[:200], flush=True)
print(n, "Polymarket funding rows", flush=True)
# Hyperliquid: same coins
coins = set()
for i in inst:
    s = str(i.get("symbol") or i.get("name") or i.get("base_asset") or "").upper()
    for sep in ("-", "/", "_", "USD"):
        s = s.split(sep)[0] if sep in s else s
    if s:
        coins.add(s)
m = 0
with gzip.open(f"{OUT}/hl_funding.jsonl.gz", "wt") as fh:
    for c in sorted(coins):
        t = int(start.timestamp() * 1000)
        for _ in range(60):
            try:
                r = requests.post("https://api.hyperliquid.xyz/info", json={"type": "fundingHistory", "coin": c, "startTime": t}, timeout=30)
                rows = r.json() if r.ok else []
            except Exception:  # noqa: BLE001
                rows = []
            if not rows or not isinstance(rows, list):
                break
            for x in rows:
                fh.write(json.dumps(x) + "\n"); m += 1
            t = rows[-1]["time"] + 1
            if len(rows) < 500:
                break
            time.sleep(0.3)
print(m, "Hyperliquid funding rows for", sorted(coins))
