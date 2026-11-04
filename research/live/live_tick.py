"""One tick of the pilot (every 10 minutes from .github/workflows/pilot.yml).

Modes (file research/live/PILOT_MODE):  off  - do nothing
                                        dry  - read the account, run the rules, sign-but-don't-post orders, log
                                        live - post-only orders are actually sent, within the hard limits below
Kill switch: a file named STOP in the repo root -> cancel every open order, do nothing else.
Hard limits (env, defaults): MM_CAPITAL (max $ in resting buy orders, default 95% of balance),
MM_MAX_MARKET ($150 per market), MM_LOSS_LIMIT ($30 net loss per UTC day -> cancel all, stop for the day).
The quoting rules are paper_mm2 variant "live" (= 2cl rules, 4 markets, minimum size); positions come
from the exchange, fills and rewards are read from the exchange, nothing is simulated.
Outputs: data/live_pilot/report.json, data/live_pilot/ticks/<day>.jsonl, data/live_pilot/ledger.jsonl
"""
import json, os, sys, time, traceback
from datetime import datetime, timezone, timedelta
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["MM_VARIANT"] = "live"
import paper_mm2 as P  # noqa: E402
from broker import Broker  # noqa: E402

OUT = "data/live_pilot"
os.makedirs(f"{OUT}/ticks", exist_ok=True)
MAX_MARKET = float(os.environ.get("MM_MAX_MARKET", "150"))
LOSS_LIMIT = float(os.environ.get("MM_LOSS_LIMIT", "30"))
now = time.time(); day = datetime.now(timezone.utc).strftime("%Y-%m-%d")


def mode():
    try:
        return open(f"{HERE}/PILOT_MODE").read().strip().lower()
    except OSError:
        return "off"


def jlog(obj):
    with open(f"{OUT}/ticks/{day}.jsonl", "a") as fh:
        fh.write(json.dumps(obj, default=str) + "\n")
    print(json.dumps(obj, default=str)[:1500], flush=True)


def ledger(rows):
    if rows:
        with open(f"{OUT}/ledger.jsonl", "a") as fh:
            for r in rows:
                fh.write(json.dumps(r, default=str) + "\n")


def main():
    m = mode()
    if m == "off":
        print("PILOT_MODE off"); return
    send = m == "live"
    b = Broker(send=send)
    if os.path.exists("STOP"):
        r = b.cancel_all(); jlog({"ts": int(now), "mode": m, "STOP": True, "cancel_all": r}); return
    bal = b.balance(); appr = b.ensure_approvals()
    pos = b.positions()
    red = b.redeem_resolved(); mrg = b.merge_complementary(pos)
    if red or mrg:
        pos = b.positions()
    pos_value = sum(p["value"] for p in pos.values())
    equity = bal["balance_usd"] + pos_value
    # daily loss limit on real equity
    ref_p = f"{OUT}/day_{day}.json"
    if not os.path.exists(ref_p):
        json.dump({"equity_at_day_start": equity, "ts": int(now)}, open(ref_p, "w"))
    ref = json.load(open(ref_p))
    day_pnl = equity - ref["equity_at_day_start"]
    if ref.get("stopped") or day_pnl < -LOSS_LIMIT:
        if not ref.get("stopped"):
            ref["stopped"] = int(now); json.dump(ref, open(ref_p, "w"))
        r = b.cancel_all()
        jlog({"ts": int(now), "mode": m, "loss_limit_stop": True, "day_pnl": round(day_pnl, 2), "equity": round(equity, 2), "cancel_all": r}); return

    # hand the exchange's positions to the rules, run one tick (no network orders inside)
    os.makedirs(P.D, exist_ok=True)
    json.dump({cid: {"yes": p["yes"], "token": next(iter(p["tokens"]), None), "q": p["q"]} for cid, p in pos.items()}, open(f"{P.D}/positions_live.json", "w"))
    rep = P.tick(now) or {}
    st = P.load(); rw = P.rewards_table()

    # desired orders
    cap = min(float(os.environ.get("MM_CAPITAL", "1e9")), bal["balance_usd"] * 0.95)
    want, rejected, spent = {}, [], 0.0
    quotes = sorted(st["quotes"].items(), key=lambda kv: -(kv[1].get("rpd") or 0))
    for cid, q in quotes:
        r = rw.get(cid)
        if not r:
            continue
        tick = r["tick"]; toks = r.get("tokens") or [r["token"], None]
        inv = st["positions"].get(cid, {}).get("yes", 0.0)
        orders = []
        if q.get("rpd"):  # reward quotes: buy Yes at bid, buy No at 1-ask
            if q.get("bid"):
                orders.append((toks[0], "BUY", q["bid"], q["size"]))
            if q.get("ask") and toks[1]:
                orders.append((toks[1], "BUY", round(1 - q["ask"], 4), q["size"]))
        else:  # exit: sell what we hold
            if inv > 0 and q.get("ask"):
                orders.append((toks[0], "SELL", q["ask"], abs(inv)))
            elif inv < 0 and q.get("bid") and toks[1]:
                orders.append((toks[1], "SELL", round(1 - q["bid"], 4), abs(inv)))
        mkt_notional = 0.0
        for tok, side, price, size in orders:
            price = round(round(price / tick) * tick, 4); size = round(float(size), 2)
            notional = price * size if side == "BUY" else 0.0
            why = []
            if not (0 < price < 1):
                why.append("price")
            if size < max(5.0, r["minsize"] if q.get("rpd") else 5.0):
                why.append(f"size {size} < min")
            if side == "BUY" and (spent + notional > cap or mkt_notional + notional > MAX_MARKET):
                why.append("capital cap")
            if why:
                rejected.append({"cid": cid[:10], "side": side, "price": price, "size": size, "why": why}); continue
            spent += notional; mkt_notional += notional
            want[f"{tok}:{side}"] = {"token": tok, "side": side, "price": price, "size": size, "cid": cid, "q": q["q"][:50]}

    # reconcile with the exchange
    open_ = b.open_orders()
    keep, cancel_ids, posts = set(), [], []
    by_key = {}
    for o in open_:
        by_key.setdefault(f"{o['token']}:{o['side']}", []).append(o)
    for k, w in want.items():
        matched = [o for o in by_key.get(k, []) if abs(o["price"] - w["price"]) < 1e-9 and o["remaining"] >= 0.8 * w["size"]]
        if matched:
            keep.add(matched[0]["id"])
        else:
            posts.append(w)
    for o in open_:
        if o["id"] not in keep:
            cancel_ids.append(o["id"])
    c = b.cancel(cancel_ids) if cancel_ids else {}
    results = []
    for w in posts:
        try:
            results.append({**{k: w[k] for k in ("side", "price", "size", "q")}, **b.post(w["token"], w["side"], w["price"], w["size"])})
        except Exception as e:  # noqa: BLE001
            results.append({**{k: w[k] for k in ("side", "price", "size", "q")}, "ok": False, "error": str(e)[:200]})
    # ledger: real fills since the last tick, and yesterday's rewards once a day
    last_p = f"{OUT}/last_ts.json"
    last = json.load(open(last_p))["ts"] if os.path.exists(last_p) else now - 3600
    fills = b.trades_since(last)
    ledger([{"kind": "fill", **f} for f in fills])
    json.dump({"ts": now}, open(last_p, "w"))
    yday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
    earn_p = f"{OUT}/earnings_{yday}.json"
    earned = None
    if not os.path.exists(earn_p):
        try:
            earned = b.earnings(yday); earned["rebates"] = b.rebates(yday)
            json.dump(earned, open(earn_p, "w")); ledger([{"kind": "rewards", **earned}])
        except Exception as e:  # noqa: BLE001
            earned = {"error": str(e)[:200]}
    report = {"updated": datetime.now(timezone.utc).isoformat(), "mode": m, "wallet_type": b.wallet_type, "balance_usd": round(bal["balance_usd"], 2),
              "positions": len(pos), "positions_value": round(pos_value, 2), "equity": round(equity, 2), "day_pnl": round(day_pnl, 2),
              "approvals": appr, "open_orders_before": len(open_), "kept": len(keep), "cancelled": len(cancel_ids), "posted": len(posts),
              "post_results": results[:40], "rejected": rejected[:20], "resting_notional": round(spent, 2), "capital_cap": round(cap, 2),
              "fills_since_last": len(fills), "paper_estimate": {k: rep.get(k) for k in ("quoting", "capital_in_use")}, "redeemed": red, "merged": mrg,
              "earnings_yesterday": earned, "sample_position": getattr(b, "sample_position", None), "sample_open_order": (open_ or [None])[0]}
    json.dump(report, open(f"{OUT}/report.json", "w"), indent=1, default=str)
    jlog({"ts": int(now), **{k: v for k, v in report.items() if k not in ("post_results", "rejected")}, "posts": len(results), "cancel": c})


if __name__ == "__main__":
    try:
        main()
    except Exception:  # noqa: BLE001
        err = traceback.format_exc()
        for k in ("POLYMARKET_PRIVATE_KEY", "POLYMARKET_RELAYER_API_KEY"):
            v = os.environ.get(k)
            if v:
                err = err.replace(v, "***")
        jlog({"ts": int(now), "error": err[-1500:]})
        sys.exit(1)
