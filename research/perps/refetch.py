"""Slow, resumable refetch: funding for instruments missing from pm_funding.jsonl.gz, then hourly candles
for the coins that matter (crypto with a Hyperliquid twin). Writes after every instrument."""
import asyncio, gzip, json, os, time
from datetime import datetime, timezone, timedelta
import requests
from polymarket import AsyncPublicClient

OUT = "data/perps"
start = datetime.now(timezone.utc) - timedelta(days=60)
COINS = os.environ.get("COINS", "ARB,ETHFI,LINK,ENA,JUP,AAVE,ADA,PUMP,SUI,BNB,HYPE,AVAX,DOGE,LDO,LTC,NEAR,ONDO,TAO,UNI,WLD,XRP,ZEC,ZRO,PENDLE,MORPHO,KAITO,VIRTUAL,TIA,BTC,ETH,SOL").split(",")


def dump(o):
    try:
        return o.model_dump(mode="json")
    except Exception:  # noqa: BLE001
        return repr(o)


def have_funding():
    s = set()
    p = f"{OUT}/pm_funding.jsonl.gz"
    if os.path.exists(p):
        for l in gzip.open(p, "rt"):
            s.add(json.loads(l)["_sym"])
    return s


async def call(fn, **kw):
    for a in range(8):
        try:
            return [dump(x) async for x in fn(**kw).iter_items()]
        except Exception as e:  # noqa: BLE001
            if "rate limited" not in str(e):
                print("error", str(e)[:120], flush=True); return None
            await asyncio.sleep(15 * (a + 1))
    return None


async def main():
    pc = AsyncPublicClient()
    inst = json.load(open(f"{OUT}/pm_instruments.json"))
    have = have_funding()
    for i in inst:
        sym = i["symbol"]; base = sym.split("-")[0]
        if base not in COINS:
            continue
        if sym not in have:
            rows = await call(pc.list_perps_funding_history, instrument_id=int(i["id"]), start=start)
            if rows:
                with gzip.open(f"{OUT}/pm_funding.jsonl.gz", "at") as fh:
                    for d in rows:
                        d["_iid"] = i["id"]; d["_sym"] = sym; fh.write(json.dumps(d, default=str) + "\n")
                print("funding", sym, len(rows), flush=True)
            await asyncio.sleep(3)
        cp = f"{OUT}/pm_candles/{base}.json"
        if not os.path.exists(cp):
            os.makedirs(f"{OUT}/pm_candles", exist_ok=True)
            rows = await call(pc.list_perps_candles, instrument_id=int(i["id"]), interval="1h", start=start)
            if rows:
                json.dump(rows, open(cp, "w"), default=str); print("candles", sym, len(rows), flush=True)
            await asyncio.sleep(3)
        hp = f"{OUT}/hl_candles/{base}.json"
        if not os.path.exists(hp):
            os.makedirs(f"{OUT}/hl_candles", exist_ok=True)
            try:
                r = requests.post("https://api.hyperliquid.xyz/info", json={"type": "candleSnapshot", "req": {"coin": base, "interval": "1h", "startTime": int(start.timestamp() * 1000), "endTime": int(time.time() * 1000)}}, timeout=60)
                if r.ok and r.json():
                    json.dump(r.json(), open(hp, "w")); print("hl candles", base, len(r.json()), flush=True)
            except Exception as e:  # noqa: BLE001
                print("hl error", base, e)
            time.sleep(0.5)

asyncio.run(main())
print("done")
