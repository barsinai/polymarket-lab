"""Paper tracker (NO ORDERS, public endpoints only): follow big taker orders at the REAL ask a moment later.

Why (11-14, tape_census.py / tape_entries.py, public trade tape): on Polymarket the makers lose to the takers in slow categories,
and the taker's edge grows with the size of the trade: trades under $10 lose 1.6 points per share, trades of $1,000+ win 6.4
[3.2, 9.9], and a follower who bought at the next same-way print still kept +4.6 [1.1, 8.1] (6 weeks, 6 small categories, 61
events). 'Next print' is a proxy; this tracker measures the real thing: the best ask in the order book when a slow bot would act.

Loop (RUN_MIN minutes, one poll every POLL s): the public feed of taker fills >= $FILTER (data-api /v2/trades, a few seconds
behind the chain). Fills of one wallet one way in one market are summed per transaction (an 'order') and over 30 minutes (an
'accumulation'). Direction +1 = towards YES (buy YES or sell NO); every fill is booked as buying the token of its direction at the
ask-equivalent price (buy: p, sell: 1 - p) - the same definitions as the back-test (buy_frac = the share that was real buys;
a sale of YES counts as 'towards NO' but may be profit-taking - the back-test file cannot tell them apart, this log can).
When the sum crosses a tier ($1,000, $2,500, $10,000): classify the market by its event's tags, drop sports / e-sports / parlays /
crypto up-down (fast, in-play), drop markets that are closed, end in < 1 h or in > 60 days, read the book of the token of the
order's direction and paper-buy $20 at the best ask if it is 0.03-0.97.
Flags on every paper position: tier, cap_ok (ask <= the order's average price + 3c) and primary (the first cap_ok position in
that market and direction that UTC day) - 'primary' is the rule a real bot would run; the rest is for slicing (category, price,
market volume, order size vs volume, days to the end, buy vs sell).
The ask is read again 5 and 60 minutes later (does it run away?) and the bid/ask 24 and 72 hours later (a mark for positions that
settle late). Settled at resolution with the market's taker fee.

Storage (append-only, so the hourly git save stays small): data/bigfollow/opens-<day>.jsonl (one line per position),
upd-<day>.jsonl (later prices and settlements, by position id), state.json, report.json."""
import json, os, time, glob, datetime as dt, collections
import requests

DA = "https://data-api.polymarket.com"; G = "https://gamma-api.polymarket.com"; CLOB = "https://clob.polymarket.com"
RUN_MIN = float(os.environ.get("RUN_MIN", "55")); POLL = float(os.environ.get("POLL", "20")); FILTER = float(os.environ.get("FILTER", "10"))
TIERS = (1000, 2500, 10000); STAKE = 20.0; CAP = 0.03; WINDOW = 1800; BACK = 60; MAX_DAYS = 60
D = os.environ.get("BF_DIR", "data/bigfollow"); CACHE = os.environ.get("BF_CACHE", "/tmp/bf_cache.json")
STATE = f"{D}/state.json"; REP = f"{D}/report.json"
FAST = {"sports", "games", "esports", "soccer", "nba", "nfl", "nhl", "mlb", "ncaa", "tennis", "ufc", "mma", "cricket", "golf", "f1", "formula1", "cfb", "cbb",
        "boxing", "epl", "ucl", "up-or-down", "crypto-up-down", "5m", "15m", "1h", "hourly", "4h"}
CATS = [("weather", "weather"), ("mention-markets", "mention"), ("earnings-calls", "mention"), ("tweets-markets", "tweets"), ("youtube", "culture"),
        ("mrbeast", "culture"), ("movies", "culture"), ("music", "culture"), ("awards", "culture"), ("crypto-prices", "crypto"), ("hit-price", "crypto"),
        ("pop-culture", "culture"), ("economy", "economy"), ("fed", "economy"), ("earnings", "economy"), ("finance", "economy"), ("ai", "tech"), ("tech", "tech"),
        ("geopolitics", "geopolitics"), ("elections", "politics"), ("politics", "politics"), ("crypto", "crypto"), ("world", "geopolitics"),
        ("business", "economy"), ("science", "tech")]
LATER = ((300, "ask5"), (3600, "ask60"), (86400, "m24"), (259200, "m72"))    # ask 5 / 60 minutes later; [bid, ask] 24 / 72 hours later
S = requests.Session(); S.headers["User-Agent"] = "polymarket-lab-research/0.1"
T0 = time.time(); stats = collections.Counter()


def get(url, params=None, tries=3):
    for k in range(tries):
        try:
            r = S.get(url, params=params, timeout=20)
            if r.status_code == 200:
                return r.json()
            stats[f"http {r.status_code}"] += 1
            if r.status_code != 429:
                return None
        except Exception:  # noqa: BLE001
            stats["http error"] += 1
        time.sleep(1 + 2 * k)
    return None


def ts(s):
    try:
        return dt.datetime.fromisoformat(str(s).replace(" ", "T").replace("Z", "+00:00").replace("+00+00:00", "+00:00")).timestamp()
    except Exception:  # noqa: BLE001
        try:
            return dt.datetime.fromisoformat(str(s)[:19]).replace(tzinfo=dt.timezone.utc).timestamp()
        except Exception:  # noqa: BLE001
            return None


def load(path, default):
    try:
        return json.load(open(path))
    except Exception:  # noqa: BLE001
        return default


def dump(obj, path, **kw):                                       # atomic: the git save may run while this process writes
    with open(path + ".tmp", "w") as fh:
        json.dump(obj, fh, **kw)
    os.replace(path + ".tmp", path)


def append(kind, obj):                                           # one JSON line to today's append-only file
    path = f"{D}/{kind}-{time.strftime('%Y-%m-%d', time.gmtime())}.jsonl"
    if path not in _checked:                                     # a killed job may have left a half-written last line
        _checked.add(path)
        if os.path.exists(path) and os.path.getsize(path) and open(path, "rb").read()[-1:] != b"\n":
            open(path, "a").write("\n")
    with open(path, "a") as fh:
        fh.write(json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n")


os.makedirs(D, exist_ok=True); _checked = set()
st = load(STATE, {})
since = max(float(st.get("since", 0)), time.time() - 600)             # a restart never replays more than 10 minutes
primary = set(st.get("primary", [])); started = st.get("started") or int(time.time()); hours = float(st.get("hours", 0)); seq = int(st.get("seq", 0))
total = collections.Counter(st.get("totals", {}))
pos = {}                                                              # id -> position (opens + their updates)
for f in sorted(glob.glob(f"{D}/opens-*.jsonl")):
    for l in open(f):
        try:
            p = json.loads(l); pos[p["id"]] = p
        except Exception:  # noqa: BLE001
            pass
for f in sorted(glob.glob(f"{D}/upd-*.jsonl")):
    for l in open(f):
        try:
            u = json.loads(l); pos[u.pop("id")].update(u)
        except Exception:  # noqa: BLE001
            pass
seq = max([seq] + [int(i) for i in pos])
ch = load(CACHE, {})
ecache = ch.get("e", {}); mcache = ch.get("m", {})
seen = {}; orders = {}; accum = {}; fired = {}
recheck = [(p["t"] + dl, i, key) for i, p in pos.items() for dl, key in LATER if key not in p and not p.get("res")]


def event_tags(slug):
    if slug not in ecache:
        e = get(f"{G}/events", {"slug": slug}) or get(f"{G}/events", {"slug": slug, "closed": "true"}) or []
        ecache[slug] = [str(t.get("slug")) for t in (e[0].get("tags") or [])] if e else None
    return ecache[slug]


def is_fast(slug, tags):
    s = (slug or "").lower()
    return "updown" in s or "up-or-down" in s or bool(set(tags or []) & FAST)


def market(cid):
    if cid in mcache:
        return mcache[cid]
    d = get(f"{G}/markets", {"condition_ids": cid}) or get(f"{G}/markets", {"condition_ids": cid, "closed": "true"}) or []
    m = d[0] if d else None
    if m:
        fs = m.get("feeSchedule") or {}
        if isinstance(fs, str):
            try:
                fs = json.loads(fs)
            except Exception:  # noqa: BLE001
                fs = {}
        try:
            tok = json.loads(m.get("clobTokenIds") or "[]")
        except Exception:  # noqa: BLE001
            tok = []
        try:
            vol = float(m.get("volumeNum") or m.get("volume") or 0)
        except Exception:  # noqa: BLE001
            vol = 0.0
        m = {"id": str(m.get("id")), "q": (m.get("question") or "")[:90], "ev": ((m.get("events") or [{}])[0] or {}).get("slug"), "end": ts(m.get("endDate")),
             "closed": bool(m.get("closed")), "tok": tok, "fee": float(fs.get("rate") or 0) if str(m.get("feesEnabled")).lower() == "true" else 0.0,
             "sport": bool(m.get("sportsMarketType")) or bool(m.get("gameStartTime")), "slug": m.get("slug") or "", "vol": round(vol)}
    mcache[cid] = m
    return m


def book(token):
    b = get(f"{CLOB}/book", {"token_id": token})
    if not b:
        return None
    try:
        asks = sorted((float(o["price"]), float(o["size"])) for o in b.get("asks") or [])
        bids = sorted(((float(o["price"]), float(o["size"])) for o in b.get("bids") or []), reverse=True)
    except Exception:  # noqa: BLE001
        return None
    if not asks:
        return None
    a = asks[0][0]
    return {"ask": a, "ask_usd": round(a * asks[0][1]), "usd2c": round(sum(p * s for p, s in asks if p <= a + 0.02 + 1e-9)), "bid": bids[0][0] if bids else None}


def update(i, **kw):
    pos[i].update(kw); append("upd", dict(id=i, **kw))


def settle():
    ids = sorted({p["mid"] for p in pos.values() if not p.get("res")}); done = {}
    for i in range(0, len(ids), 40):
        d = get(f"{G}/markets", [("id", x) for x in ids[i:i + 40]] + [("closed", "true"), ("limit", 100)])
        for m in d or []:
            try:
                pr = [float(x) for x in json.loads(m.get("outcomePrices") or "[]")]
            except Exception:  # noqa: BLE001
                continue
            if m.get("closed") and len(pr) == 2 and (max(pr) >= 0.99 or (abs(pr[0] - 0.5) < 0.01 and abs(pr[1] - 0.5) < 0.01)):
                done[str(m.get("id"))] = pr
    for i, p in pos.items():
        pr = done.get(p["mid"])
        if pr and not p.get("res"):
            pay = 1.0 if pr[p["idx"]] >= 0.99 else 0.5 if pr[p["idx"]] > 0.4 else 0.0
            update(i, res=1, pay=pay, pnl=round(p["sh"] * pay - STAKE - p["fee"], 3), t_res=int(time.time())); total["settled"] += 1


def skip(why):
    stats["skip: " + why] += 1; total["skip: " + why] += 1


def trigger(cid, w, d, tier, o, acc, row):
    global seq
    now = time.time(); total[f"crossings ${tier}"] += 1
    ev_slug = row.get("event_slug") or ""; title = row.get("title") or ""
    if is_fast(ev_slug, None) or is_fast(row.get("slug"), None):
        return skip("fast: crypto up/down")
    if not ev_slug and " AND " in title:
        return skip("fast: sports parlay (combo)")
    tags = event_tags(ev_slug) if ev_slug else None
    if is_fast(ev_slug, tags):
        return skip("fast: sports")
    m = market(cid)
    if not m:
        return skip("market not found")
    if m["sport"] or is_fast(m["slug"], None):
        return skip("fast: sports")
    if tags is None and m["ev"]:
        ev_slug = m["ev"]; tags = event_tags(ev_slug)
        if is_fast(ev_slug, tags):
            return skip("fast: sports")
    tags = tags or []
    hb = ((m["end"] or 0) - now) / 3600
    if m["closed"] or hb < 1 or len(m["tok"]) != 2:
        return skip("closed or ends in < 1 h")
    if hb > MAX_DAYS * 24:
        return skip(f"ends in > {MAX_DAYS} days")
    idx = 0 if d == 1 else 1
    b = book(m["tok"][idx])
    if not b:
        return skip("no ask in the book")
    if not 0.03 <= b["ask"] <= 0.97:
        return skip("ask outside 0.03-0.97")
    avg = acc["usd"] / acc["sh"]
    day = time.strftime("%Y-%m-%d", time.gmtime(now)); pk = f"{cid}|{d}|{day}"
    cap_ok = b["ask"] <= avg + CAP + 1e-9
    prim = bool(cap_ok and pk not in primary)
    if prim:
        primary.add(pk); total["primary follows"] += 1
    sh = STAKE / b["ask"]; seq += 1
    rec = {"id": str(seq), "t": int(now), "lag": int(now - acc["t_last"]), "cid": cid, "mid": m["id"], "idx": idx, "dir": d, "tier": tier,
           "kind": "order" if o["usd"] >= tier else "accum", "usd": round(acc["usd"]), "avg": round(avg, 4), "max": round(acc["max"], 4),
           "buy_frac": round(acc["buy"] / acc["usd"], 2), "fills": acc["n"], "w": w, "q": m["q"], "ev": ev_slug,
           "cat": next((c for t, c in CATS if t in tags), "other"), "tags": tags[:5], "hb": round(hb, 1), "end": int(m["end"] or 0), "vol": m["vol"],
           "ask": b["ask"], "ask_usd": b["ask_usd"], "usd2c": b["usd2c"], "bid": b["bid"], "cap_ok": cap_ok, "primary": prim, "sh": round(sh, 3),
           "fee_rate": m["fee"], "fee": round(m["fee"] * b["ask"] * (1 - b["ask"]) * sh, 4), "tok": m["tok"][idx]}
    pos[rec["id"]] = rec; append("opens", rec); total["paper positions"] += 1; stats["paper positions"] += 1
    recheck.extend((now + dl, rec["id"], key) for dl, key in LATER)


def pts(p, key="ask"):
    a = p.get(key)
    return None if a is None else p["pay"] - a - p["fee_rate"] * a * (1 - a)


def table(P, keyf):
    by = collections.defaultdict(list)
    for p in P:
        by[keyf(p)].append(p)
    out = {}
    for k, L in sorted(by.items(), key=lambda kv: str(kv[0])):
        x = [pts(p) for p in L]; x5 = [v for v in (pts(p, "ask5") for p in L) if v is not None]
        out[str(k)] = {"n": len(L), "events": len({p["ev"] for p in L}), "won": sum(1 for p in L if p["pay"] >= 0.99), "avg_ask": round(sum(p["ask"] for p in L) / len(L), 3),
                       "edge_pts": round(100 * sum(x) / len(x), 2), "edge_pts_5min_later": round(100 * sum(x5) / len(x5), 2) if x5 else None,
                       "pnl": round(sum(p["pnl"] for p in L), 2), "roi": round(sum(p["pnl"] for p in L) / (STAKE * len(L)), 4)}
    return out


def mark(P, key):                                               # positions (settled or not) with a book 24 / 72 h later: the mid then minus the ask paid
    by = collections.defaultdict(list)
    for p in P:
        if p.get(key) and p[key][0] is not None:
            v = (p[key][0] + p[key][1]) / 2 - p["ask"]; by[p["cat"]].append(v); by["all"].append(v)
    return {k: {"n": len(v), "mid_minus_ask_pts": round(100 * sum(v) / len(v), 2)} for k, v in sorted(by.items())}


def save():
    cutday = time.strftime("%Y-%m-%d", time.gmtime(time.time() - 2 * 86400))
    hrs = round(hours + (time.time() - T0) / 3600, 2)
    dump({"since": since, "primary": sorted(k for k in primary if k.rsplit("|", 1)[-1] >= cutday), "started": started, "hours": hrs, "seq": seq, "totals": dict(total)}, STATE)
    dump({"e": ecache, "m": {k: v for k, v in mcache.items() if v}}, CACHE)
    P = list(pos.values()); done = [p for p in P if p.get("res")]; main = [p for p in done if p["primary"]]; prim = [p for p in P if p["primary"]]
    sl = sorted(p["ask"] - p["avg"] for p in P) or [0]; med = lambda L: sorted(L)[len(L) // 2] if L else None   # noqa: E731
    band = lambda p: "ask < 0.20" if p["ask"] < 0.2 else "ask 0.20-0.50" if p["ask"] < 0.5 else "ask 0.50-0.80" if p["ask"] < 0.8 else "ask 0.80-0.97"   # noqa: E731
    hz = lambda p: "ends in < 24 h" if p["hb"] < 24 else "ends in 1-7 d" if p["hb"] < 168 else "ends in 7-60 d"   # noqa: E731
    vb = lambda p: "market volume < $50k" if p["vol"] < 5e4 else "$50k-500k" if p["vol"] < 5e5 else ">= $500k"   # noqa: E731
    rel = lambda p: "order >= 5% of market volume" if p["usd"] >= 0.05 * max(p["vol"], 1) else "order < 5% of market volume"   # noqa: E731
    rep = {"updated": time.strftime("%Y-%m-%d %H:%M", time.gmtime()), "tracking_hours": hrs,
           "rule": "primary = first position per market+direction+UTC day after a taker order/accumulation >= $1,000 (non-sports, ends in 1 h - 60 d), "
                   "ask 0.03-0.97 and <= its average price + 3c; $20 at the ask; taker fee paid",
           "positions": len(P), "open": len(P) - len(done), "settled": len(done), "primary": len(prim), "primary_settled": len(main),
           "primary_per_day": round(len(prim) / max(hrs / 24, 0.01), 1),
           "PRIMARY": table(main, lambda p: "all"), "primary_by_category": table(main, lambda p: p["cat"]), "primary_by_price": table(main, band),
           "primary_by_days_to_end": table(main, hz), "primary_by_market_volume": table(main, vb), "primary_by_order_vs_volume": table(main, rel),
           "primary_by_tier": table(main, lambda p: f"${p['tier']}+"), "primary_buys_vs_sells": table(main, lambda p: "real buys" if p["buy_frac"] >= 0.5 else "sells of the other side"),
           "not_primary_cap_ok": table([p for p in done if p["cap_ok"] and not p["primary"]], lambda p: "all"),
           "ask_ran_away_more_than_3c": table([p for p in done if not p["cap_ok"]], lambda p: "all"),
           "mark_24h_all_primary_positions": mark(prim, "m24"), "mark_72h_all_primary_positions": mark(prim, "m72"),
           "ask_minus_order_avg": {"p25": round(sl[len(sl) // 4], 3), "median": round(sl[len(sl) // 2], 3), "p75": round(sl[3 * len(sl) // 4], 3)},
           "median_lag_s": med([p["lag"] for p in P]), "median_usd_at_ask": med([p["ask_usd"] for p in P]), "median_usd_within_2c": med([p["usd2c"] for p in P]),
           "open_primary_by_category": dict(collections.Counter(p["cat"] for p in prim if not p.get("res"))), "totals": dict(total), "this_run": dict(stats)}
    dump(rep, REP, indent=1)
    return rep


def poll():
    global since
    rows = []; cur = None
    for _ in range(12):
        p = {"limit": 500, "filter_type": "CASH", "filter_amount": int(FILTER) if FILTER == int(FILTER) else FILTER, "taker_only": "true"}
        if cur:
            p["cursor"] = cur
        d = get(f"{DA}/v2/trades", p)
        page = (d or {}).get("data") if isinstance(d, dict) else None
        if not page:
            if d is None:
                stats["feed failures"] += 1
            break
        rows += page; stats["feed pages"] += 1
        pg = d.get("pagination") or {}
        try:
            oldest = min(float(r["timestamp"]) for r in page)
        except Exception:  # noqa: BLE001
            break
        if oldest < since - BACK or not pg.get("has_more") or not pg.get("next_cursor"):
            break
        cur = pg["next_cursor"]
    else:
        stats["feed gaps (12 pages were not enough)"] += 1
    stats["polls"] += 1
    cnt = collections.Counter(); keep = {}
    for r in rows:
        try:
            k = (r.get("transaction_hash"), r.get("proxy_wallet"), str(r.get("token_id")), r.get("side"), float(r["price"]), float(r["size"]), float(r["timestamp"]))
        except Exception:  # noqa: BLE001
            continue
        if k[6] < since - BACK or not k[1] or not r.get("condition_id"):
            continue
        cnt[k] += 1; keep[k] = r
    touched = {}; tmax = since
    for k, n in sorted(cnt.items(), key=lambda kv: kv[0][6]):
        new = n - seen.get(k, 0)
        if new <= 0:
            continue
        seen[k] = n
        r = keep[k]; pz, sz, t = k[4], k[5] * new, k[6]
        try:
            oi = int(r["outcome_index"])
        except Exception:  # noqa: BLE001
            continue
        if not 0 < pz < 1 or sz <= 0:
            continue
        stats["fills"] += new; tmax = max(tmax, t)
        buy = r.get("side") == "BUY"
        d = 1 if (buy and oi == 0) or ((not buy) and oi == 1) else -1
        a = pz if buy else 1 - pz
        cid = r["condition_id"]; w = k[1]
        ok = (cid, w, d, k[0]); o = orders.get(ok)
        if o is None:
            o = orders[ok] = {"t": t, "usd": 0.0, "sh": 0.0}
        o["usd"] += a * sz; o["sh"] += sz
        ak = (cid, w, d); acc = accum.get(ak)
        if acc is None or t - acc["t"] > WINDOW:
            acc = accum[ak] = {"t": t, "usd": 0.0, "sh": 0.0, "max": 0.0, "t_last": t, "buy": 0.0, "n": 0}
        acc["usd"] += a * sz; acc["sh"] += sz; acc["max"] = max(acc["max"], a); acc["t_last"] = max(acc["t_last"], t)
        acc["buy"] += a * sz * buy; acc["n"] += new
        touched[ak] = (o, acc, r)
    since = tmax
    for (cid, w, d), (o, acc, r) in touched.items():
        tier = max((x for x in TIERS if acc["usd"] >= x), default=0)
        f = fired.get((cid, w, d))
        if tier and (f is None or f[1] != acc["t"] or tier > f[0]):
            fired[(cid, w, d)] = (tier, acc["t"])
            try:
                trigger(cid, w, d, tier, o, acc, r)
            except Exception as e:  # noqa: BLE001
                stats[f"trigger error {type(e).__name__}"] += 1
    cut = time.time() - 3 * WINDOW
    if len(seen) > 150000:
        for k in [k for k in seen if k[6] < since - 2 * BACK]:
            del seen[k]
    if len(orders) > 150000:
        for k in [k for k, o in orders.items() if o["t"] < cut]:
            del orders[k]
        for k in [k for k, o in accum.items() if o["t_last"] < cut]:
            del accum[k]; fired.pop(k, None)


settle(); last_settle = last_save = time.time()
while time.time() - T0 < RUN_MIN * 60:
    t_poll = time.time()
    poll()
    nowt = time.time(); due = [x for x in recheck if x[0] <= nowt]
    if due:
        recheck[:] = [x for x in recheck if x[0] > nowt]
        for when, i, key in due[:40]:
            if pos[i].get("res"):
                continue
            if nowt - when > 900:
                update(i, **{key: None}); continue                 # missed (the tracker was restarting): unknown, not a price
            b = book(pos[i]["tok"])
            update(i, **{key: None if not b else b["ask"] if key.startswith("ask") else [b["bid"], b["ask"]]})
        recheck.extend(due[40:])
    if time.time() - last_settle > 1500:
        settle(); last_settle = time.time()
    if time.time() - last_save > 600:
        rep = save(); last_save = time.time()
        print(time.strftime("%m-%d %H:%M", time.gmtime()), "polls", stats["polls"], "fills", stats["fills"], "positions", rep["positions"], "primary", rep["primary"],
              "settled", rep["settled"], flush=True)
    time.sleep(max(1.0, POLL - (time.time() - t_poll)))
settle()
rep = save()
print(json.dumps({k: rep[k] for k in ("updated", "tracking_hours", "positions", "open", "settled", "primary", "primary_settled", "PRIMARY", "this_run")}))
