"""Paper market making, version 2 - runs every 10 minutes alongside version 1 (paper_mm.py)
so the two can be compared. No money; real order books and real trades.

Changes from v1 (all from v1's first 11 hours):
  * requotes every 10 minutes (v1: hourly) - stale quotes were what got picked off
  * leans against inventory: quote centre shifted 1c per full size held, and no new orders on
    a side once holding more than 2x size (v1 piled up one-sided positions)
  * keeps quoting (exit-only) markets where it holds inventory instead of abandoning them
  * caps exposure per question family (template: names/numbers stripped, e.g. all
    "Will X be in the next Israeli government?") at $300
  * ranks markets by reward relative to recent price movement, skips data-release markets
    (CPI, PPI, PMI, GDP, payrolls, jobless...) and anything within 5 days of its end
Each tick: settle fills since the last tick from real taker trades, credit rewards for the
time quotes rested (pool/day x our score share at the time), mark to midpoint, settle
resolved markets (CLOB /markets/<id> winner flags), requote.
State: data/paper_mm2/state.json; report: data/paper_mm2/report.json; hourly logs.
"""
import glob, gzip, json, math, os, re, sys, time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import collect  # noqa: E402
from record_books import books_for  # noqa: E402

# Variant (env MM_VARIANT): "1c" offers at mid+-1c (default), "2c" at mid+-2c,
# "edge" just inside the reward zone's outer edge (max_spread - 0.5c). Each has its own state dir.
# "wide": 1c offers, but the smallest size each market's reward programme accepts, in up to
# 200 markets (same capital spread thin: reward share saturates per market, so breadth should
# earn more per dollar and no single market can hurt much).
# "park": maker-only favourites. Markets 1-5 days from their end priced 80-95c (or 5-20c: then
# the favourite is No): post ONE resting order on the favourite side just inside the best price,
# hold to resolution. Fair history: favourites 80-95c one day out were ~2.6c underpriced; as a
# maker there is no fee, plus rebates and (one-sided) rewards. Risk = upsets.
VARIANT = os.environ.get("MM_VARIANT", "1c")
PARK = VARIANT == "park"
# "2cv": 2c offers with size scaled by calmness (replay: net/hour doubled vs plain 2c)
if VARIANT in ("2cv", "2cl"):
    os.environ.setdefault("MM_SIZE_BY_VOL", "1")
# "2cl": the replay frontier as of 11-03 evening: 2c offers, vol from the 14-day history, size by calmness
# with a wide clamp (0.25-3x), size capped at 1x the competing depth. Replay: net +13.6/h on $3.7k vs
# +9.0/h on $6.7k for 2cv. (The one-tick lean it started with no longer helped on top of these; dropped.)
if VARIANT in ("2cl", "live"):
    os.environ.setdefault("MM_VOL14", "1")
    os.environ.setdefault("MM_SV_LO", "0.25"); os.environ.setdefault("MM_SV_HI", "3")
    os.environ.setdefault("MM_SIZE_BY_COMP", "1")
    # 11-04 night batch (93h): 1.5c offers where the tick allows, harder size cut (ref 0.004), event cap $75
    # -> net per $ +24% vs the 11-03 frontier (17.4/h on $4.5k vs 16.5/h on $5.3k)
    os.environ.setdefault("MM_OFF", "0.015"); os.environ.setdefault("MM_SV_REF", "0.004"); os.environ.setdefault("MM_EVENT_CAP", "75")
# "live": the pilot. Same rules as 2cl, few markets, minimum size; positions come from the exchange
# (research/live/live_tick.py writes positions_live.json before each tick) and fills/rewards are NOT
# simulated - the exchange is the truth. Never sends orders itself.
if VARIANT == "live":
    os.environ.setdefault("MM_N", "8"); os.environ.setdefault("MM_SIZE", "0"); os.environ.setdefault("MM_LIVE", "1")
LIVE = os.environ.get("MM_LIVE") == "1"
D = "data/paper_mm2" if VARIANT == "1c" else f"data/paper_mm2_{VARIANT}"
N = int(os.environ.get("MM_N", "200" if VARIANT == "wide" else "40"))
SIZE = int(os.environ.get("MM_SIZE", "0" if VARIANT == "wide" else "200"))
SKEW, EVENT_CAP, MAX_BOOK_SPREAD = float(os.environ.get("MM_SKEW", "0.01")), float(os.environ.get("MM_EVENT_CAP", "150")), 0.04
EXIT_OFF = float(os.environ.get("MM_EXIT_OFF", "0.005"))          # exit-only quotes sit this far from mid
# "tight": 0.4c from mid in markets with 0.1c ticks (the quadratic reward score roughly doubles
# vs 1c), 1c elsewhere. More reward share, more fills: the trade-off to measure.
OFF = {"1c": 0.01, "2c": 0.02, "2cv": 0.02, "2cl": 0.02, "live": 0.02, "wide": 0.01, "park": 0.005, "tight": 0.01}.get(VARIANT, 0.01)
# trade-tape filter: pull quotes for a tick when the last trades were big and one-directional
TAPE_USD, TAPE_N = 500.0, 3
# experimental switches (env), so the same code runs live and in replay:
PAUSE_AFTER_FILL = os.environ.get("MM_PAUSE_AFTER_FILL") == "1"   # filled last tick -> stand aside this tick
SIZE_BY_VOL = os.environ.get("MM_SIZE_BY_VOL") == "1"             # quote more in calm markets, less in jumpy ones
MAX_JUMP = float(os.environ.get("MM_MAX_JUMP", "0.10"))           # exclude markets that moved more than this in an hour (48h)
MIN_POOL = float(os.environ.get("MM_MIN_POOL", "0"))              # ignore markets whose daily pool is below this
MIN_DAYS = float(os.environ.get("MM_MIN_DAYS", "7"))              # only markets at least this many days from their end
AGE_MAX = float(os.environ.get("MM_AGE_MAX", "1e9"))              # only markets created within this many days (new-market liquidity)
TAG = os.environ.get("MM_TAG", "").lower()                        # only markets carrying this tag (e.g. "weather")
OFF = float(os.environ["MM_OFF"]) if os.environ.get("MM_OFF") else OFF   # offset override, dollars
LEAN = os.environ.get("MM_LEAN") == "1"                           # shift quotes one tick toward the heavier side of the book
SV_LO, SV_HI = float(os.environ.get("MM_SV_LO", "0.5")), float(os.environ.get("MM_SV_HI", "2.0"))  # size-by-calmness clamp
SV_REF = float(os.environ.get("MM_SV_REF", "0.005"))
SIZE_BY_COMP = float(os.environ.get("MM_SIZE_BY_COMP", "0"))     # >0: size = this x the competing depth (in our-score units), capped at SIZE              # size-by-calmness: size *= SV_REF / vol (clamped)
VOL_W = float(os.environ.get("MM_VOL_W", "20"))                   # ranking: reward / (size * (1 + VOL_W * hourly vol))
VOL14 = os.environ.get("MM_VOL14") == "1"                         # vol from 14-day hourly history instead of the last 48h
JUMP14 = os.environ.get("MM_JUMP14") == "1"                       # ...and apply MAX_JUMP to the 14-day max move too
HOLD = os.environ.get("MM_HOLD") == "1"                           # markets no longer chosen: keep two-sided quotes at the normal offset instead of dumping at mid
WALLET = os.environ.get("MM_WALLET") == "1"                       # filled by a wallet with a good record -> stand aside 1h in that market
WALLET_TOP = float(os.environ.get("MM_WALLET_TOP", "0.058"))      # "good" = profit per $ above this (decile 9 edge of the sample)
WSCORES = None


def wallet_scores():
    global WSCORES
    if WSCORES is None:
        try:
            WSCORES = json.load(gzip.open("data/replay_mm/wallet_scores.json.gz", "rt"))["wallets"]
        except (OSError, ValueError):
            WSCORES = {}
    return WSCORES


def offset(v, tick=0.01):
    """distance from mid for this variant, in dollars; v = market max spread in cents"""
    if VARIANT == "edge":
        return max(0.01, (v - 0.5) / 100)
    if VARIANT == "tight" and tick <= 0.001:
        return 0.004
    return round(math.ceil(OFF / tick - 1e-9) * tick, 4)   # never finer than the market's tick (1.5c -> 2c in 1c-tick markets)
DATA_API = "https://data-api.polymarket.com"
SKIP = re.compile(r"\b(cpi|ppi|pmi|gdp|payroll|jobless|unemployment|inflation|nonfarm|retail sales|ism|jobs report|fed funds"
                  r"|sentiment|claims|interest rate|cash rate|policy rate|repo rate|rate cut|rate hike|bps|fed|fomc|ecb|boe|boj)\b"
                  r"|be between -?[\d.,]+ and -?[\d.,]+"
                  # 11-03: news-deadline and crypto-threshold questions jump without warning (overnight
                  # Iran-ceasefire / US-Cuba losses; historically 22% vs 17% of days with a >15c move,
                  # crypto thresholds ~50%): out of the universe for every v2 variant
                  r"|\b(by|before|through)\s+(january|february|march|april|may|june|july|august|september|october|november|december)\b"
                  r"|\b(hit|reach|dip to|settle over|settle under|above|below)\s+\$"
                  r"|\b(ceasefire|truce)\b", re.I)


# maker rebate (docs.polymarket.com/market-makers/maker-rebates): a maker fill earns
# rebate_share * taker_fee_rate * p * (1-p) per share, credited daily. Geopolitics: none.
def rebate_per_share(p, q):
    ql = (q or "").lower()
    if re.search(r"\b(bitcoin|btc|ethereum|eth|solana|xrp|doge|crypto)\b", ql):
        return 0.20 * 0.07 * p * (1 - p)
    if re.search(r"\b(vs\.?|nba|nfl|mlb|nhl|ufc|o/u|spread)\b", ql):
        return 0.15 * 0.05 * p * (1 - p)
    if re.search(r"\b(war|israel|iran|russia|ukraine|ceasefire|nato|gaza|hamas|houthi)\b", ql):
        return 0.0
    return 0.25 * 0.05 * p * (1 - p)


def template(q):
    q = re.sub(r"\d+([.,]\d+)?", "#", q or "")
    q = re.sub(r"\b[A-Z][\w'.&-]*", "X", q)
    return re.sub(r"(X[\s.,]*)+X", "X", q).lower().strip()


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


def score(levels, mid, v, minsize, is_bid):
    s_ = 0.0
    for p, size in levels:
        s = 100 * ((mid - p) if is_bid else (p - mid))
        if 0 <= s < v and size >= minsize:
            s_ += ((v - s) / v) ** 2 * size
    return s_


def load():
    try:
        return json.load(open(f"{D}/state.json"))
    except (OSError, ValueError):
        return {"positions": {}, "cash": 0.0, "rewards": 0.0, "quotes": {}, "fills": 0, "ticks": 0,
                "mids": {}, "universe": [], "universe_ts": 0, "settled": {}}


def jump_table():
    """conditionId -> (max abs 1h mid move over the last 48h, std of hourly moves), from the
    hourly live recording. Markets that have jumped >10c in a day are the ones that pick off
    a market maker; exclude them."""
    try:
        h = json.load(gzip.open("data/live/mids_48h.json.gz", "rt"))
    except (OSError, ValueError):
        return {}
    out = {}
    for c, v in h.items():
        ps = [p for _, p in v]
        if len(ps) >= 6:
            d = [abs(b - a) for a, b in zip(ps, ps[1:])]
            out[c] = (max(d), (sum(x * x for x in d) / len(d)) ** 0.5)
    if VOL14:  # 14-day hourly history (collect_hist.py): steadier vol estimate; optionally the 14-day max jump
        files = sorted(glob.glob("data/live/volfeat/*.json.gz"))
        if files:
            try:
                vf = json.load(gzip.open(files[-1], "rt"))
            except (OSError, ValueError):
                vf = {}
            for c, (sd, mx, n) in vf.items():
                j48 = out.get(c, (0.0, sd))[0]
                out[c] = (max(j48, mx) if JUMP14 else j48, sd)
    return out


def event_map():
    """conditionId -> Polymarket event id, from the daily meta files of the live recording"""
    out = {}
    for f in sorted(glob.glob("data/live/meta/*.jsonl.gz"))[-3:]:
        for m in collect.read_jsonl_gz(f):
            if m.get("conditionId") and m.get("event_id"):
                out[m["conditionId"]] = str(m["event_id"])
    return out


def created_map():
    """conditionId -> creation time (from the live meta files)"""
    out = {}
    for f in sorted(glob.glob("data/live/meta/*.jsonl.gz"))[-5:]:
        for m in collect.read_jsonl_gz(f):
            if m.get("conditionId") and m.get("createdAt"):
                out[m["conditionId"]] = ts(m["createdAt"])
    return out


def rewards_table():
    files = sorted(glob.glob("data/live/rewards/*.jsonl.gz"))
    out = {}
    if not files:
        return out
    for m in collect.read_jsonl_gz(files[-1]):
        r = m.get("rewards") or {}
        rate = sum(x.get("rewards_daily_rate") or 0 for x in r.get("rates") or [])
        toks = m.get("tokens") or []
        if rate > 0 and r.get("max_spread") and toks and m.get("accepting_orders", True):
            out[m["condition_id"]] = {"rate": rate, "v": float(r["max_spread"]), "minsize": float(r.get("min_size") or 0),
                                      "tick": float(m.get("minimum_tick_size") or 0.01),
                                      "q": m.get("question") or "", "end": ts(m.get("end_date_iso")),
                                      "tags": " ".join(t for t in (collect.as_list(m.get("tags")) or []) if isinstance(t, str)).lower(),
                                      "token": str(toks[0]["token_id"]), "tokens": [str(t["token_id"]) for t in toks]}
    return out


def book_view(bk):
    bids = sorted(((float(x["price"]), float(x["size"])) for x in bk.get("bids") or []), reverse=True)
    asks = sorted((float(x["price"]), float(x["size"])) for x in bk.get("asks") or [])
    return bids, asks


def trades_since(cid, t0):
    return collect.trades_since(cid, t0)


def tick(now=None):
    now = now or time.time()
    os.makedirs(D, exist_ok=True)
    st = load(); rw = rewards_table()
    if not rw:
        print("no rewards table"); return None
    log = {"ts": int(now), "fills": [], "rewards": 0.0, "settled": []}

    # refresh the universe hourly: books for all reward markets, keep the best 150 candidates
    JT = jump_table()
    if now - st["universe_ts"] > 3300 or not st["universe"]:
        cands = []
        if PARK:
            ok = {c: r for c, r in rw.items() if r["end"] and 1 * 86400 <= r["end"] - now <= 5 * 86400
                  and not re.search(r"\b(hit|reach|dip to|settle over|settle under)\s+\$", r["q"], re.I)}
        else:
            CM = created_map() if AGE_MAX < 1e8 else {}
            ok = {c: r for c, r in rw.items() if not SKIP.search(r["q"]) and not (r["end"] and r["end"] - now < MIN_DAYS * 86400)
                  and JT.get(c, (0, 0))[0] <= MAX_JUMP and r["rate"] >= MIN_POOL
                  and (not TAG or TAG in r["tags"]) and (AGE_MAX > 1e8 or (CM.get(c) and now - CM[c] <= AGE_MAX * 86400))}
        toks = [r["token"] for r in ok.values()]
        chunks = [toks[i:i + 500] for i in range(0, len(toks), 500)]
        books = {}
        with ThreadPoolExecutor(6) as ex:
            for part in ex.map(books_for, chunks):
                books.update(part)
        for c, r in ok.items():
            bk = books.get(r["token"])
            if not bk:
                continue
            bids, asks = book_view(bk)
            if not bids or not asks:
                continue
            mid = (bids[0][0] + asks[0][0]) / 2
            off = offset(r["v"], r["tick"])
            in_band = (0.80 <= mid <= 0.95 or 0.05 <= mid <= 0.20) if PARK else (0.10 < mid < 0.90)
            if not in_band or 100 * off >= r["v"] or asks[0][0] - bids[0][0] > MAX_BOOK_SPREAD:
                continue  # a wide book means the mid is not a real price: don't quote around it
            cb, ca = score(bids, mid, r["v"], r["minsize"], True), score(asks, mid, r["v"], r["minsize"], False)
            comp = min(cb, ca) if min(cb, ca) > 0 else max(cb, ca) / 3
            size = max(r["minsize"], SIZE, 20)
            ours = ((r["v"] - 100 * off) / r["v"]) ** 2 * size
            cands.append((r["rate"] * ours / (ours + comp) / size, c))
        st["universe"] = [c for _, c in sorted(cands, reverse=True)[:max(150, 3 * N)]]
        st["universe_ts"] = now
        print(f"universe refreshed: {len(st['universe'])} candidates from {len(ok)} eligible reward markets", flush=True)

    if LIVE:  # positions from the exchange, no simulated fills or reward credit
        try:
            live_pos = json.load(open(f"{D}/positions_live.json"))
        except (OSError, ValueError):
            live_pos = {}
        for p in st["positions"].values():
            p["yes"] = 0.0
        for cid, v in live_pos.items():
            r = rw.get(cid, {})
            p = st["positions"].setdefault(cid, {"yes": 0.0, "q": r.get("q", v.get("q", "")), "tpl": template(r.get("q", "")), "token": r.get("token") or v.get("token")})
            p["yes"] = float(v["yes"])
        st["quotes"] = {}
    watch = list(dict.fromkeys(st["universe"] + [c for c, p in st["positions"].items() if abs(p["yes"]) > 1e-9 and c not in st["settled"]]))
    tok_of = {c: (rw[c]["token"] if c in rw else st["positions"].get(c, {}).get("token")) for c in watch}
    books = books_for([t for t in tok_of.values() if t])
    st["last_books_ts"] = int(now) if books else st.get("last_books_ts", 0)

    # 1. fills on standing quotes, from real taker trades since they were placed
    qs = st["quotes"]
    with ThreadPoolExecutor(6) as ex:
        tr = dict(zip(qs, ex.map(lambda c: trades_since(c, qs[c]["ts"]), qs)))
    for cid, q in qs.items():
        pos = st["positions"].setdefault(cid, {"yes": 0.0, "q": q["q"], "tpl": q["tpl"], "token": q.get("token")})
        lb, la = q["size"] if q["bid"] else 0, q["size"] if q["ask"] else 0
        for t in sorted(tr.get(cid, []), key=lambda t: float(t["timestamp"])):
            px, sz, side, oc = float(t["price"]), float(t["size"]), t.get("side"), int(t.get("outcomeIndex") or 0)
            yp = px if oc == 0 else 1 - px
            hit_bid = ((oc == 0 and side == "SELL") or (oc == 1 and side == "BUY")) and lb > 0 and yp <= q["bid"] + 1e-9
            hit_ask = ((oc == 0 and side == "BUY") or (oc == 1 and side == "SELL")) and la > 0 and yp >= q["ask"] - 1e-9
            if WALLET and (hit_bid or hit_ask):
                w = wallet_scores().get(str(t.get("proxyWallet") or ""))
                if w and w[0] >= WALLET_TOP:
                    st.setdefault("toxic_until", {})[cid] = now + 3600
                    st["wallet_skips"] = st.get("wallet_skips", 0) + 1
            if hit_bid:
                f = min(lb, sz); lb -= f; pos["yes"] += f; st["cash"] -= f * q["bid"]; st["fills"] += 1
                st["rebates"] = st.get("rebates", 0.0) + f * rebate_per_share(q["bid"], q["q"])
                log["fills"].append([cid, "buy", q["bid"], f])
            elif hit_ask:
                f = min(la, sz); la -= f; pos["yes"] -= f; st["cash"] += f * q["ask"]; st["fills"] += 1
                st["rebates"] = st.get("rebates", 0.0) + f * rebate_per_share(q["ask"], q["q"])
                log["fills"].append([cid, "sell", q["ask"], f])
        # 2. rewards for the time rested: full credit if both sides still had size, a third if one
        #    side. Scaled by how far our quotes sit from the CURRENT mid (a quote that drifted out of
        #    the reward zone scores 0), and zero if the market would pay us < $1/day (Polymarket's
        #    minimum payout).
        dt_days = (now - q["ts"]) / 86400
        both = lb > 0 and la > 0
        one = (lb > 0) != (la > 0)
        drift = 1.0
        bk_now = books.get(q.get("token"))
        if bk_now and q.get("rpd", 0) > 0:
            b_, a_ = book_view(bk_now)
            if b_ and a_:
                mid_now = (b_[0][0] + a_[0][0]) / 2
                v = rw.get(cid, {}).get("v", 3.0)
                def sc(dist_c):
                    return ((v - dist_c) / v) ** 2 if 0 <= dist_c < v else 0.0
                s_old = sc(100 * q.get("off", OFF))
                s_new = min(sc(100 * abs(mid_now - q["bid"])) if q["bid"] else 1.0,
                            sc(100 * abs(q["ask"] - mid_now)) if q["ask"] else 1.0)
                drift = (0.5 * (s_old + s_new) / s_old) if s_old > 0 else 0.0
        credit = q["rpd"] * dt_days * (1 if both else (1 / 3 if one else 0)) * drift
        if q.get("rpd", 0) * (1 if both else 1 / 3) < 1.0:
            credit = 0.0  # below the $1/day minimum: nothing is paid
        st["rewards"] += credit; log["rewards"] += credit
    st["quotes"] = {}

    # 3. mark to mid; settle closed markets
    for cid, pos in st["positions"].items():
        bk = books.get(tok_of.get(cid) or pos.get("token"))
        if bk:
            bids, asks = book_view(bk)
            if bids and asks:
                pos["mid"] = (bids[0][0] + asks[0][0]) / 2
                st["mids"].setdefault(cid, []).append([int(now), pos["mid"]])
                st["mids"][cid] = st["mids"][cid][-200:]
        elif abs(pos["yes"]) > 1e-9 and cid not in st["settled"]:
            m = collect.get(f"{collect.CLOB}/markets/{cid}", tries=2) or {}
            if m.get("closed"):
                toks_ = m.get("tokens") or []
                if any(t.get("winner") for t in toks_):
                    pay = 1.0 if any(str(t.get("token_id")) == pos.get("token") and t.get("winner") for t in toks_) else 0.0
                    st["cash"] += pos["yes"] * pay
                    log["settled"].append([cid, pos["yes"], pay])
                    pos["yes"] = 0.0; st["settled"][cid] = pay

    # exposure per event (Polymarket's own grouping; sentence-shape template only as fallback)
    EVM = event_map()
    fam = {}
    for cid, pos in st["positions"].items():
        g = EVM.get(cid) or pos.get("tpl", "")
        fam[g] = fam.get(g, 0) + abs(pos["yes"]) * pos.get("mid", 0.5)

    # 4. requote: best N by reward vs recent movement, plus exit-only quotes where we hold inventory
    ranked = []; compq = {}
    for cid in watch:
        r = rw.get(cid); bk = books.get(r["token"]) if r else None
        if not bk:
            continue
        bids, asks = book_view(bk)
        if not bids or not asks:
            continue
        mid = (bids[0][0] + asks[0][0]) / 2
        if not (0.05 < mid < 0.95) if not PARK else not (0.80 <= mid <= 0.96 or 0.04 <= mid <= 0.20):
            continue
        off = offset(r["v"], r["tick"])
        wide = asks[0][0] - bids[0][0] > MAX_BOOK_SPREAD
        cb, ca = score(bids, mid, r["v"], r["minsize"], True), score(asks, mid, r["v"], r["minsize"], False)
        comp = min(cb, ca) if min(cb, ca) > 0 else max(cb, ca) / 3
        size = max(r["minsize"], SIZE, 20)
        ours = ((r["v"] - 100 * off) / r["v"]) ** 2 * size
        compq[cid] = comp / max(((r["v"] - 100 * off) / r["v"]) ** 2, 1e-9)   # competitors' score, in shares-at-our-offset
        rpd = 0.0 if wide else r["rate"] * ours / (ours + comp)
        # tape filter: recent taker trades big and all one way -> informed flow, stand aside
        tape = sorted(tr.get(cid, []), key=lambda t: float(t["timestamp"]))[-TAPE_N:]
        if len(tape) == TAPE_N and all(float(t["price"]) * float(t["size"]) >= TAPE_USD for t in tape):
            dirs = {((t.get("side") == "BUY") == (int(t.get("outcomeIndex") or 0) == 0)) for t in tape}
            if len(dirs) == 1:
                st["tape_skips"] = st.get("tape_skips", 0) + 1
                rpd = 0.0
        if cid in JT:
            vol = JT[cid][1]
            if JT[cid][0] > MAX_JUMP:
                rpd = 0.0  # jumped recently: exit only
        else:
            hist = [p for _, p in st["mids"].get(cid, [])][-36:]
            vol = (sum((b - a) ** 2 for a, b in zip(hist, hist[1:])) / max(len(hist) - 1, 1)) ** 0.5 if len(hist) > 3 else 0.01
        if PAUSE_AFTER_FILL and any(f_[0] == cid for f_ in log["fills"]):
            rpd = 0.0  # someone just traded with us: let the price settle before quoting again
        if WALLET and st.get("toxic_until", {}).get(cid, 0) > now:
            rpd = 0.0  # a wallet with a good track record just traded against us: stand aside
        ranked.append((rpd / (size * (1 + VOL_W * vol)), cid, mid, size, rpd))
    ranked.sort(reverse=True)
    chosen = {c for sc_, c, *_ in ranked[:N] if sc_ > 0}
    for _, cid, mid, size, rpd in ranked:
        pos = st["positions"].get(cid, {"yes": 0.0})
        inv = pos["yes"]
        if cid not in chosen and abs(inv) < 1e-9:
            continue
        tpl = template(rw[cid]["q"])
        exit_only = cid not in chosen
        off = offset(rw[cid]["v"], rw[cid]["tick"])
        if SIZE_BY_COMP and not exit_only and not PARK and cid in compq:
            size = max(rw[cid]["minsize"], 20, min(size, round(SIZE_BY_COMP * compq[cid])))
        if SIZE_BY_VOL and cid in JT and not PARK:
            size = max(rw[cid]["minsize"], 20, round(size * min(SV_HI, max(SV_LO, SV_REF / max(JT[cid][1], 0.001)))))
        centre = mid - SKEW * (inv / size)
        if LEAN and not PARK:  # heavier bid side within 2c of mid -> price tends to drift up (+0.1c/h at the extremes)
            bk_ = books.get(rw[cid]["token"]); bids_, asks_ = book_view(bk_) if bk_ else ([], [])
            db = sum(s_ for p_, s_ in bids_ if mid - p_ <= 0.02); da = sum(s_ for p_, s_ in asks_ if p_ - mid <= 0.02)
            imb = (db - da) / (db + da) if db + da > 0 else 0.0
            if abs(imb) > 0.4:
                centre += (rw[cid]["tick"] if imb > 0 else -rw[cid]["tick"])
        bid = round(centre - off, 3); ask = round(centre + off, 3)
        over_cap = fam.get(EVM.get(cid) or tpl, 0) > EVENT_CAP
        want_bid = inv < 2 * size and not (exit_only and inv >= 0) and not (over_cap and inv >= 0)
        want_ask = inv > -2 * size and not (exit_only and inv <= 0) and not (over_cap and inv <= 0)
        if PARK:  # one resting order on the favourite side, hold to resolution, never add past 1x size
            if exit_only:
                continue
            fav_yes = mid >= 0.5
            bid, ask = (round(mid - OFF, 3), None) if fav_yes else (None, round(mid + OFF, 3))
            want_bid = fav_yes and inv < size * 0.99
            want_ask = (not fav_yes) and inv > -size * 0.99
            if not (want_bid or want_ask):
                continue
        elif exit_only and HOLD:  # keep both quotes up at the normal offset (prices revert ~1/3 within a day); no reward counted
            want_bid, want_ask = inv < size, inv > -size
        elif exit_only:  # only work the position off, at the mid, no reward expected
            bid, ask = (round(mid - EXIT_OFF, 3), None) if inv < 0 else (None, round(mid + EXIT_OFF, 3))
            want_bid, want_ask = inv < 0, inv > 0
        st["quotes"][cid] = {"ts": int(now), "q": rw[cid]["q"], "tpl": tpl, "token": rw[cid]["token"], "off": off, "size": size if (not exit_only or HOLD) else abs(inv),
                             "bid": bid if want_bid and 0 < bid < 1 else None, "ask": ask if want_ask and ask and 0 < ask < 1 else None,
                             "rpd": 0.0 if exit_only else rpd}
    st["ticks"] += 1
    mtm = sum(p["yes"] * p.get("mid", 0.5) for p in st["positions"].values())
    inv_capital = sum(abs(p["yes"]) * (p.get("mid", 0.5) if p["yes"] > 0 else 1 - p.get("mid", 0.5)) for p in st["positions"].values())
    capital = sum(q["size"] * ((q["bid"] or 0) + (1 - (q["ask"] or 1))) for q in st["quotes"].values() if q["rpd"] > 0) + inv_capital
    rep = {"variant": VARIANT, "updated": datetime.fromtimestamp(now, timezone.utc).isoformat(), "ticks": st["ticks"], "fills": st["fills"],
           "rewards_earned": round(st["rewards"], 2), "maker_rebates": round(st.get("rebates", 0.0), 2),
           "trading_cash": round(st["cash"], 2), "inventory_value_at_mid": round(mtm, 2),
           "total_pnl": round(st["cash"] + mtm + st["rewards"] + st.get("rebates", 0.0), 2), "quoting": sum(1 for q in st["quotes"].values() if q["rpd"] > 0),
           "exit_only": sum(1 for q in st["quotes"].values() if q["rpd"] == 0), "capital_in_use": round(capital, 2),
           "capital_in_inventory": round(inv_capital, 2),
           "open_positions": sum(1 for p in st["positions"].values() if abs(p["yes"]) > 1e-9),
           "tape_skips": st.get("tape_skips", 0)}
    d = datetime.fromtimestamp(now, timezone.utc)
    os.makedirs(f"{D}/{d:%Y-%m-%d}", exist_ok=True)
    with open(f"{D}/{d:%Y-%m-%d}/{d:%H}.jsonl", "a") as f:
        f.write(json.dumps(log) + "\n")
    json.dump(st, open(f"{D}/state.json", "w"))
    json.dump(rep, open(f"{D}/report.json", "w"), indent=1)
    print(json.dumps(rep), flush=True)
    return rep


if __name__ == "__main__":
    tick()
