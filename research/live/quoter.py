"""Dry-run quoter: turns the paper market maker's decisions into the ORDERS a live bot would send,
validates them, diffs them against the orders it believes are open, and logs the result.
It never talks to the exchange: Broker.DRY only prints. (A real broker would implement the four
methods below with the official SDK; see LIVE_DESIGN.md. Not written until there is an account.)

Order mapping (makers only hold pUSD): our Yes BID at p  -> BUY Yes-token at p, size shares
                                       our Yes ASK at p  -> BUY No-token at (1 - p), size shares
Safety rules enforced here, before any order could exist:
  - STOP file in the working dir -> cancel-all, exit
  - daily NET loss (trading + estimated rewards, paper report, UTC day) below -LOSS_LIMIT -> cancel-all, stop
    (trading alone loses ~$200/day against ~$400/day of rewards: a trading-only limit would trip daily)
  - a book older than STALE_S -> cancel that market's orders
  - every order: price on the tick grid, 0 < price < 1, size >= max(5, rewards min size), post-only
Usage: MM_VARIANT=2cl python research/live/quoter.py          (one pass, after the paper tick)
"""
import glob, json, os, sys, time
from datetime import datetime, timezone
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import paper_mm2 as P  # noqa: E402

LOSS_LIMIT = float(os.environ.get("MM_LOSS_LIMIT", "150"))   # $ per UTC day, NET of estimated rewards (trading alone loses ~$200/day by design)
STALE_S = 120
LOG = f"{P.D}/orders"
os.makedirs(LOG, exist_ok=True)


class DryBroker:
    """Remembers what it 'sent' so the next pass can diff against it."""
    def __init__(self):
        self.p = f"{LOG}/open.json"
        try:
            self.open = json.load(open(self.p))
        except (OSError, ValueError):
            self.open = {}

    def open_orders(self):
        return self.open

    def post(self, key, order):
        self.open[key] = order

    def cancel(self, key):
        self.open.pop(key, None)

    def cancel_all(self):
        self.open = {}

    def flush(self):
        json.dump(self.open, open(self.p, "w"))


def desired_orders(st, rw):
    """From the paper state's quotes to exchange orders, validated."""
    out, rejected = {}, []
    for cid, q in st["quotes"].items():
        r = rw.get(cid)
        if not r:
            continue
        tick = r["tick"]
        minsize = max(5.0, r["minsize"]) if q.get("rpd") else 5.0   # exits only need the exchange minimum
        toks = r.get("tokens") or [r["token"], None]
        for side, px in (("bid", q["bid"]), ("ask", q["ask"])):
            if not px:
                continue
            size = round(float(q["size"]), 2)
            if side == "bid":
                tok, price = toks[0], px
            else:
                tok, price = toks[1], round(1 - px, 4)
            price = round(round(price / tick) * tick, 4)
            problems = []
            if not (0 < price < 1):
                problems.append("price out of range")
            if size < minsize:
                problems.append(f"size {size} < min {minsize}" + ("" if q.get("rpd") else " (exit: hold until it can be merged or resolves)"))
            if tok is None:
                problems.append("no token id for the No side")
            if problems:
                rejected.append({"cid": cid, "side": side, "price": price, "size": size, "why": problems})
                continue
            out[f"{cid}:{side}"] = {"token": tok, "side": "BUY", "price": price, "size": size, "post_only": True, "q": q["q"][:60]}
    return out, rejected


def main():
    now = time.time()
    broker = DryBroker()
    if os.path.exists("STOP"):
        broker.cancel_all(); broker.flush()
        print("STOP file present: cancelled everything, not quoting"); return
    st = P.load(); rw = P.rewards_table()
    rep = json.load(open(f"{P.D}/report.json"))
    # daily loss limit from the paper accounting (trading cash + inventory at mid, since the UTC day start)
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    ref_p = f"{LOG}/day_{day}.json"
    pnl_now = rep["trading_cash"] + rep["inventory_value_at_mid"] + rep.get("rewards_earned", 0) + rep.get("maker_rebates", 0)
    if not os.path.exists(ref_p):
        json.dump({"pnl_at_day_start": pnl_now}, open(ref_p, "w"))
    ref = json.load(open(ref_p))["pnl_at_day_start"]
    if pnl_now - ref < -LOSS_LIMIT:
        broker.cancel_all(); broker.flush()
        print(f"daily loss limit hit ({pnl_now - ref:.0f} < -{LOSS_LIMIT}): cancelled everything, not quoting"); return
    want, rejected = desired_orders(st, rw)
    have = broker.open_orders()
    stale = now - st.get("last_books_ts", now) > STALE_S
    cancels = [k for k in have if k not in want or have[k] != want[k] or stale]
    posts = {} if stale else {k: v for k, v in want.items() if k not in have or have[k] != v}
    for k in cancels:
        broker.cancel(k)
    for k, v in posts.items():
        broker.post(k, v)
    broker.flush()
    summary = {"ts": int(now), "variant": P.VARIANT, "open_after": len(broker.open), "cancels": len(cancels), "posts": len(posts),
               "rejected": rejected, "stale_books": stale, "notional_open": round(sum(o["price"] * o["size"] for o in broker.open.values()), 2),
               "day_pnl": round(pnl_now - ref, 2)}
    with open(f"{LOG}/{day}.jsonl", "a") as fh:
        fh.write(json.dumps({**summary, "posts": [posts[k] for k in list(posts)[:200]], "cancels": cancels[:200]}) + "\n")
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
