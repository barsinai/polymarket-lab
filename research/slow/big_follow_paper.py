"""Paper tracker (NO ORDERS, public endpoints only): follow big taker orders in slow markets at the REAL ask a moment later.

Why (11-14, tape_census.py / tape_entries.py, public trade tape): on Polymarket the makers lose to the takers in slow categories,
and the taker's edge grows with the size of the trade: trades under $10 lose 1.6 points per share, trades of $1,000+ win 6.4
[3.2, 9.9], and a follower who bought at the next same-way print still kept +4.6 [1.1, 8.1] (6 weeks, 6 small categories, 61
events). 'Next print' is a proxy; this tracker measures the real thing: the best ask in the order book when a slow bot would act.

Loop (RUN_MIN minutes, one poll every POLL s): the public feed of taker fills >= $FILTER (data-api /v2/trades, a few seconds
behind the chain). Fills of one wallet one way in one market are summed per transaction (an 'order') and over 30 minutes (an
'accumulation'). Direction +1 = towards YES (buy YES or sell NO); every fill is booked as buying the token of its direction at the
ask-equivalent price (buy: p, sell: 1 - p) - the same definitions as the back-test. When the sum crosses a tier ($500, $1,000,
$2,500, $10,000): classify the market by its event's tags, drop sports / e-sports / crypto up-down (fast, in-play), drop markets
that are closed or end in < 1 h, read the book of the token of the order's direction and paper-buy $20 at the best ask.
Flags on every paper position: tier, cap_ok (ask <= the order's average price + 3c) and primary (the first cap_ok position of
tier >= $1,000 in that market and direction that UTC day) - 'primary' is the rule a real bot would run; the rest is for slicing.
The ask is read again 5 and 60 minutes later (how fast does it run away?). Settled at resolution with the market's taker fee.
State under data/bigfollow/."""
import json, os, time, datetime as dt, collections
import requests

DA = "https://data-api.polymarket.com"; G = "https://gamma-api.polymarket.com"; CLOB = "https://clob.polymarket.com"
RUN_MIN = float(os.environ.get("RUN_MIN", "55")); POLL = float(os.environ.get("POLL", "20")); FILTER = float(os.environ.get("FILTER", "10"))
TIERS = (500, 1000, 2500, 10000); MAIN = 1000; STAKE = 20.0; CAP = 0.03; WINDOW = 1800; BACK = 60
D = os.environ.get("BF_DIR", "data/bigfollow"); CACHE = os.environ.get("BF_CACHE", "/tmp/bf_cache.json")
POS = f"{D}/positions.jsonl"; STATE = f"{D}/state.json"; REP = f"{D}/report.json"; SKIP = f"{D}/skipped.jsonl"
FAST = {"sports", "games", "esports", "soccer", "nba", "nfl", "nhl", "mlb", "ncaa", "tennis", "ufc", "mma", "cricket", "golf", "f1", "formula1", "cfb", "cbb",
        "boxing", "epl", "ucl", "up-or-down", "crypto-up-down", "5m", "15m", "1h", "hourly", "4h"}
CATS = [("weather", "weather"), ("mention-markets", "mention"), ("earnings-calls", "mention"), ("youtube", "culture"), ("mrbeast", "culture"),
        ("movies", "culture"), ("music", "culture"), ("awards", "culture"), ("pop-culture", "culture"), ("economy", "economy"), ("fed", "economy"),
        ("earnings", "economy"), ("ai", "tech"), ("tech", "tech"), ("geopolitics", "geopolitics"), ("elections", "politics"), ("politics", "politics"),
        ("crypto-prices", "crypto"), ("crypto", "crypto"), ("world", "geopolitics"), ("business", "economy"), ("science", "tech")]
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


os.makedirs(D, exist_ok=True)
st = json.load(open(STATE)) if os.path.exists(STATE) else {}
since = max(float(st.get("since", 0)), time.time() - 600)             # a restart never replays more than 10 minutes
primary = set(st.get("primary", [])); started = st.get("started") or int(time.time()); hours = float(st.get("hours", 0))
pos = [json.loads(l) for l in open(POS)] if os.path.exists(POS) else []
try:
    ch = json.load(open(CACHE))
except Exception:  # noqa: BLE001
    ch = {}
ecache = ch.get("e", {}); mcache = ch.get("m", {})
seen = {}; orders = {}; accum = {}; fired = {}
recheck = [(p["t"] + dl, i, key) for i, p in enumerate(pos) for dl, key in ((300, "ask5"), (3600, "ask60")) if key not in p and not p.get("res")]


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
        m = {"id": str(m.get("id")), "q": (m.get("question") or "")[:110], "ev": ((m.get("events") or [{}])[0] or {}).get("slug"), "end": ts(m.get("endDate")),
             "closed": bool(m.get("closed")), "tok": tok, "fee": float(fs.get("rate") or 0) if str(m.get("feesEnabled")).lower() == "true" else 0.0,
             "sport": bool(m.get("sportsMarketType")) or bool(m.get("gameStartTime")), "slug": m.get("slug") or ""}
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
    return {"ask": a, "ask_usd": round(a * asks[0][1], 1), "usd2c": round(sum(p * s for p, s in asks if p <= a + 0.02 + 1e-9), 1), "bid": bids[0][0] if bids else None}


def settle():
    ids = sorted({p["mid"] for p in pos if not p.get("res")}); done = {}
    for i in range(0, len(ids), 40):
        d = get(f"{G}/markets", [("id", x) for x in ids[i:i + 40]] + [("closed", "true"), ("limit", 100)])
        for m in d or []:
            try:
                pr = [float(x) for x in json.loads(m.get("outcomePrices") or "[]")]
            except Exception:  # noqa: BLE001
                continue
            if m.get("closed") and len(pr) == 2 and (max(pr) >= 0.99 or (abs(pr[0] - 0.5) < 0.01 and abs(pr[1] - 0.5) < 0.01)):
                done[str(m.get("id"))] = pr
    n = 0
    for p in pos:
        pr = done.get(p["mid"])
        if pr and not p.get("res"):
            pay = 1.0 if pr[p["idx"]] >= 0.99 else 0.5 if pr[p["idx"]] > 0.4 else 0.0
            p.update(res=1, pay=pay, pnl=round(p["sh"] * pay - STAKE - p["fee"], 3)); n += 1
    stats["settled now"] += n


def skip(rec, why):
    stats["skip: " + why] += 1
    rec["skip"] = why
    with open(SKIP, "a") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


def trigger(cid, w, d, tier, o, acc, row):
    now = time.time(); stats[f"crossings ${tier}"] += 1
    ev_slug = row.get("event_slug") or ""
    if is_fast(ev_slug, None) or is_fast(row.get("slug"), None):
        stats["fast (crypto up/down)"] += 1; return
    tags = event_tags(ev_slug) if ev_slug else None
    if is_fast(ev_slug, tags):
        stats["fast (sports)"] += 1; return
    m = market(cid)
    kind = "order" if o["usd"] >= tier else "accum"
    rec = {"t": int(now), "lag": int(now - acc["t_last"]), "cid": cid, "dir": d, "tier": tier, "kind": kind, "usd": round(acc["usd"], 1),
           "avg": round(acc["usd"] / acc["sh"], 4), "max": round(acc["max"], 4), "w": w, "q": (row.get("title") or "")[:110], "ev": ev_slug}
    if not m:
        return skip(rec, "market not found")
    if m["sport"] or is_fast(m["slug"], None):
        stats["fast (sports)"] += 1; return
    if tags is None and m["ev"]:
        tags = event_tags(m["ev"]); rec["ev"] = m["ev"]
        if is_fast(m["ev"], tags):
            stats["fast (sports)"] += 1; return
    tags = tags or []
    cat = next((c for t, c in CATS if t in tags), "other")
    hb = ((m["end"] or 0) - now) / 3600
    rec.update(cat=cat, hb=round(hb, 1))
    if m["closed"] or hb < 1 or len(m["tok"]) != 2:
        return skip(rec, "closed or ends in < 1 h")
    idx = 0 if d == 1 else 1
    b = book(m["tok"][idx])
    if not b:
        return skip(rec, "no ask in the book")
    rec.update(b)
    if not 0.02 <= b["ask"] <= 0.98:
        return skip(rec, "ask outside 0.02-0.98")
    day = time.strftime("%Y-%m-%d", time.gmtime(now)); pk = f"{cid}|{d}|{day}"
    cap_ok = b["ask"] <= rec["avg"] + CAP + 1e-9
    prim = bool(cap_ok and tier >= MAIN and pk not in primary)
    if prim:
        primary.add(pk); stats["primary follows"] += 1
    sh = STAKE / b["ask"]
    rec.update(mid=m["id"], idx=idx, end=int(m["end"] or 0), tags=tags[:6], cap_ok=cap_ok, primary=prim, sh=round(sh, 3), fee_rate=m["fee"],
               fee=round(m["fee"] * b["ask"] * (1 - b["ask"]) * sh, 4), tok=m["tok"][idx])
    pos.append(rec); stats["paper positions"] += 1
    recheck.append((now + 300, len(pos) - 1, "ask5")); recheck.append((now + 3600, len(pos) - 1, "ask60"))


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


def save():
    with open(POS, "w") as fh:
        for p in pos:
            fh.write(json.dumps(p, ensure_ascii=False) + "\n")
    today = time.strftime("%Y-%m-%d", time.gmtime(time.time() - 2 * 86400))
    json.dump({"since": since, "primary": sorted(k for k in primary if k.rsplit("|", 1)[-1] >= today), "started": started,
               "hours": round(hours + (time.time() - T0) / 3600, 2)}, open(STATE, "w"))
    json.dump({"e": ecache, "m": {k: v for k, v in mcache.items() if v}}, open(CACHE, "w"))
    done = [p for p in pos if p.get("res")]; main = [p for p in done if p["primary"]]; opn = [p for p in pos if not p.get("res")]
    sl = sorted(p["ask"] - p["avg"] for p in pos if p["tier"] >= MAIN) or [0]
    band = lambda p: "ask < 0.20" if p["ask"] < 0.2 else "ask 0.20-0.50" if p["ask"] < 0.5 else "ask 0.50-0.80" if p["ask"] < 0.8 else "ask >= 0.80"   # noqa: E731
    rep = {"updated": time.strftime("%Y-%m-%d %H:%M", time.gmtime()), "tracking_hours": round(hours + (time.time() - T0) / 3600, 1),
           "rule": "primary = first position per market+direction+day after a taker order/accumulation >= $1,000, ask <= its average price + 3c; $20 at the ask; fee paid",
           "positions": len(pos), "open": len(opn), "settled": len(done), "primary_open": sum(1 for p in opn if p["primary"]), "primary_settled": len(main),
           "PRIMARY": table(main, lambda p: "all"), "primary_by_category": table(main, lambda p: p["cat"]), "primary_by_price": table(main, band),
           "primary_by_tier": table(main, lambda p: f"${p['tier']}+"), "all_cap_ok_by_tier": table([p for p in done if p["cap_ok"]], lambda p: f"${p['tier']}+"),
           "not_cap_ok_by_tier": table([p for p in done if not p["cap_ok"]], lambda p: f"${p['tier']}+"),
           "slip_vs_order_avg_tier1000+": {"p25": round(sl[len(sl) // 4], 3), "median": round(sl[len(sl) // 2], 3), "p75": round(sl[3 * len(sl) // 4], 3)},
           "median_lag_s": sorted(p["lag"] for p in pos)[len(pos) // 2] if pos else None,
           "median_usd_at_ask": sorted(p["ask_usd"] for p in pos)[len(pos) // 2] if pos else None,
           "median_usd_within_2c": sorted(p["usd2c"] for p in pos)[len(pos) // 2] if pos else None, "run_stats": dict(stats)}
    json.dump(rep, open(REP, "w"), indent=1)
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
            acc = accum[ak] = {"t": t, "usd": 0.0, "sh": 0.0, "max": 0.0, "t_last": t}
        acc["usd"] += a * sz; acc["sh"] += sz; acc["max"] = max(acc["max"], a); acc["t_last"] = max(acc["t_last"], t)
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
            if nowt - when > 900:
                pos[i][key] = None; continue                       # missed (the tracker was restarting): unknown, not a price
            b = book(pos[i]["tok"])
            pos[i][key] = b["ask"] if b else None
        recheck.extend(due[40:])
    if time.time() - last_settle > 1500:
        settle(); last_settle = time.time()
    if time.time() - last_save > 600:
        save(); last_save = time.time()
    time.sleep(max(1.0, POLL - (time.time() - t_poll)))
settle()
rep = save()
print(json.dumps({k: rep[k] for k in ("updated", "tracking_hours", "positions", "open", "settled", "primary_open", "primary_settled", "PRIMARY", "run_stats")}))
