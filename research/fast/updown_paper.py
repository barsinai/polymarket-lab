"""Paper bot v4 for Polymarket's short "Up or Down" crypto markets (5 and 15 minutes, 8 assets). NO ORDERS.

Resolution (market description + 598 calibrated windows): Up iff the Chainlink 60-second TWAP at the END of the
window >= the "price to beat" (the same TWAP at the START). Polymarket broadcasts both the Chainlink price and
that TWAP on its public feed (research/fast/rtds.py), so the quantity the market resolves on is known exactly,
and in the last minute most of the final TWAP is already fixed.

Every ~2 s in the last LAST_S seconds of each window: read both order books; log an observation; paper-trade
under three rules, each settled on the market's real result (Gamma):
  exact  model probability (exact feed) beats the ask by EDGE after the taker fee (0.07*p*(1-p) per share)
  lock   last 60 s only: the outcome is locked beyond LOCK_Z standard deviations and the ask is <= LOCK_ASK
  fav    control: buy the market's favourite at FAV_LO..FAV_HI with <= FAV_REM s left (no model)
  dog    tape finding: buy the cheap side at DOG_LO..DOG_HI with DOG_RMIN..DOG_RMAX s left (no model)
  pair   15-minute + 5-minute windows ending together: one share of each right side pays >= $1 (see below)
Model: final TWAP = g*A + (1-g)*M, A = mean of Chainlink prices in [end-60, now], g = share of the last minute
elapsed, M ~ Normal(S, sigma^2 * r/3) (mean of a Brownian path over the remaining r seconds); before the last
minute: S ~ Normal(S_now, sigma^2 * (time until end-60 + 20)). sigma = 1 s Chainlink log-return std (15 min).
Falls back to Binance (1 s REST) for assets without a Chainlink feed.
Output: data/fast/obs.jsonl, trades.jsonl, windows.jsonl, report.json; feed in data/fast/rtds/.
"""
import json, math, os, sys, time, threading
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(os.path.dirname(HERE), "live"))
try:
    import netprefs  # noqa: F401  (IPv6 for *.polymarket.com on the Finnish server)
except Exception:  # noqa: BLE001
    pass
import rtds  # noqa: E402

D = os.environ.get("FAST_DIR", "data/fast"); os.makedirs(D, exist_ok=True)
RUN_MIN = float(os.environ.get("RUN_MIN", "60"))
LAST_S = int(os.environ.get("LAST_S", "120"))
EDGE = float(os.environ.get("EDGE", "0.03"))
SIZE_USD = float(os.environ.get("SIZE_USD", "20"))
LOCK_Z, LOCK_ASK = float(os.environ.get("LOCK_Z", "2.5")), float(os.environ.get("LOCK_ASK", "0.97"))
PAIR_EDGE, PAIR_MAX = float(os.environ.get("PAIR_EDGE", "0.03")), float(os.environ.get("PAIR_MAX", "1.15"))
DOG_LO, DOG_HI, DOG_RMIN, DOG_RMAX = float(os.environ.get("DOG_LO", "0.05")), float(os.environ.get("DOG_HI", "0.35")), int(os.environ.get("DOG_RMIN", "30")), int(os.environ.get("DOG_RMAX", "120"))
FAV_REM, FAV_LO, FAV_HI = int(os.environ.get("FAV_REM", "90")), float(os.environ.get("FAV_LO", "0.60")), float(os.environ.get("FAV_HI", "0.95"))
ASSETS = {"btc": "BTCUSDT", "eth": "ETHUSDT", "sol": "SOLUSDT", "xrp": "XRPUSDT", "doge": "DOGEUSDT", "bnb": "BNBUSDT",
          "hype": "HYPEUSDT", "zec": "ZECUSDT"}
WINDOWS = (300, 900)
GAMMA, CLOB = "https://gamma-api.polymarket.com", "https://clob.polymarket.com"
S = requests.Session(); S.headers["User-Agent"] = "polymarket-lab-research/0.1"
px = {a: deque(maxlen=1500) for a in ASSETS}          # Binance proxy (ts, price), last ~25 min
CL, TW = "crypto_prices_chainlink", "crypto_prices_twap_sixty"


def binance_price(a):
    try:
        return float(S.get("https://api.binance.com/api/v3/ticker/price", params={"symbol": ASSETS[a]}, timeout=3).json()["price"])
    except Exception:  # noqa: BLE001
        return None


def sampler(stop):
    while not stop.is_set():
        t = time.time()
        for a in ASSETS:
            p = binance_price(a)
            if p:
                px[a].append((t, p))
        time.sleep(max(0.0, 1.0 - (time.time() - t)))


def feed(a):
    """(source, [(ts, price)]) for the last 20 minutes: Chainlink when the feed has it, else Binance"""
    now = time.time()
    cl = rtds.series(CL, f"{a}/usd", now - 1200, now + 5)
    if len(cl) >= 120 and now - cl[-1][0] < 10:
        return "chainlink", cl
    return "binance", [(t, p) for t, p in px[a] if t >= now - 1200]


def sigma_of(ser):
    v = [p for _, p in ser]
    if len(v) < 120:
        return None
    r = [math.log(b / x) for x, b in zip(v, v[1:]) if x > 0 and b > 0]
    dt = (ser[-1][0] - ser[0][0]) / max(len(r), 1)
    m = sum(r) / len(r)
    return math.sqrt(sum((x - m) ** 2 for x in r) / (len(r) - 1)) / math.sqrt(max(dt, 0.2))  # per 1 s


def phi(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


meta = {}


def market(a, w, start):
    """tokens + the official price to beat (Gamma eventMetadata.priceToBeat, re-read once if missing)"""
    slug = f"{a}-updown-{w // 60}m-{start}"
    cur = meta.get(slug)
    if cur is not None and (cur.get("ptb") is not None or cur.get("tries", 0) >= 2):
        return cur
    if slug in meta and cur is None:
        return None
    try:
        ev = S.get(f"{GAMMA}/events", params={"slug": slug}, timeout=10).json()
        m = ev[0]["markets"][0]
        ptb = (ev[0].get("eventMetadata") or {}).get("priceToBeat")
        meta[slug] = {"tokens": json.loads(m["clobTokenIds"]), "cid": m["conditionId"], "slug": slug,
                      "ptb": float(ptb) if ptb else None, "tries": (cur or {}).get("tries", 0) + 1}
    except Exception:  # noqa: BLE001
        if cur is None:
            meta[slug] = None
    return meta[slug]


def book(tok):
    try:
        b = S.get(f"{CLOB}/book", params={"token_id": tok}, timeout=4).json()
        asks = sorted((float(x["price"]), float(x["size"])) for x in b.get("asks") or [])
        bids = sorted(((float(x["price"]), float(x["size"])) for x in b.get("bids") or []), reverse=True)
        return (asks[0] if asks else None), (bids[0] if bids else None)
    except Exception:  # noqa: BLE001
        return None, None


def settle(trades):
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


def twap_at(a, ts, tol=4.0):
    """feed TWAP value at the first message with timestamp >= ts (within tol seconds), else None"""
    pts = rtds.series(TW, f"{a}/usd", ts, ts + tol)
    return pts[0][1] if pts else None


def write_trades(trades):
    with open(f"{D}/trades.jsonl", "w") as fh:
        for x in trades:
            fh.write(json.dumps(x) + "\n")


def main():
    stop = threading.Event()
    threading.Thread(target=sampler, args=(stop,), daemon=True).start()
    rt_stop = rtds.start()
    try:
        trades = [t for t in (json.loads(l) for l in open(f"{D}/trades.jsonl")) if t.get("model") in ("v2", "v4")]
    except OSError:
        trades = []
    for t in trades:
        t.setdefault("strat", "v2")
    done = {(t["strat"], t["slug"], t["side"]) for t in trades}
    starts = {}   # (asset, w, start) -> {K, K_src, ...}
    pool = ThreadPoolExecutor(max_workers=8)
    end_at = time.time() + RUN_MIN * 60
    time.sleep(130)  # warm up sigma / feed
    print("feed", json.dumps(rtds.stats)[:300], flush=True)
    n_obs = 0
    while time.time() < end_at:
        loop_t = time.time()
        now = time.time()
        jobs = []
        for a in ASSETS:
            src, ser = feed(a)
            if len(ser) < 60:
                continue
            s_now = ser[-1][1]
            sg = sigma_of(ser)
            for w in WINDOWS:
                st = int(now // w * w); end = st + w
                key = (a, w, st)
                acc = starts.get(key)
                if acc is None:
                    m = market(a, w, st)
                    if not m:
                        continue
                    kt = twap_at(a, st)
                    pre = [p for t, p in ser if st - 60 <= t < st]
                    kp = sum(pre) / len(pre) if len(pre) >= 20 else None
                    K0 = m.get("ptb") or kt or kp
                    if K0 is None:
                        continue  # no reference yet (market() re-reads the price to beat once more)
                    acc = starts[key] = {"K": K0, "K_src": "ptb" if m.get("ptb") else "twap" if kt is not None else src,
                                         "K_twap": kt, "K_proxy": kp, "spot_start": s_now if now - st < 6 else None}
                rem = end - now
                if rem < 2 or not sg:
                    continue
                late = rem <= LAST_S
                if not late and now - acc.get("model_ts", 0) < 5:
                    continue  # outside the last LAST_S: model line every 5 s, no books
                m = market(a, w, st)
                if not m:
                    continue
                if m.get("ptb") and acc["K_src"] != "ptb":
                    acc["K"], acc["K_src"] = m["ptb"], "ptb"
                K = acc["K"]
                if now < end - 60:
                    sd = s_now * sg * math.sqrt((end - 60 - now) + 20.0)
                    z = (s_now - K) / max(sd, 1e-9); g = 0.0; A = None
                else:
                    lastm = [p for t, p in ser if end - 60 <= t <= now]
                    g = min(max((now - (end - 60)) / 60.0, 0.0), 1.0)
                    A = sum(lastm) / len(lastm) if lastm else s_now
                    r = max(end - now, 1.0)
                    sd = max((1 - g) * s_now * sg * math.sqrt(r / 3), 1e-9)
                    z = (g * A + (1 - g) * s_now - K) / sd
                p_up = min(max(phi(z), 0.001), 0.999)
                if not late:
                    acc["model_ts"] = now
                    with open(f"{D}/model.jsonl", "a") as fh:   # whole-window model track (for maker replays against the tape)
                        fh.write(json.dumps({"ts": round(now, 1), "slug": m["slug"], "p_up": round(p_up, 4), "z": round(z, 2), "rem": int(rem),
                                             "spot": s_now, "K": K, "k_src": acc["K_src"], "src": src, "sigma": round(sg, 7)}) + "\n")
                    continue
                jobs.append((a, w, st, end, rem, m, p_up, z, g, A, s_now, K, acc["K_src"], sg, src))
        books = list(pool.map(lambda j: (book(j[5]["tokens"][0]), book(j[5]["tokens"][1])), jobs)) if jobs else []
        new_trades = False
        for j, (b_up, b_dn) in zip(jobs, books):
            a, w, st, end, rem, m, p_up, z, g, A, s_now, K, k_src, sg, src = j
            for side, (ask, bid), p_side in (("Up", b_up, p_up), ("Down", b_dn, 1 - p_up)):
                if not ask:
                    continue
                zs = z if side == "Up" else -z
                with open(f"{D}/obs.jsonl", "a") as fh:
                    fh.write(json.dumps({"ts": round(now, 1), "slug": m["slug"], "side": side, "ask": ask[0], "ask_sz": ask[1],
                                         "bid": bid[0] if bid else None, "bid_sz": bid[1] if bid else None, "p_model": round(p_side, 4),
                                         "z": round(zs, 2), "rem": int(rem), "spot": s_now, "K": K, "k_src": k_src, "src": src,
                                         "g": round(g, 3), "A": A, "sigma": round(sg, 7), "v": 4}) + "\n")
                n_obs += 1
                a_px, a_sz = ask
                fee = 0.07 * a_px * (1 - a_px)
                edge = p_side - a_px - fee
                picks = []
                if edge >= EDGE and 0.02 <= a_px <= 0.98:
                    picks.append("exact")
                if rem <= 60 and zs >= LOCK_Z and a_px <= LOCK_ASK and k_src in ("ptb", "twap") and src == "chainlink":
                    picks.append("lock")
                if rem <= FAV_REM and FAV_LO <= a_px <= FAV_HI:
                    picks.append("fav")
                if DOG_RMIN <= rem <= DOG_RMAX and DOG_LO <= a_px <= DOG_HI:
                    picks.append("dog")   # tape finding (598 windows): the cheap side 30-120 s before the end is underpriced
                for strat in picks:
                    if (strat, m["slug"], side) in done:
                        continue
                    if strat != "exact" and any((strat, m["slug"], o) in done for o in ("Up", "Down")):
                        continue  # one side per window for lock/fav
                    shares = round(min(a_sz, SIZE_USD / a_px), 2)
                    if shares < 5:
                        continue
                    tr = {"ts": int(now), "slug": m["slug"], "asset": a, "window": w, "side": side, "price": a_px, "shares": shares,
                          "fee": round(fee * shares, 4), "p_model": round(p_side, 4), "z": round(zs, 2), "edge": round(edge, 4),
                          "rem_s": int(rem), "K": K, "k_src": k_src, "src": src, "spot": s_now, "model": "v4", "strat": strat,
                          "end": end, "result": None}
                    trades.append(tr); done.add((strat, m["slug"], side)); new_trades = True
                    print(f"{datetime.now(timezone.utc):%H:%M:%S} PAPER[{strat}] BUY {side} {m['slug']} @ {a_px} x {shares} p {p_side:.3f} z {zs:.1f} rem {int(rem)}s", flush=True)
        # PAIR: a 15-minute window and the 5-minute window that ends at the same second resolve off the SAME
        # final TWAP, compared with two different prices to beat. One share of each of the right sides pays
        # at least $1 and $2 when the final lands between the two references (0 violations in 132 pairs).
        seen = {}
        for j, bk in zip(jobs, books):
            seen[(j[0], j[1])] = (j, bk)
        for a in ASSETS:
            if (a, 900) not in seen or (a, 300) not in seen:
                continue
            (j15, (u15, d15)), (j5, (u5, d5)) = seen[(a, 900)], seen[(a, 300)]
            if j15[3] != j5[3] or not all((u15, d15, u5, d5)):
                continue  # must end at the same second, both books present
            k15, k5, p15, p5 = j15[11], j5[11], j15[6], j5[6]
            if k15 < k5:
                legs = (("Up", j15, u15[0]), ("Down", j5, d5[0])); p_mid = p15 - p5
            elif k15 > k5:
                legs = (("Down", j15, d15[0]), ("Up", j5, u5[0])); p_mid = p5 - p15
            else:
                continue
            a1, a2 = legs[0][2][0], legs[1][2][0]
            fees = 0.07 * a1 * (1 - a1) + 0.07 * a2 * (1 - a2)
            ev = 1 + max(p_mid, 0.0) - (a1 + a2) - fees
            with open(f"{D}/pairs.jsonl", "a") as fh:
                fh.write(json.dumps({"ts": round(now, 1), "asset": a, "end": j15[3], "rem": int(j15[4]), "k15": k15, "k5": k5,
                                     "legs": [(s_, jj[5]["slug"], ask_[0], ask_[1]) for s_, jj, ask_ in legs], "sum": round(a1 + a2, 3),
                                     "p_mid": round(p_mid, 4), "ev": round(ev, 4)}) + "\n")
            key = ("pair", j15[5]["slug"], "both")
            if ev >= PAIR_EDGE and a1 + a2 <= PAIR_MAX and key not in done:
                shares = round(min(legs[0][2][1], legs[1][2][1], SIZE_USD / (a1 + a2)), 2)
                if shares < 5:
                    continue
                done.add(key); new_trades = True
                for s_, jj, ask_ in legs:
                    fee = 0.07 * ask_[0] * (1 - ask_[0])
                    trades.append({"ts": int(now), "slug": jj[5]["slug"], "asset": a, "window": jj[1], "side": s_, "price": ask_[0], "shares": shares,
                                   "fee": round(fee * shares, 4), "p_model": round(jj[6] if s_ == "Up" else 1 - jj[6], 4), "edge": round(ev, 4),
                                   "rem_s": int(jj[4]), "K": jj[11], "k_src": jj[12], "src": jj[14], "spot": jj[10], "model": "v4", "strat": "pair",
                                   "pair": j15[5]["slug"], "p_mid": round(p_mid, 4), "end": jj[3], "result": None})
                print(f"{datetime.now(timezone.utc):%H:%M:%S} PAPER[pair] {a} {legs[0][0]}15m@{a1} + {legs[1][0]}5m@{a2} x {shares} sum {a1 + a2:.2f} p_mid {p_mid:.2f} ev {ev:+.3f} rem {int(j15[4])}s", flush=True)
        if new_trades or settle(trades):
            write_trades(trades)
        # window summaries, ~70 s after each window ends
        for (a_, w_, st_), acc_ in list(starts.items()):
            end_ = st_ + w_
            if acc_.get("logged") or now < end_ + 70:
                continue
            src_, ser_ = feed(a_)
            def mean_(lo, hi):
                v = [p for t, p in ser_ if lo <= t < hi]
                return round(sum(v) / len(v), 6) if v else None
            def at_(x):
                v = [p for t, p in ser_ if t >= x]
                return v[0] if v else None
            te = twap_at(a_, end_)
            rec = {"slug": f"{a_}-updown-{w_ // 60}m-{st_}", "asset": a_, "window": w_, "start": st_, "src": src_,
                   "K": acc_.get("K"), "K_src": acc_.get("K_src"), "K_twap": acc_.get("K_twap"), "K_proxy": acc_.get("K_proxy"), "twap_end": te,
                   "spot_start": acc_.get("spot_start"), "spot_end": at_(end_), "mean_window": mean_(st_, end_),
                   "mean_last60": mean_(end_ - 60, end_), "mean_pre60": mean_(st_ - 60, st_), "mean_first60": mean_(st_, st_ + 60),
                   "rule_twap": (te >= acc_["K_twap"]) if (te is not None and acc_.get("K_twap") is not None) else None, "v": 4}
            with open(f"{D}/windows.jsonl", "a") as fh:
                fh.write(json.dumps(rec) + "\n")
            acc_["logged"] = True
        starts = {k: v for k, v in starts.items() if k[2] + k[1] > now - 200}
        time.sleep(max(0.2, 2.0 - (time.time() - loop_t)))
    stop.set(); rt_stop.set()
    settle(trades); write_trades(trades)
    done_t = [t for t in trades if t.get("result") is not None]
    by_strat, by_day = {}, {}
    for t in done_t:
        for key, dct in ((t.get("strat", "v2"), by_strat), (datetime.fromtimestamp(t["ts"], timezone.utc).strftime("%Y-%m-%d") + " " + t.get("strat", "v2"), by_day)):
            b = dct.setdefault(key, {"trades": 0, "won": 0, "staked": 0.0, "pnl": 0.0})
            b["trades"] += 1; b["won"] += t["result"]; b["staked"] += t["price"] * t["shares"]; b["pnl"] += t["pnl"]
    rnd = lambda b: {k: round(v, 2) if isinstance(v, float) else v for k, v in b.items()}
    rep = {"updated": datetime.now(timezone.utc).isoformat(), "trades": len(trades), "settled": len(done_t), "obs_this_run": n_obs,
           "feed": {k: v for k, v in rtds.stats.items() if k != "topics"}, "feed_topics": rtds.stats.get("topics"),
           "by_strat": {k: rnd(b) for k, b in sorted(by_strat.items())}, "by_day": {d: rnd(b) for d, b in sorted(by_day.items())}}
    json.dump(rep, open(f"{D}/report.json", "w"), indent=1)
    print(json.dumps(rep), flush=True)


if __name__ == "__main__":
    main()
