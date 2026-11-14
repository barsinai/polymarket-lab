"""Taker 'entries' from the public trade tape, for a wallet-skill and follow-the-sharp-takers study (read-only, 11-14).

Finding that started this (tape_census.py, 6 weeks, 15k markets): on Polymarket the MAKERS lose to the takers in most slow
categories (weather -0.9% of taker volume [-1.4, -0.4], youtube -3.8%, movies -1.9%, mention pre-event -2.2%), and the takers who
won in the first half kept winning in the second (top quarter by first-half return: +6..7% after fees out of sample, 4 categories).
This script collects what a walk-forward test of 'follow those wallets' needs, for many more markets and 12 weeks:
one row per (wallet, market, direction): time and price of the wallet's FIRST taker trade that way, its total shares / cost / fees
that way before the scheduled end, and the price of the next print the same way by someone else >= 60 s and >= 300 s later (a
price a follower could really have had). Direction +1 = towards YES (buy YES or sell NO), -1 = towards NO; every taker trade is
booked as buying the token of its direction at the ask-equivalent price (buy: p, sell: 1 - p).
Env GROUP = a (culture) | b (weather) | c (politics / economy / tech). Output data/research/entries_<group>.bin.gz + _meta.json.gz"""
import json, time, gzip, os, hashlib, collections, threading, datetime as dt, struct, bisect
from concurrent.futures import ThreadPoolExecutor
import requests

G = "https://gamma-api.polymarket.com"; DA = "https://data-api.polymarket.com"
T0 = time.time(); T_MAX = float(os.environ.get("T_MAX", "2900")); WEEKS = int(os.environ.get("WEEKS", "12")); GROUP = os.environ.get("GROUP", "a")
MAXPAGES = 40
PLANS = {"a": [("mention-markets", "mention", 1), ("earnings-calls", "mention", 1), ("mrbeast", "youtube", 1), ("youtube", "youtube", 1),
               ("movies", "movies", 1), ("music", "music", 1), ("awards", "awards", 1), ("pop-culture", "pop-culture", 1)],
         "b": [("weather", "weather", 3)],
         "c": [("economy", "economy", 1), ("ai", "ai/tech", 1), ("tech", "ai/tech", 1), ("geopolitics", "geopolitics", 1), ("politics", "politics", 4)]}
PLAN = PLANS[GROUP]
ROW = struct.Struct("<IIIhfffHHHIB")
ROW2 = struct.Struct("<IIIhffHHHHHIffB")     # big taker orders (>= $100)
tl = threading.local(); lock = threading.Lock(); nxt = [0.0]; n429 = [0]


def sess():
    if not hasattr(tl, "s"):
        tl.s = requests.Session(); tl.s.headers["User-Agent"] = "polymarket-lab-research/0.1"
    return tl.s


def get(url, params, tries=5, pace=0.07):
    for k in range(tries):
        with lock:
            w = nxt[0] - time.time(); nxt[0] = max(nxt[0], time.time()) + pace
        if w > 0:
            time.sleep(w)
        try:
            r = sess().get(url, params=params, timeout=40)
            if r.status_code == 429:
                n429[0] += 1; time.sleep(2.0 * (k + 1)); continue
            if r.status_code != 200:
                return None
            return r.json()
        except Exception:  # noqa: BLE001
            time.sleep(1 + k)
    return None


def trades(cid):
    out = []; cur = None
    for _ in range(MAXPAGES):
        p = {"condition_id": cid, "limit": 500}
        if cur:
            p["cursor"] = cur
        d = get(f"{DA}/v2/trades", p)
        rows = (d or {}).get("data") if isinstance(d, dict) else None
        if not rows:
            return out, False
        out += rows
        pg = d.get("pagination") or {}
        if not pg.get("has_more") or not pg.get("next_cursor"):
            return out, False
        cur = pg["next_cursor"]
    return out, True


def ts(s):
    try:
        return dt.datetime.fromisoformat(str(s).replace(" ", "T").replace("Z", "+00:00").replace("+00+00:00", "+00:00")).timestamp()
    except Exception:  # noqa: BLE001
        try:
            return dt.datetime.fromisoformat(str(s)[:19]).replace(tzinfo=dt.timezone.utc).timestamp()
        except Exception:  # noqa: BLE001
            return None


def process(m):
    if m["vol"] > 3e6:                                         # would hit the page cap anyway (truncated tapes are not used)
        return m, None, None, 0, True
    rows, trunc = trades(m["cid"])
    if not rows or trunc:
        return m, None, None, len(rows), trunc
    # fills -> taker ORDERS (one transaction of one wallet one way): shares, cost, worst fill price, fee
    od = {}
    for r in rows:
        try:
            p = float(r["price"]); s = float(r["size"]); oi = int(r["outcome_index"]); t = float(r["timestamp"]); buy = r["side"] == "BUY"
        except Exception:  # noqa: BLE001
            continue
        w = r.get("proxy_wallet") or ""
        if not (0 < p < 1) or s <= 0 or not w:
            continue
        d = 1 if (buy and oi == 0) or ((not buy) and oi == 1) else -1
        a = p if buy else 1 - p
        k = (r.get("transaction_hash") or t, w, d)
        o = od.get(k)
        if o is None:
            od[k] = [t, w, d, s, a * s, a, m["fee"] * p * (1 - p) * s]
        else:
            o[3] += s; o[4] += a * s; o[5] = max(o[5], a); o[6] += m["fee"] * p * (1 - p) * s
    T = sorted(od.values())
    seq = {1: ([], [], []), -1: ([], [], [])}                  # per direction: times, average prices, wallets
    for t, w, d, s, c, amax, f in T:
        seq[d][0].append(t); seq[d][1].append(c / s); seq[d][2].append(w)

    def nxt(t, w, d, delay):
        ts_, ps_, ws_ = seq[d]
        i = bisect.bisect_left(ts_, t + delay)
        while i < len(ts_) and ts_[i] <= t + 6 * 3600:
            if ws_[i] != w:
                return ps_[i], ts_[i] - t
            i += 1
        return 0.0, 0

    def prev(t, w, d):
        ts_, ps_, ws_ = seq[d]
        i = bisect.bisect_left(ts_, t) - 1
        while i >= 0 and ts_[i] >= t - 24 * 3600:
            if ws_[i] != w:
                return ps_[i]
            i -= 1
        return 0.0

    ent = {}; pre_cut = m["end"] - 3600; big = []; vol = 0.0; cum = collections.defaultdict(float)
    for t, w, d, s, c, amax, f in T:
        ywin = m["y0"] if d == 1 else 1 - m["y0"]
        fl = (1 if d == 1 else 0) | (2 if ywin >= 0.5 else 0)
        hb = max(-32000, min(32000, int((m["end"] - t) / 3600)))
        if c >= 100:                                           # a 'big' taker order
            a60, lag = nxt(t, w, d, 60); a300, _ = nxt(t, w, d, 300)
            big.append((int(t), w, hb, c, s, c / s, amax, prev(t, w, d), a60, a300, int(lag), vol, cum[(w, d)], fl))
        vol += c; cum[(w, d)] += c
        e = ent.get((w, d))
        if e is None:
            ent[(w, d)] = [t, c / s, s, c, f, t <= pre_cut]
        elif not (e[5] and t > pre_cut):                       # an entry opened before the event ignores the wallet's later live trades
            e[2] += s; e[3] += c; e[4] += f
    out = []
    for (w, d), (t, a, S, C, F, _pre) in ent.items():
        a60, lag = nxt(t, w, d, 60); a300, _ = nxt(t, w, d, 300)
        ywin = m["y0"] if d == 1 else 1 - m["y0"]
        out.append((int(t), w, max(-32000, min(32000, int((m["end"] - t) / 3600))), S, C, F, a, a60, a300, int(lag), (1 if d == 1 else 0) | (2 if ywin >= 0.5 else 0)))
    return m, out, big, len(rows), trunc


now = dt.datetime.now(dt.timezone.utc)
seen_ev = set(); todo = []; ev_n = collections.Counter()
for w in range(1, WEEKS + 1):                                  # newest weeks first: a time-out drops the oldest
    a = now - dt.timedelta(days=7 * w + 3); b = now - dt.timedelta(days=7 * (w - 1) + 3)
    for tag, cat, den in PLAN:
        for off in range(0, 2000, 100):
            page = get(f"{G}/events", {"tag_slug": tag, "closed": "true", "limit": 100, "offset": off,
                                       "end_date_min": a.strftime("%Y-%m-%dT%H:%M:%SZ"), "end_date_max": b.strftime("%Y-%m-%dT%H:%M:%SZ")}, pace=0.25)
            if not page:
                break
            for e in page:
                if e.get("id") in seen_ev:
                    continue
                seen_ev.add(e.get("id"))
                if int(hashlib.md5(str(e.get("id")).encode()).hexdigest(), 16) % den:
                    continue
                ev_n[cat] += 1
                for m in e.get("markets") or []:
                    try:
                        pr = [float(x) for x in json.loads(m.get("outcomePrices") or "[]")]
                        tk = json.loads(m.get("clobTokenIds") or "[]")
                    except Exception:  # noqa: BLE001
                        continue
                    if not m.get("closed") or len(pr) != 2 or len(tk) != 2 or not m.get("conditionId"):
                        continue
                    if not ((pr[0] >= 0.99 and pr[1] <= 0.01) or (pr[1] >= 0.99 and pr[0] <= 0.01)):
                        continue
                    end = ts(m.get("endDate") or e.get("endDate"))
                    if not end:
                        continue
                    fs = m.get("feeSchedule") or {}
                    if isinstance(fs, str):
                        try:
                            fs = json.loads(fs)
                        except Exception:  # noqa: BLE001
                            fs = {}
                    on = str(m.get("feesEnabled")).lower() == "true"
                    todo.append({"cid": m["conditionId"], "e": e.get("slug"), "cat": cat, "q": (m.get("question") or "")[:70], "end": end,
                                 "closed": ts(m.get("closedTime")), "y0": 1.0 if pr[0] >= 0.99 else 0.0,
                                 "fee": float(fs.get("rate") or 0) if on else 0.0, "vol": float(m.get("volumeNum") or 0)})
            if len(page) < 100:
                break
    if w % 3 == 0:
        print(f"weeks 1-{w}: events {dict(ev_n)} markets {len(todo)}  ({time.time() - T0:.0f}s)", flush=True)

markets = []; wallets = {}; wl = []; blob = bytearray(); blob2 = bytearray(); n_tr = 0; n_trunc = 0; done = 0


def save():
    with gzip.open(f"data/research/entries_{GROUP}.bin.gz", "wb") as fh:
        fh.write(bytes(blob))
    with gzip.open(f"data/research/orders_{GROUP}.bin.gz", "wb") as fh:
        fh.write(bytes(blob2))
    json.dump({"at": now.strftime("%Y-%m-%d %H:%M"), "group": GROUP, "weeks": WEEKS, "row": ROW.format, "row2": ROW2.format, "markets": markets, "wallets": wl,
               "trades": n_tr, "truncated_markets": n_trunc}, gzip.open(f"data/research/entries_{GROUP}_meta.json.gz", "wt"), separators=(",", ":"))


os.makedirs("data/research", exist_ok=True); last_save = time.time()
with ThreadPoolExecutor(5) as ex:
    it = iter(todo); futs = []
    while True:
        while len(futs) < 40 and time.time() - T0 < T_MAX:
            m = next(it, None)
            if m is None:
                break
            futs.append(ex.submit(process, m))
        if not futs:
            break
        m, out, big, n, trunc = futs.pop(0).result()
        done += 1; n_tr += n; n_trunc += trunc
        if out:
            mi = len(markets)
            markets.append([m["cid"], m["e"], m["cat"], m["q"], int(m["end"]), int(m["closed"] or 0), m["y0"], m["fee"]])
            for t, w, hb, S, C, F, a, a60, a300, lag, fl in out:
                wi = wallets.get(w)
                if wi is None:
                    wi = wallets[w] = len(wl); wl.append(w)
                blob += ROW.pack(t, mi, wi, hb, S, C, F, int(round(a * 1e4)), int(round(a60 * 1e4)), int(round(a300 * 1e4)), min(lag, 4000000000), fl)
            for t, w, hb, c, sh, aavg, amax, aprev, a60, a300, lag, volp, cumw, fl in big:
                wi = wallets.get(w)
                if wi is None:
                    wi = wallets[w] = len(wl); wl.append(w)
                blob2 += ROW2.pack(t, mi, wi, hb, c, sh, int(round(aavg * 1e4)), int(round(amax * 1e4)), int(round(aprev * 1e4)), int(round(a60 * 1e4)),
                                   int(round(a300 * 1e4)), min(lag, 4000000000), volp, cumw, fl)
        if done % 2000 == 0:
            print(f"  {done}/{len(todo)} markets, {n_tr} trades, entries {len(blob) // ROW.size}, big orders {len(blob2) // ROW2.size}, wallets {len(wl)}, truncated {n_trunc}, 429s {n429[0]}, {time.time() - T0:.0f}s", flush=True)
        if time.time() - last_save > 900:
            save(); last_save = time.time()
    left = sum(1 for _ in it)
save()
print(f"group {GROUP}: markets done {done} (kept {len(markets)}), not reached {left}, trades {n_tr}, entries {len(blob) // ROW.size}, wallets {len(wl)}, "
      f"truncated {n_trunc}, 429s {n429[0]}, {time.time() - T0:.0f}s", flush=True)
