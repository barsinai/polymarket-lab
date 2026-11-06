"""Paper bot for Polymarket's short "Up or Down" crypto markets (BTC/ETH, 5 and 15 minutes). NO ORDERS.

Resolution: Up if the Chainlink TWAP of the window >= the price at the window's start. Late in a window most
of the average is already fixed, so the outcome becomes predictable from the exchange price.

Every second: BTC/ETH price (Binance, Coinbase fallback). Per active window: start price K (first price we
saw at/after the start), running mean A of our 1-second prices, elapsed fraction f.
Model: final avg = f*A + (1-f)*M, M ~ Normal(S, sigma^2 * T_rem / 3)   (mean of Brownian motion over T_rem)
       P(Up) = Phi((f*A + (1-f)*S - K) / ((1-f) * sigma * sqrt(T_rem / 3)))      sigma from the last 15 min.
Every 3 s in the last LAST_S seconds: read both order books; a paper trade when the model's probability
beats the best ask by EDGE after the taker fee (crypto: 0.07 * p * (1 - p) per share), up to SIZE_USD per
window and side, at the displayed size. Settled on the market's actual result (Gamma), so model errors
(our price vs Chainlink's) show up as losses. Output: data/fast/trades.jsonl, data/fast/report.json.
"""
import json, math, os, sys, time, threading
from collections import deque
from datetime import datetime, timezone
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "live"))
try:
    import netprefs  # noqa: F401  (IPv6 for *.polymarket.com on the Finnish server)
except Exception:  # noqa: BLE001
    pass

D = "data/fast"; os.makedirs(D, exist_ok=True)
RUN_MIN = float(os.environ.get("RUN_MIN", "60"))
LAST_S = int(os.environ.get("LAST_S", "150"))
EDGE = float(os.environ.get("EDGE", "0.03"))
SIZE_USD = float(os.environ.get("SIZE_USD", "20"))
ASSETS = {"btc": ("BTCUSDT", "BTC-USD"), "eth": ("ETHUSDT", "ETH-USD")}
WINDOWS = (300, 900)
GAMMA, CLOB = "https://gamma-api.polymarket.com", "https://clob.polymarket.com"
S = requests.Session(); S.headers["User-Agent"] = "polymarket-lab-research/0.1"
px = {a: deque(maxlen=1200) for a in ASSETS}          # (ts, price) last 20 min


def price(a):
    bsym, csym = ASSETS[a]
    try:
        return float(S.get("https://api.binance.com/api/v3/ticker/price", params={"symbol": bsym}, timeout=3).json()["price"])
    except Exception:  # noqa: BLE001
        try:
            return float(S.get(f"https://api.exchange.coinbase.com/products/{csym}/ticker", timeout=3).json()["price"])
        except Exception:  # noqa: BLE001
            return None


def sampler(stop):
    while not stop.is_set():
        t = time.time()
        for a in ASSETS:
            p = price(a)
            if p:
                px[a].append((t, p))
        time.sleep(max(0.0, 1.0 - (time.time() - t)))


def sigma(a):
    v = [p for _, p in px[a]]
    if len(v) < 120:
        return None
    r = [math.log(b / x) for x, b in zip(v, v[1:])]
    m = sum(r) / len(r)
    return math.sqrt(sum((x - m) ** 2 for x in r) / (len(r) - 1))  # per ~1 s


def phi(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


meta = {}  # slug -> {tokens:[up,down], cid}


def market(a, w, start):
    slug = f"{a}-updown-{w // 60}m-{start}"
    if slug in meta:
        return meta[slug]
    try:
        ev = S.get(f"{GAMMA}/events", params={"slug": slug}, timeout=10).json()
        m = ev[0]["markets"][0]
        meta[slug] = {"tokens": json.loads(m["clobTokenIds"]), "cid": m["conditionId"], "slug": slug}
    except Exception:  # noqa: BLE001
        meta[slug] = None
    return meta[slug]


def best_ask(tok):
    try:
        b = S.get(f"{CLOB}/book", params={"token_id": tok}, timeout=4).json()
        asks = sorted((float(x["price"]), float(x["size"])) for x in b.get("asks") or [])
        bids = sorted(((float(x["price"]), float(x["size"])) for x in b.get("bids") or []), reverse=True)
        return (asks[0] if asks else None), (bids[0] if bids else None)
    except Exception:  # noqa: BLE001
        return None, None


def settle(trades):
    """fill in outcome for trades whose window has ended (Gamma outcomePrices once closed)"""
    changed = False
    for t in trades:
        if t.get("result") is not None or time.time() < t["end"] + 90:
            continue
        try:
            m = S.get(f"{GAMMA}/events", params={"slug": t["slug"]}, timeout=10).json()[0]["markets"][0]
            pr = [float(x) for x in json.loads(m["outcomePrices"])]
            if max(pr) >= 0.99:
                up_won = pr[0] > pr[1]
                won = up_won if t["side"] == "Up" else not up_won
                t["result"] = 1 if won else 0
                t["pnl"] = round(t["shares"] * (t["result"] - t["price"]) - t["fee"], 4)
                changed = True
        except Exception:  # noqa: BLE001
            pass
    return changed


def main():
    stop = threading.Event()
    threading.Thread(target=sampler, args=(stop,), daemon=True).start()
    try:
        trades = [json.loads(l) for l in open(f"{D}/trades.jsonl")]
    except OSError:
        trades = []
    done = {(t["slug"], t["side"]) for t in trades}
    starts = {}   # (asset, w, start) -> [K, sum, n]
    end_at = time.time() + RUN_MIN * 60
    time.sleep(130)  # warm up sigma
    while time.time() < end_at:
        now = time.time()
        for a in ASSETS:
            if not px[a]:
                continue
            t_last, s_now = px[a][-1]
            for w in WINDOWS:
                st = int(now // w * w); end = st + w
                key = (a, w, st)
                acc = starts.get(key)
                if acc is None:
                    first = [p for t, p in px[a] if t >= st]
                    if not first or first and [t for t, _ in px[a] if t >= st][0] - st > 3:
                        continue  # we did not see the start: no reliable K
                    acc = starts[key] = {"K": first[0], "sum": 0.0, "n": 0, "last": st}
                for t, p in px[a]:
                    if t > acc["last"]:
                        acc["sum"] += p; acc["n"] += 1; acc["last"] = t
                rem = end - now
                if rem > LAST_S or rem < 5 or acc["n"] < 10:
                    continue
                sg = sigma(a)
                if not sg:
                    continue
                f = (now - st) / w; A = acc["sum"] / acc["n"]
                sd = (1 - f) * s_now * sg * math.sqrt(max(rem, 1) / 3)
                z = (f * A + (1 - f) * s_now - acc["K"]) / max(sd, 1e-9)
                p_up = min(max(phi(z), 0.001), 0.999)
                m = market(a, w, st)
                if not m:
                    continue
                for side, tok, p_side in (("Up", m["tokens"][0], p_up), ("Down", m["tokens"][1], 1 - p_up)):
                    if (m["slug"], side) in done:
                        continue
                    ask, bid = best_ask(tok)
                    if not ask:
                        continue
                    a_px, a_sz = ask
                    fee = 0.07 * a_px * (1 - a_px)
                    edge = p_side - a_px - fee
                    if edge >= EDGE and 0.02 <= a_px <= 0.98:
                        shares = round(min(a_sz, SIZE_USD / a_px), 2)
                        if shares < 5:
                            continue
                        tr = {"ts": int(now), "slug": m["slug"], "asset": a, "window": w, "side": side, "price": a_px, "shares": shares,
                              "fee": round(fee * shares, 4), "p_model": round(p_side, 4), "edge": round(edge, 4), "rem_s": int(rem),
                              "K": acc["K"], "avg": round(A, 2), "spot": s_now, "end": end, "result": None}
                        trades.append(tr); done.add((m["slug"], side))
                        with open(f"{D}/trades.jsonl", "w") as fh:
                            for x in trades:
                                fh.write(json.dumps(x) + "\n")
                        print(f"{datetime.now(timezone.utc):%H:%M:%S} PAPER BUY {side} {m['slug']} @ {a_px} x {shares} model {p_side:.3f} edge {edge:.3f} rem {int(rem)}s", flush=True)
        if settle(trades):
            with open(f"{D}/trades.jsonl", "w") as fh:
                for x in trades:
                    fh.write(json.dumps(x) + "\n")
        # window summaries for calibrating the resolution rule: written once, ~70 s after each window ends
        for (a_, w_, st_), acc_ in list(starts.items()):
            end_ = st_ + w_
            if acc_.get("logged") or now < end_ + 70:
                continue
            ser = [(t, p) for t, p in px[a_] if st_ - 120 <= t <= end_ + 60]
            def mean_(lo, hi):
                v = [p for t, p in ser if lo <= t < hi]
                return round(sum(v) / len(v), 4) if v else None
            def at_(x):
                v = [p for t, p in ser if t >= x]
                return v[0] if v else None
            rec = {"slug": f"{a_}-updown-{w_ // 60}m-{st_}", "asset": a_, "window": w_, "start": st_,
                   "spot_start": at_(st_), "spot_end": at_(end_), "mean_window": mean_(st_, end_),
                   "mean_last60": mean_(end_ - 60, end_), "mean_pre60": mean_(st_ - 60, st_), "mean_first60": mean_(st_, st_ + 60), "result": None}
            with open(f"{D}/windows.jsonl", "a") as fh:
                fh.write(json.dumps(rec) + "\n")
            acc_["logged"] = True
        starts = {k: v for k, v in starts.items() if k[2] + k[1] > now - 200}
        time.sleep(3)
    stop.set()
    settle(trades)
    with open(f"{D}/trades.jsonl", "w") as fh:
        for x in trades:
            fh.write(json.dumps(x) + "\n")
    done_t = [t for t in trades if t.get("result") is not None]
    by_day = {}
    for t in done_t:
        d = datetime.fromtimestamp(t["ts"], timezone.utc).strftime("%Y-%m-%d")
        b = by_day.setdefault(d, {"trades": 0, "won": 0, "staked": 0.0, "pnl": 0.0})
        b["trades"] += 1; b["won"] += t["result"]; b["staked"] += t["price"] * t["shares"]; b["pnl"] += t["pnl"]
    rep = {"updated": datetime.now(timezone.utc).isoformat(), "trades": len(trades), "settled": len(done_t),
           "win_rate": round(sum(t["result"] for t in done_t) / len(done_t), 3) if done_t else None,
           "avg_price": round(sum(t["price"] for t in done_t) / len(done_t), 3) if done_t else None,
           "pnl_usd": round(sum(t["pnl"] for t in done_t), 2), "staked_usd": round(sum(t["price"] * t["shares"] for t in done_t), 2),
           "by_day": {d: {k: round(v, 2) if isinstance(v, float) else v for k, v in b.items()} for d, b in sorted(by_day.items())}}
    json.dump(rep, open(f"{D}/report.json", "w"), indent=1)
    print(json.dumps(rep), flush=True)


if __name__ == "__main__":
    main()
