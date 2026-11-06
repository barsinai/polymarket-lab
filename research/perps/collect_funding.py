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


import asyncio  # noqa: E402
from polymarket import AsyncPublicClient  # noqa: E402


CANDLES = []


async def pm():
    pc = AsyncPublicClient()
    if hasattr(pc, "__aenter__"):
        pc = await pc.__aenter__()
    inst = [dump(i) for i in await pc.fetch_perps_instruments()]
    tick = [dump(t) for t in await pc.fetch_perps_tickers()]
    rows = []
    for i in inst:
        iid = i.get("instrument_id") or i.get("id")
        sym = i.get("symbol") or i.get("name")
        for attempt in range(6):
            got = []
            try:
                async for f in pc.list_perps_funding_history(instrument_id=int(iid), start=start).iter_items():
                    d = dump(f); d["_iid"] = iid; d["_sym"] = sym; got.append(d)
                rows.extend(got); break
            except Exception as e:  # noqa: BLE001
                print("funding retry", iid, sym, attempt, str(e)[:80], flush=True)
                await asyncio.sleep(10 * (attempt + 1))
        # hourly candles (mark/last) for the basis between venues
        for attempt in range(6):
            try:
                cs = []
                async for c in pc.list_perps_candles(instrument_id=int(iid), interval="1h", start=start).iter_items():
                    d = dump(c); d["_sym"] = sym; cs.append(d)
                CANDLES.extend(cs); break
            except Exception as e:  # noqa: BLE001
                print("candles retry", iid, sym, attempt, str(e)[:80], flush=True)
                await asyncio.sleep(10 * (attempt + 1))
        await asyncio.sleep(1.5)
    return inst, tick, rows

inst, tick, rows = asyncio.run(pm())
json.dump(inst, open(f"{OUT}/pm_instruments.json", "w"), indent=1, default=str)
json.dump(tick, open(f"{OUT}/pm_tickers.json", "w"), indent=1, default=str)
print(len(inst), "instruments; sample:", json.dumps(inst[0], default=str)[:700], flush=True)
print("ticker sample:", json.dumps(tick[0], default=str)[:700], flush=True)
with gzip.open(f"{OUT}/pm_funding.jsonl.gz", "wt") as fh:
    for d in rows:
        fh.write(json.dumps(d, default=str) + "\n")
with gzip.open(f"{OUT}/pm_candles_1h.jsonl.gz", "wt") as fh:
    for d in CANDLES:
        fh.write(json.dumps(d, default=str) + "\n")
print(len(CANDLES), "Polymarket candles; sample", json.dumps(CANDLES[:1], default=str)[:300], flush=True)
print(len(rows), "Polymarket funding rows; sample", json.dumps(rows[:2], default=str)[:600], flush=True)
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
k = 0
with gzip.open(f"{OUT}/hl_candles_1h.jsonl.gz", "wt") as fh:
    for c in sorted(coins):
        t = int(start.timestamp() * 1000)
        try:
            r = requests.post("https://api.hyperliquid.xyz/info", json={"type": "candleSnapshot", "req": {"coin": c, "interval": "1h", "startTime": t, "endTime": int(time.time() * 1000)}}, timeout=60)
            for x in (r.json() if r.ok else []) or []:
                x["coin"] = c; fh.write(json.dumps(x) + "\n"); k += 1
        except Exception:  # noqa: BLE001
            pass
        time.sleep(0.3)
print(k, "Hyperliquid candles")
