"""LP-1 paper simulation (NO ORDERS, 11-13): be the sole two-sided liquidity provider in UNCONTESTED reward markets.

Why: Polymarket pays ~$121k/day of liquidity rewards; lp_screen.py found 837 of the 1,487 largest pools (>= $10/day, $22k/day)
with NO quote inside the reward band (empty books), persistent for days. By the published rules a lone two-sided maker scores
100% of a market's pool. What paper CAN measure: (1) fills - every public taker trade that would have hit our quotes (we would be
the best bid/ask in an empty book), and what they cost against the later price / the resolution; (2) whether competitors arrive;
(3) the reward the published formula promises. What paper CANNOT measure: what Polymarket actually pays ('silent zeros', the
pilot's 1/5) - that needs real orders.

Each hourly run:
  - universe: reward markets (CLOB sampling-markets) with pool >= MIN_POOL and min size <= MAX_MIN, top N_MAX by pool; a fair price
    = manual override (data/slow/lp_fair.json) else Polymarket's displayed price (Gamma outcomePrices: mid when the spread <= 10c,
    else the last trade) - and only if the market has traded in the last FAIR_DAYS days (otherwise no basis for a price: skipped);
  - our quotes: bid = fair - 1c, ask = fair + 1c on the tick grid, size = the market's min size, two-sided;
  - competition = other orders scoring inside the band around OUR mid (formula score), our formula share = ours / (ours + comp);
  - fills: book orders crossing our quotes (we would take them at their price) + public taker trades since the last run that would
    have reached us (buy YES at >= our ask, sell YES at <= our bid), up to our size per side per run;
  - formula reward accrued = pool x share x hours/24; inventory marked at the current fair; settled at resolution.
State data/slow/lp_paper_state.json, report data/slow/lp_paper_report.json. Env: MIN_POOL (10) MAX_MIN (100) N_MAX (60) FAIR_DAYS (14)."""
import json, math, os, sys, time, datetime as dt
import requests
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import collect  # noqa: E402

D = "data/slow"; ST = f"{D}/lp_paper_state.json"; REP = f"{D}/lp_paper_report.json"; FAIR = f"{D}/lp_fair.json"
MIN_POOL = float(os.environ.get("MIN_POOL", "10")); MAX_MIN = float(os.environ.get("MAX_MIN", "100"))
N_MAX = int(os.environ.get("N_MAX", "60")); FAIR_DAYS = float(os.environ.get("FAIR_DAYS", "14"))
now = time.time(); T0 = now


def score(levels, mid, v, ms, is_bid):
    s_ = 0.0
    for p, sz in levels:
        s = 100 * ((mid - p) if is_bid else (p - mid))
        if 0 <= s < v and sz >= ms:
            s_ += ((v - s) / v) ** 2 * sz
    return s_


st = json.load(open(ST)) if os.path.exists(ST) else {"markets": {}, "runs": 0, "started": int(now)}
manual = json.load(open(FAIR)) if os.path.exists(FAIR) else {}

# 1. reward configs
cfg = {}; cur = ""
for _ in range(600):
    d = collect.get(f"{collect.CLOB}/sampling-markets", {"next_cursor": cur}, tries=3)
    if not d:
        break
    for m in d.get("data") or []:
        r = m.get("rewards") or {}
        rate = sum(x.get("rewards_daily_rate") or 0 for x in r.get("rates") or [])
        toks = [str(t.get("token_id")) for t in m.get("tokens") or []]
        if rate > 0 and m.get("condition_id") and len(toks) == 2 and m.get("accepting_orders", True):
            cfg[m["condition_id"]] = {"rate": rate, "min": float(r.get("min_size") or 0), "v": float(r.get("max_spread") or 0),
                                      "tick": float(m.get("minimum_tick_size") or 0.01), "toks": toks, "q": (m.get("question") or "")[:120]}
    cur = d.get("next_cursor") or ""
    if not cur or cur == "LTE=":
        break
print("reward markets", len(cfg), flush=True)

# 2. candidates: ours already held + new ones by pool size
held = [c for c, x in st["markets"].items() if x.get("active")]
new = sorted((c for c in cfg if c not in st["markets"] and cfg[c]["rate"] >= MIN_POOL and 0 < cfg[c]["min"] <= MAX_MIN and cfg[c]["v"] > 1),
             key=lambda c: -cfg[c]["rate"])
cands = held + new[:max(0, 4 * N_MAX - len(held))]
# displayed prices (Gamma) for the candidates
gm = {}
for i in range(0, len(cands), 40):
    for m in collect.get(f"{collect.GAMMA}/markets", [("condition_ids", c) for c in cands[i:i + 40]] + [("limit", 100)], tries=3) or []:
        gm[m.get("conditionId")] = m
books = {}
toks = [cfg[c]["toks"][0] for c in cands if c in cfg]
for i in range(0, len(toks), 50):
    try:
        rr = requests.post(f"{collect.CLOB}/books", json=[{"token_id": t} for t in toks[i:i + 50]], timeout=30)
        for b in (rr.json() if rr.status_code == 200 else []):
            books[str(b.get("asset_id"))] = b
    except Exception:  # noqa: BLE001
        pass

active_n = sum(1 for c in held if c in cfg)
for c in cands:
    if time.time() - T0 > 240:
        break
    x = st["markets"].get(c); g = gm.get(c) or {}; k = cfg.get(c)
    # settle closed markets
    if g.get("closed") and x:
        try:
            pr = [float(p) for p in json.loads(g.get("outcomePrices") or "[]")]
        except Exception:  # noqa: BLE001
            pr = []
        if pr and max(pr) >= 0.99 and x.get("active"):
            yes_pay = 1.0 if pr[0] >= 0.99 else 0.0
            x["cash"] += x["inv"] * yes_pay; x["inv"] = 0.0; x["active"] = False; x["settled"] = yes_pay
        continue
    if not k:
        if x:
            x["active"] = False; x["why_off"] = "pool removed"
        continue
    if not x and active_n >= N_MAX:
        continue
    # fair price
    fair, src = None, None
    if c in manual:
        fair, src = float(manual[c]["fair"]), "manual"
    else:
        try:
            fair = float(json.loads(g.get("outcomePrices") or "[]")[0]); src = "displayed"
        except Exception:  # noqa: BLE001
            fair = None
    tr_all = collect.trades_since(c, (x or {}).get("last_ts", now - FAIR_DAYS * 86400), max_rows=500)
    if not x:
        if src != "manual" and not tr_all:
            continue                                      # never traded recently: no basis for a price
        if fair is None or not (0.02 <= fair <= 0.98):
            continue
        x = st["markets"][c] = {"q": k["q"], "opened": int(now), "inv": 0.0, "cash": 0.0, "reward": 0.0, "fills": [], "comp_runs": 0,
                                "runs": 0, "active": True, "last_ts": now, "fair0": fair, "src": src}
        active_n += 1
        tr_all = []                                       # trades before we started quoting are not fills
    if not x.get("active"):
        continue
    tick = k["tick"]; size = max(k["min"], 5.0)
    bid = max(tick, math.floor(round((fair - 0.01) / tick, 6)) * tick); ask = min(1 - tick, math.ceil(round((fair + 0.01) / tick, 6)) * tick)
    mid = (bid + ask) / 2
    if 100 * (mid - bid) >= k["v"] or 100 * (ask - mid) >= k["v"]:
        x["why_off"] = "band too narrow for the tick"; continue
    # fills from crossing book orders and from public taker trades since the last run
    b = books.get(k["toks"][0]) or {}
    bl = sorted(((float(o["price"]), float(o["size"])) for o in b.get("bids") or []), reverse=True)
    al = sorted((float(o["price"]), float(o["size"])) for o in b.get("asks") or [])
    left_b, left_a = size, size
    for p, s in bl:                                       # a resting bid above our ask: we would sell to it at its price
        if p > ask and left_a > 0:
            q = min(s, left_a); x["cash"] += p * q; x["inv"] -= q; left_a -= q; x["fills"].append([int(now), "book_sell", p, q, fair])
    for p, s in al:
        if p < bid and left_b > 0:
            q = min(s, left_b); x["cash"] -= p * q; x["inv"] += q; left_b -= q; x["fills"].append([int(now), "book_buy", p, q, fair])
    pb, pa = x.get("bid"), x.get("ask")                # the quotes that were resting since the last run
    tb, ta = size, size
    for t in sorted(tr_all, key=lambda t: float(t["timestamp"] or 0)):
        if pb is None or pa is None:
            break
        p = float(t["price"] or 0); s = float(t["size"] or 0); oi = int(t.get("outcomeIndex") or 0); side = t.get("side")
        buy_yes = (side == "BUY") == (oi == 0); py = p if oi == 0 else 1 - p
        if buy_yes and py >= pa and ta > 0:
            q = min(s, ta); x["cash"] += pa * q; x["inv"] -= q; ta -= q; x["fills"].append([int(t["timestamp"]), "sell", pa, q, fair])
        elif (not buy_yes) and py <= pb and tb > 0:
            q = min(s, tb); x["cash"] -= pb * q; x["inv"] += q; tb -= q; x["fills"].append([int(t["timestamp"]), "buy", pb, q, fair])
    # competition inside the band around our mid (orders that are not ours; we have none on the real book)
    comp = max(min(score(bl, mid, k["v"], k["min"], True), score(al, mid, k["v"], k["min"], False)),
               (score(bl, mid, k["v"], k["min"], True) + score(al, mid, k["v"], k["min"], False)) / 3)
    ours = min(((k["v"] - 100 * (mid - bid)) / k["v"]) ** 2, ((k["v"] - 100 * (ask - mid)) / k["v"]) ** 2) * size
    share = ours / (ours + comp) if ours > 0 else 0.0
    hrs = min((now - x["last_ts"]) / 3600, 2.0) if x["runs"] else 0.0   # the first run only posts; rewards accrue from the next
    x["reward"] += k["rate"] * share * hrs / 24
    x["comp_runs"] += comp > 0; x["runs"] += 1; x["last_ts"] = now
    x.update(fair=fair, src=src, rate=k["rate"], v=k["v"], min=k["min"], bid=bid, ask=ask, share=round(share, 3), comp=round(comp, 1),
             capital=round(size * (bid + 1 - ask), 2))

# 3. report
st["runs"] += 1
ms = st["markets"]
def pnl(x):
    return x["cash"] + x["inv"] * (x.get("fair") or 0)
act = [x for x in ms.values() if x.get("active")]
tot_r = sum(x["reward"] for x in ms.values()); tot_t = sum(pnl(x) for x in ms.values())
days = max((now - st["started"]) / 86400, 1 / 24)
rep = {"updated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M"), "runs": st["runs"], "days": round(days, 2),
       "markets_quoted": len(act), "markets_ever": len(ms), "capital_now": round(sum(x.get("capital", 0) for x in act), 2),
       "pool_quoted_per_day": round(sum(x.get("rate", 0) for x in act), 1),
       "formula_reward": round(tot_r, 2), "fills": sum(len(x["fills"]) for x in ms.values()), "trading_pnl": round(tot_t, 2),
       "net_if_paid_100pct": round(tot_r + tot_t, 2), "net_if_paid_50pct": round(tot_r / 2 + tot_t, 2), "net_if_paid_20pct": round(tot_r / 5 + tot_t, 2),
       "markets_with_competition_seen": sum(1 for x in ms.values() if x["comp_runs"]),
       "worst": sorted(([round(pnl(x), 2), x["q"][:70], len(x["fills"])] for x in ms.values()), key=lambda r: r[0])[:5],
       "top_reward": sorted(([round(x["reward"], 2), x["q"][:70], x.get("share")] for x in ms.values()), key=lambda r: -r[0])[:5]}
json.dump(st, open(ST, "w")); json.dump(rep, open(REP, "w"), indent=1)
print(json.dumps(rep))
