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
import glob, json, math, os, re, sys, time
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
VARIANT = os.environ.get("MM_VARIANT", "1c")
D = "data/paper_mm2" if VARIANT == "1c" else f"data/paper_mm2_{VARIANT}"
N = 200 if VARIANT == "wide" else 40
SIZE = 0 if VARIANT == "wide" else 200          # max(min_size, SIZE); wide -> min_size only
SKEW, EVENT_CAP, MAX_BOOK_SPREAD = 0.01, 300.0, 0.04
OFF = {"1c": 0.01, "2c": 0.02, "wide": 0.01}.get(VARIANT, 0.01)
# trade-tape filter: pull quotes for a tick when the last trades were big and one-directional
TAPE_USD, TAPE_N = 500.0, 3


def offset(v):
    """distance from mid for this variant, in dollars; v = market max spread in cents"""
    if VARIANT == "edge":
        return max(0.01, (v - 0.5) / 100)
    return OFF
DATA_API = "https://data-api.polymarket.com"
SKIP = re.compile(r"\b(cpi|ppi|pmi|gdp|payroll|jobless|unemployment|inflation|nonfarm|retail sales|ism|jobs report|fed funds"
                  r"|sentiment|claims|interest rate|cash rate|policy rate|repo rate|rate cut|rate hike|bps)\b"
                  r"|be between -?[\d.,]+ and -?[\d.,]+", re.I)


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


def event_map():
    """conditionId -> Polymarket event id, from the daily meta files of the live recording"""
    out = {}
    for f in sorted(glob.glob("data/live/meta/*.jsonl.gz"))[-3:]:
        for m in collect.read_jsonl_gz(f):
            if m.get("conditionId") and m.get("event_id"):
                out[m["conditionId"]] = str(m["event_id"])
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
                                      "q": m.get("question") or "", "end": ts(m.get("end_date_iso")),
                                      "token": str(toks[0]["token_id"])}
    return out


def book_view(bk):
    bids = sorted(((float(x["price"]), float(x["size"])) for x in bk.get("bids") or []), reverse=True)
    asks = sorted((float(x["price"]), float(x["size"])) for x in bk.get("asks") or [])
    return bids, asks


def trades_since(cid, t0):
    out, offset = [], 0
    while offset <= 1500:
        b = collect.get(f"{DATA_API}/trades", {"market": cid, "limit": 500, "offset": offset, "takerOnly": "true"}, tries=3)
        if not b:
            break
        new = [t for t in b if float(t.get("timestamp") or 0) > t0]
        out += new
        if len(b) < 500 or len(new) < len(b):
            break
        offset += 500
    return out


def tick(now=None):
    now = now or time.time()
    os.makedirs(D, exist_ok=True)
    st = load(); rw = rewards_table()
    if not rw:
        print("no rewards table"); return None
    log = {"ts": int(now), "fills": [], "rewards": 0.0, "settled": []}

    # refresh the universe hourly: books for all reward markets, keep the best 150 candidates
    if now - st["universe_ts"] > 3300 or not st["universe"]:
        cands = []
        ok = {c: r for c, r in rw.items() if not SKIP.search(r["q"]) and not (r["end"] and r["end"] - now < 7 * 86400)}
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
            off = offset(r["v"])
            if not (0.10 < mid < 0.90) or 100 * off >= r["v"] or asks[0][0] - bids[0][0] > MAX_BOOK_SPREAD:
                continue  # a wide book means the mid is not a real price: don't quote around it
            cb, ca = score(bids, mid, r["v"], r["minsize"], True), score(asks, mid, r["v"], r["minsize"], False)
            comp = min(cb, ca) if min(cb, ca) > 0 else max(cb, ca) / 3
            size = max(r["minsize"], SIZE, 20)
            ours = ((r["v"] - 100 * off) / r["v"]) ** 2 * size
            cands.append((r["rate"] * ours / (ours + comp) / size, c))
        st["universe"] = [c for _, c in sorted(cands, reverse=True)[:max(150, 3 * N)]]
        st["universe_ts"] = now
        print(f"universe refreshed: {len(st['universe'])} candidates from {len(ok)} eligible reward markets", flush=True)

    watch = list(dict.fromkeys(st["universe"] + [c for c, p in st["positions"].items() if abs(p["yes"]) > 1e-9 and c not in st["settled"]]))
    books = books_for([rw[c]["token"] for c in watch if c in rw])

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
            if ((oc == 0 and side == "SELL") or (oc == 1 and side == "BUY")) and lb > 0 and yp <= q["bid"] + 1e-9:
                f = min(lb, sz); lb -= f; pos["yes"] += f; st["cash"] -= f * q["bid"]; st["fills"] += 1
                st["rebates"] = st.get("rebates", 0.0) + f * rebate_per_share(q["bid"], q["q"])
                log["fills"].append([cid, "buy", q["bid"], f])
            elif ((oc == 0 and side == "BUY") or (oc == 1 and side == "SELL")) and la > 0 and yp >= q["ask"] - 1e-9:
                f = min(la, sz); la -= f; pos["yes"] -= f; st["cash"] += f * q["ask"]; st["fills"] += 1
                st["rebates"] = st.get("rebates", 0.0) + f * rebate_per_share(q["ask"], q["q"])
                log["fills"].append([cid, "sell", q["ask"], f])
        # 2. rewards for the time rested: full credit if both sides still had size, a third if one side
        dt_days = (now - q["ts"]) / 86400
        both = lb > 0 and la > 0
        one = (lb > 0) != (la > 0)
        credit = q["rpd"] * dt_days * (1 if both else (1 / 3 if one else 0))
        st["rewards"] += credit; log["rewards"] += credit
    st["quotes"] = {}

    # 3. mark to mid; settle closed markets
    for cid, pos in st["positions"].items():
        bk = books.get(rw.get(cid, {}).get("token"))
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
    ranked = []
    for cid in watch:
        r = rw.get(cid); bk = books.get(r["token"]) if r else None
        if not bk:
            continue
        bids, asks = book_view(bk)
        if not bids or not asks:
            continue
        mid = (bids[0][0] + asks[0][0]) / 2
        if not (0.05 < mid < 0.95):
            continue
        off = offset(r["v"])
        wide = asks[0][0] - bids[0][0] > MAX_BOOK_SPREAD
        cb, ca = score(bids, mid, r["v"], r["minsize"], True), score(asks, mid, r["v"], r["minsize"], False)
        comp = min(cb, ca) if min(cb, ca) > 0 else max(cb, ca) / 3
        size = max(r["minsize"], SIZE, 20)
        ours = ((r["v"] - 100 * off) / r["v"]) ** 2 * size
        rpd = 0.0 if wide else r["rate"] * ours / (ours + comp)
        # tape filter: recent taker trades big and all one way -> informed flow, stand aside
        tape = sorted(tr.get(cid, []), key=lambda t: float(t["timestamp"]))[-TAPE_N:]
        if len(tape) == TAPE_N and all(float(t["price"]) * float(t["size"]) >= TAPE_USD for t in tape):
            dirs = {((t.get("side") == "BUY") == (int(t.get("outcomeIndex") or 0) == 0)) for t in tape}
            if len(dirs) == 1:
                st["tape_skips"] = st.get("tape_skips", 0) + 1
                rpd = 0.0
        hist = [p for _, p in st["mids"].get(cid, [])][-36:]
        vol = (sum((b - a) ** 2 for a, b in zip(hist, hist[1:])) / max(len(hist) - 1, 1)) ** 0.5 if len(hist) > 3 else 0.01
        ranked.append((rpd / (size * (1 + 20 * vol)), cid, mid, size, rpd))
    ranked.sort(reverse=True)
    chosen = {c for sc_, c, *_ in ranked[:N] if sc_ > 0}
    for _, cid, mid, size, rpd in ranked:
        pos = st["positions"].get(cid, {"yes": 0.0})
        inv = pos["yes"]
        if cid not in chosen and abs(inv) < 1e-9:
            continue
        tpl = template(rw[cid]["q"])
        exit_only = cid not in chosen
        off = offset(rw[cid]["v"])
        centre = mid - SKEW * (inv / size)
        bid = round(centre - off, 3); ask = round(centre + off, 3)
        over_cap = fam.get(EVM.get(cid) or tpl, 0) > EVENT_CAP
        want_bid = inv < 2 * size and not (exit_only and inv >= 0) and not (over_cap and inv >= 0)
        want_ask = inv > -2 * size and not (exit_only and inv <= 0) and not (over_cap and inv <= 0)
        if exit_only:  # only work the position off, at the mid, no reward expected
            bid, ask = (round(mid - 0.005, 3), None) if inv < 0 else (None, round(mid + 0.005, 3))
            want_bid, want_ask = inv < 0, inv > 0
        st["quotes"][cid] = {"ts": int(now), "q": rw[cid]["q"], "tpl": tpl, "token": rw[cid]["token"], "size": size if not exit_only else abs(inv),
                             "bid": bid if want_bid and 0 < bid < 1 else None, "ask": ask if want_ask and ask and 0 < ask < 1 else None,
                             "rpd": 0.0 if exit_only else rpd}
    st["ticks"] += 1
    mtm = sum(p["yes"] * p.get("mid", 0.5) for p in st["positions"].values())
    capital = sum(q["size"] * ((q["bid"] or 0) + (1 - (q["ask"] or 1))) for q in st["quotes"].values() if q["rpd"] > 0)
    rep = {"variant": VARIANT, "updated": datetime.fromtimestamp(now, timezone.utc).isoformat(), "ticks": st["ticks"], "fills": st["fills"],
           "rewards_earned": round(st["rewards"], 2), "maker_rebates": round(st.get("rebates", 0.0), 2),
           "trading_cash": round(st["cash"], 2), "inventory_value_at_mid": round(mtm, 2),
           "total_pnl": round(st["cash"] + mtm + st["rewards"] + st.get("rebates", 0.0), 2), "quoting": sum(1 for q in st["quotes"].values() if q["rpd"] > 0),
           "exit_only": sum(1 for q in st["quotes"].values() if q["rpd"] == 0), "capital_in_quotes_now": round(capital, 2),
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
