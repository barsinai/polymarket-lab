"""Slow paper bot: fade sudden spikes in long-dated markets (hourly, public data, NO ORDERS).

Rule from the backtest (53k random closed markets): when a market's Yes price is >= SPIKE above where it was a day
ago, buy No 5-30 minutes later and sell a day later (or hold to resolution). The mirror (dump -> buy Yes) runs as a
control. Reference here = Gamma's oneDayPriceChange (last price minus the price 24 h ago), a proxy for the
backtest's trailing-day average. Entry = best ask of the token we buy (CLOB book), $10, one entry per market per
day; exit = best bid 24 h later; also tracked to resolution.
State: data/slow/spike_positions.jsonl (one line per position, updated in place), data/slow/spike_report.json.
"""
import json, os, time
import requests

GAMMA, CLOB = "https://gamma-api.polymarket.com", "https://clob.polymarket.com"
SPIKE = float(os.environ.get("SPIKE", "0.15")); SIZE = float(os.environ.get("SIZE", "10"))
MIN_LIQ, MIN_DAYS = 1000.0, 2.0
D = "data/slow"; os.makedirs(D, exist_ok=True)
S = requests.Session(); S.headers["User-Agent"] = "polymarket-lab-research/0.1"
now = time.time()


def get(url, params, tries=3):
    for i in range(tries):
        try:
            r = S.get(url, params=params, timeout=20)
            if r.status_code == 200:
                return r.json()
            time.sleep(1 + i)
        except Exception:  # noqa: BLE001
            time.sleep(1 + i)
    return None


def universe():
    out, offset = [], 0
    while offset < 20000:
        d = get(f"{GAMMA}/markets", {"active": "true", "closed": "false", "limit": 500, "offset": offset, "order": "volume24hr", "ascending": "false"})
        if not d:
            break
        out += d
        if len(d) < 500:
            break
        offset += 500
    return out


def book_top(token):
    b = get(f"{CLOB}/book", {"token_id": token})
    if not b:
        return None, None
    asks = sorted((float(x["price"]), float(x["size"])) for x in b.get("asks") or [])
    bids = sorted(((float(x["price"]), float(x["size"])) for x in b.get("bids") or []), reverse=True)
    return (asks[0] if asks else None), (bids[0] if bids else None)


pos = []
try:
    pos = [json.loads(l) for l in open(f"{D}/spike_positions.jsonl")]
except OSError:
    pass
traded_today = {(p["cid"], p["dir"]) for p in pos if now - p["ts"] < 86400}

mk = universe()
print(f"active markets {len(mk)}", flush=True)
cands = []
for m in mk:
    try:
        if float(m.get("liquidityNum") or 0) < MIN_LIQ:
            continue
        end = m.get("endDate") or ""
        from datetime import datetime, timezone
        end_ts = datetime.fromisoformat(end.replace("Z", "+00:00")).timestamp() if end else None
        if not end_ts or (end_ts - now) / 86400 < MIN_DAYS:
            continue
        ch = m.get("oneDayPriceChange"); last = m.get("lastTradePrice")
        if ch is None or last is None:
            continue
        ch = float(ch); last = float(last)
        toks = json.loads(m.get("clobTokenIds") or "[]")
        if len(toks) != 2:
            continue
        ref = last - ch
        if not (0.10 <= ref <= 0.90):
            continue
        if ch >= SPIKE:
            cands.append((m, "no_after_spike", toks[1], last, ref))      # Yes spiked: buy No
        elif ch <= -SPIKE:
            cands.append((m, "yes_after_dump", toks[0], last, ref))      # Yes dumped: buy Yes (control)
    except (ValueError, TypeError):
        continue
print(f"candidates {len(cands)}", flush=True)
new = 0
for m, direction, tok, last, ref in cands[:60]:
    cid = m["conditionId"]
    if (cid, direction) in traded_today:
        continue
    ask, bid = book_top(tok)
    if not ask or not (0.03 <= ask[0] <= 0.97) or ask[1] * ask[0] < 2:
        continue
    pos.append({"ts": int(now), "cid": cid, "slug": m.get("slug"), "q": (m.get("question") or "")[:90], "dir": direction, "token": tok,
                "yes_last": last, "yes_ref": round(ref, 4), "entry": ask[0], "shares": round(min(ask[1], SIZE / ask[0]), 2),
                "exit24": None, "exit24_ts": None, "result": None})
    new += 1
print(f"new paper positions {new}", flush=True)

# exits at 24 h and resolution
for p in pos:
    if p["exit24"] is None and now - p["ts"] >= 86400:
        ask, bid = book_top(p["token"])
        if bid:
            p["exit24"] = bid[0]; p["exit24_ts"] = int(now)
        elif now - p["ts"] >= 2 * 86400:
            p["exit24"] = 0.0; p["exit24_ts"] = int(now)   # no bid at all: assume worthless
    if p["result"] is None and now - p["ts"] >= 86400:
        ev = get(f"{GAMMA}/markets", {"condition_ids": p["cid"]})
        if ev:
            mm = ev[0]
            try:
                pr = [float(x) for x in json.loads(mm.get("outcomePrices") or "[]")]
                if mm.get("closed") and len(pr) == 2 and max(pr) >= 0.99:
                    idx = 1 if p["dir"] == "no_after_spike" else 0
                    p["result"] = 1 if pr[idx] > pr[1 - idx] else 0
            except (ValueError, TypeError):
                pass
with open(f"{D}/spike_positions.jsonl", "w") as fh:
    for p in pos:
        fh.write(json.dumps(p) + "\n")

rep = {"updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "positions": len(pos)}
for direction in ("no_after_spike", "yes_after_dump"):
    P = [p for p in pos if p["dir"] == direction]
    ex = [p for p in P if p["exit24"] is not None]; rs = [p for p in P if p["result"] is not None]
    rep[direction] = {"open": len(P), "with_24h_exit": len(ex),
                      "pnl24": round(sum(p["shares"] * (p["exit24"] - 0.01 - p["entry"]) for p in ex), 2), "staked24": round(sum(p["shares"] * p["entry"] for p in ex), 2),
                      "resolved": len(rs), "pnl_res": round(sum(p["shares"] * (p["result"] - p["entry"]) for p in rs), 2), "staked_res": round(sum(p["shares"] * p["entry"] for p in rs), 2)}
json.dump(rep, open(f"{D}/spike_report.json", "w"), indent=1)
print(json.dumps(rep))
