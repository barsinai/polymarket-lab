"""Paper market making for liquidity rewards. No money; real books and real trades.

Every hour (called from record_live.py with the fresh snapshot):
 1. Settle the previous hour's quotes: for each market quoted, fetch the real trades since
    then (data-api, taker side). A taker SELLING Yes at or below our bid (or BUYING No at or
    above 1 - bid) fills our bid; a taker BUYING Yes at or above our ask (or SELLING No at or
    below 1 - ask) fills our ask - up to our size. Fills update inventory and cash.
 2. Credit rewards for the hour while both quotes were resting: pool/24 * our score share.
 3. Value inventory at the current midpoint; settle positions of resolved markets at 0/1.
 4. Choose up to N markets (reward pool, not live, >5 days to end, mid 10-90c) and post new
    quotes (v2 from 11-02 00:55 UTC: >5 days to end, away from catalysts): bid = mid - 1c, ask = mid + 1c, size = max(min_size, 200) shares each side,
    skipping a side if inventory there is already over 3x size (risk limit).
State: data/paper_mm/state.json. Log: data/paper_mm/<day>/<HHMM>.json. Scoreboard: data/paper_mm/report.json
"""
import glob, json, os, sys, time
from datetime import datetime, timezone
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import collect  # noqa: E402

D = "data/paper_mm"
N_MARKETS, BASE_SIZE, OFFSET = 40, 200, 0.01
DATA_API = "https://data-api.polymarket.com"


def load_state():
    try:
        return json.load(open(f"{D}/state.json"))
    except (OSError, ValueError):
        return {"positions": {}, "cash": 0.0, "rewards": 0.0, "quotes": {}, "fills": 0, "hours": 0, "settled": {}}


def score(levels, mid, v, minsize, is_bid):
    s_ = 0.0
    for p, size in levels:
        s = 100 * ((mid - p) if is_bid else (p - mid))
        if 0 <= s < v and size >= minsize:
            s_ += ((v - s) / v) ** 2 * size
    return s_


def trades_since(cid, t0):
    out, offset = [], 0
    while offset <= 2000:
        b = collect.get(f"{DATA_API}/trades", {"market": cid, "limit": 500, "offset": offset, "takerOnly": "true"}, tries=3)
        if not b:
            break
        new = [t for t in b if float(t.get("timestamp") or 0) > t0]
        out += new
        if len(b) < 500 or len(new) < len(b):
            break
        offset += 500
    return out


def run(markets, raw_books, now):
    os.makedirs(D, exist_ok=True)
    st = load_state()
    rw = {}
    files = sorted(glob.glob("data/live/rewards/*.jsonl.gz"))
    if files:
        for m in collect.read_jsonl_gz(files[-1]):
            r = m.get("rewards") or {}
            rate = sum(x.get("rewards_daily_rate") or 0 for x in r.get("rates") or [])
            if rate > 0 and r.get("max_spread"):
                rw[m["condition_id"]] = (rate, float(r["max_spread"]), float(r.get("min_size") or 0))
    by_cid = {m.get("conditionId"): m for m in markets if m.get("conditionId")}
    log = {"ts": int(now), "fills": [], "rewards": 0.0, "quotes": []}

    # 1-2. settle last hour's quotes
    for cid, q in list(st["quotes"].items()):
        pos = st["positions"].setdefault(cid, {"yes": 0.0, "cost": 0.0, "q": q["question"], "id": q["id"]})
        left_b, left_a = q["size"] if q["bid"] else 0, q["size"] if q["ask"] else 0
        for t in sorted(trades_since(cid, q["ts"]), key=lambda t: float(t["timestamp"])):
            px, sz, side, oc = float(t["price"]), float(t["size"]), t.get("side"), int(t.get("outcomeIndex") or 0)
            yes_px = px if oc == 0 else 1 - px
            hits_bid = (oc == 0 and side == "SELL") or (oc == 1 and side == "BUY")
            hits_ask = (oc == 0 and side == "BUY") or (oc == 1 and side == "SELL")
            if hits_bid and left_b > 0 and yes_px <= q["bid"] + 1e-9:
                f = min(left_b, sz); left_b -= f
                pos["yes"] += f; st["cash"] -= f * q["bid"]; st["fills"] += 1
                log["fills"].append({"cid": cid, "side": "buy", "px": q["bid"], "size": f})
            elif hits_ask and left_a > 0 and yes_px >= q["ask"] - 1e-9:
                f = min(left_a, sz); left_a -= f
                pos["yes"] -= f; st["cash"] += f * q["ask"]; st["fills"] += 1
                log["fills"].append({"cid": cid, "side": "sell", "px": q["ask"], "size": f})
        if left_b > 0 and left_a > 0:  # both sides rested the whole hour (simplified): reward credit
            st["rewards"] += q["reward_per_hour"]; log["rewards"] += q["reward_per_hour"]
    st["quotes"] = {}

    # 3. value inventory; settle resolved markets
    mtm = 0.0
    for cid, pos in st["positions"].items():
        m = by_cid.get(cid)
        if m is not None:
            bb, ba = m.get("bestBid"), m.get("bestAsk")
            if bb and ba:
                pos["last_mid"] = (float(bb) + float(ba)) / 2
        if abs(pos["yes"]) > 1e-9 and m is None and cid not in st["settled"]:
            pos["pending_settle"] = True  # gone from open markets: settle when resolution is known
        mtm += pos["yes"] * pos.get("last_mid", 0.5)

    # settle positions whose market closed (look up the result on Gamma, as paper.score does)
    pend = [(cid, p) for cid, p in st["positions"].items() if p.get("pending_settle") and cid not in st["settled"]]
    for k in range(0, len(pend), 40):
        chunk = pend[k:k + 40]
        got = collect.get(f"{collect.GAMMA}/markets", [("id", p["id"]) for _, p in chunk] + [("closed", "true"), ("limit", 100)]) or []
        res = {}
        for m in got:
            pr = [float(x) for x in collect.as_list(m.get("outcomePrices")) or []]
            if m.get("closed") and len(pr) == 2 and max(pr) >= 0.99:
                res[str(m["id"])] = 1.0 if pr[0] > pr[1] else 0.0
        for cid, p in chunk:
            if p["id"] in res:
                st["cash"] += p["yes"] * res[p["id"]]
                log.setdefault("settled", []).append({"cid": cid, "yes": p["yes"], "payout": res[p["id"]]})
                p["yes"] = 0.0; p["pending_settle"] = False; st["settled"][cid] = res[p["id"]]
    mtm = sum(p["yes"] * p.get("last_mid", 0.5) for p in st["positions"].values())

    # 4. new quotes
    cands = []
    for m in markets:
        cid = m.get("conditionId")
        if cid not in rw:
            continue
        toks = collect.as_list(m.get("clobTokenIds"))
        b = raw_books.get(str(toks[0])) if toks else None
        if not b or not b.get("bids") or not b.get("asks"):
            continue
        bids = sorted(((float(x["price"]), float(x["size"])) for x in b["bids"]), reverse=True)
        asks = sorted((float(x["price"]), float(x["size"])) for x in b["asks"])
        mid = (bids[0][0] + asks[0][0]) / 2
        end = ts(m.get("endDate")); gst = ts(m.get("gameStartTime") or "")
        if not (0.10 < mid < 0.90) or (end and end - now < 5 * 86400) or (gst and gst - now < 6 * 3600):
            continue
        rate, v, minsize = rw[cid]
        if 100 * OFFSET >= v:
            continue
        comp_b, comp_a = score(bids, mid, v, minsize, True), score(asks, mid, v, minsize, False)
        comp = min(comp_b, comp_a) if min(comp_b, comp_a) > 0 else max(comp_b, comp_a) / 3
        size = max(minsize, BASE_SIZE)
        ours = ((v - 100 * OFFSET) / v) ** 2 * size
        rph = rate / 24 * ours / (ours + comp)
        cands.append((rph / (size * (1 - 2 * OFFSET)), cid, m, mid, size, rph))
    for _, cid, m, mid, size, rph in sorted(cands, key=lambda x: -x[0])[:N_MARKETS]:
        inv = st["positions"].get(cid, {}).get("yes", 0.0)
        q = {"id": str(m["id"]), "question": m.get("question"), "ts": int(now), "mid": mid, "size": size,
             "bid": round(mid - OFFSET, 3) if inv < 3 * size else None,
             "ask": round(mid + OFFSET, 3) if inv > -3 * size else None, "reward_per_hour": rph}
        st["quotes"][cid] = q
        log["quotes"].append({"cid": cid, **q})
    st["hours"] += 1
    equity = st["cash"] + mtm + st["rewards"]
    capital = sum(q["size"] * (1 - 2 * OFFSET) for q in st["quotes"].values())
    report = {"updated": datetime.fromtimestamp(now, timezone.utc).isoformat(), "hours": st["hours"], "fills": st["fills"],
              "rewards_earned": round(st["rewards"], 2), "trading_cash": round(st["cash"], 2),
              "inventory_value_at_mid": round(mtm, 2), "total_pnl": round(equity, 2),
              "markets_quoted_now": len(st["quotes"]), "capital_in_quotes_now": round(capital, 2),
              "open_positions": sum(1 for p in st["positions"].values() if abs(p["yes"]) > 1e-9)}
    d = datetime.fromtimestamp(now, timezone.utc)
    os.makedirs(f"{D}/{d:%Y-%m-%d}", exist_ok=True)
    json.dump(log, open(f"{D}/{d:%Y-%m-%d}/{d:%H%M}.json", "w"))
    json.dump(st, open(f"{D}/state.json", "w"))
    json.dump(report, open(f"{D}/report.json", "w"), indent=1)
    return report


def ts(s):
    if not s:
        return None
    s = s.replace(" ", "T").replace("Z", "+00:00")
    if s.endswith("+00"):
        s += ":00"
    try:
        return datetime.fromisoformat(s).timestamp()
    except ValueError:
        return None
