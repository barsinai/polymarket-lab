"""Forward paper test of the funding-gap carry (no orders, public data only), run hourly.
Each run: Polymarket perps tickers (mark, index, funding) + Hyperliquid metaAndAssetCtxs (mark, funding)
for COINS. Simulated book per coin: when the trailing-24h mean funding gap (PM - HL, per hour) exceeds ENTER,
short the higher-funding venue and long the other, notional NOTIONAL per leg; exit below EXIT. P&L per hour =
funding received + change in the mark-price basis; taker fees 0.17% per round trip on entry/exit.
State/output: data/perps/paper/state.json, data/perps/paper/hours.jsonl, data/perps/paper/report.json
"""
import asyncio, json, os, time
from datetime import datetime, timezone
import requests
from polymarket import AsyncPublicClient

D = "data/perps/paper"; os.makedirs(D, exist_ok=True)
COINS = os.environ.get("COINS", "ARB,ETHFI,LINK,AAVE,ENA,KAITO,ADA,JUP,DOGE,SUI,LDO,ONDO,TAO,UNI,WLD,XRP,NEAR,LTC,PENDLE,MORPHO").split(",")
ENTER, EXIT, NOTIONAL, FEE_RT = 3e-5, 1e-5, 1000.0, 0.0017


async def pm_tickers():
    pc = AsyncPublicClient()
    return {t.symbol.split("-")[0]: t for t in await pc.fetch_perps_tickers()}


def hl_ctx():
    r = requests.post("https://api.hyperliquid.xyz/info", json={"type": "metaAndAssetCtxs"}, timeout=30).json()
    return {u["name"]: c for u, c in zip(r[0]["universe"], r[1])}


def main():
    try:
        st = json.load(open(f"{D}/state.json"))
    except (OSError, ValueError):
        st = {"hist": {}, "pos": {}, "pnl": {}, "fees": 0.0, "hours": 0, "start": int(time.time())}
    pm = asyncio.run(pm_tickers()); hl = hl_ctx(); now = int(time.time())
    row = {"ts": now, "coins": {}}
    for c in COINS:
        if c not in pm or c not in hl:
            continue
        f_pm = float(pm[c].funding_rate or 0); f_hl = float(hl[c]["funding"] or 0)
        m_pm = float(pm[c].mark_price); m_hl = float(hl[c]["markPx"])
        gap = f_pm - f_hl; basis = (m_pm - m_hl) / m_hl
        h = st["hist"].setdefault(c, []); h.append(gap); st["hist"][c] = h[-24:]
        p = st["pos"].get(c, {"side": 0, "basis": basis})
        pnl = 0.0
        if p["side"]:
            pnl += p["side"] * gap * NOTIONAL - p["side"] * (basis - p["basis"]) * NOTIONAL  # side +1 = short PM / long HL
        mean = sum(st["hist"][c]) / len(st["hist"][c])
        want = p["side"]
        if len(st["hist"][c]) >= 24:
            if p["side"] == 0 and abs(mean) > ENTER:
                want = 1 if mean > 0 else -1
            elif p["side"] and p["side"] * mean < EXIT:
                want = 0
        if want != p["side"]:
            fee = FEE_RT / 2 * NOTIONAL * (abs(want) + abs(p["side"])); pnl -= fee; st["fees"] += fee
        st["pos"][c] = {"side": want, "basis": basis}
        st["pnl"][c] = st["pnl"].get(c, 0.0) + pnl
        row["coins"][c] = {"gap": gap, "mean24": mean, "basis": round(basis, 5), "side": want, "pnl": round(pnl, 4)}
    st["hours"] += 1
    with open(f"{D}/hours.jsonl", "a") as fh:
        fh.write(json.dumps(row) + "\n")
    json.dump(st, open(f"{D}/state.json", "w"))
    tot = sum(st["pnl"].values()); open_ = sum(1 for p in st["pos"].values() if p["side"])
    rep = {"updated": datetime.now(timezone.utc).isoformat(), "hours": st["hours"], "total_pnl_usd": round(tot, 2), "fees_usd": round(st["fees"], 2),
           "notional_per_leg": NOTIONAL, "open_pairs": open_, "by_coin": {c: round(v, 2) for c, v in sorted(st["pnl"].items(), key=lambda x: -x[1])}}
    json.dump(rep, open(f"{D}/report.json", "w"), indent=1)
    print(json.dumps(rep))


if __name__ == "__main__":
    main()
