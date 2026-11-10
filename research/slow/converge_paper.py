"""Favourite-convergence paper tracker (NO ORDERS). The 6-month history backtest says: buying the side priced 0.90-0.97
with 1-14 days to resolution returned +2-6% per position with a ~99% hit rate (daily last-trade prices). This checks it
with real executable prices: every run scans active binary markets ending in 1-14 days, and for each new candidate reads
the CLOB order book of the favoured side and 'buys' $20 at the best ask if the size is there. Positions settle on the
official outcome. State: data/slow/converge_positions.jsonl; summary: data/slow/converge_report.json.
Excluded: crypto up/down windows and anything already held. Env: LO (0.90) HI (0.97) DMIN (1) DMAX (14) STAKE (20)."""
import json, os, re, time, datetime as dt
from collections import defaultdict
import requests

GAMMA = "https://gamma-api.polymarket.com"; CLOB = "https://clob.polymarket.com"; D = "data/slow"; os.makedirs(D, exist_ok=True)
LO, HI = float(os.environ.get("LO", "0.90")), float(os.environ.get("HI", "0.98")); DMIN, DMAX = float(os.environ.get("DMIN", "1")), float(os.environ.get("DMAX", "30"))
STAKE = float(os.environ.get("STAKE", "20")); MAX_NEW = int(os.environ.get("MAX_NEW", "40")); MAX_NEW_NO = int(os.environ.get("MAX_NEW_NO", "5"))
# 11-10 history (6,570 markets): the edge is YES 0.95-0.98 in NON-sports markets (393 positions 100% +2.4% at 3-7 d; 14-30 d +2.1%);
# sports favourites at the same price LOSE (live games flip), and the NO side is ~0. Sports are skipped; NO is kept as a small control.
SPORT = re.compile(r"\b(vs\.?|nba|nfl|nhl|mlb|ncaa|ufc|mma|premier|la liga|serie a|bundesliga|ligue|champions|europa|mls|atp|wta|tennis|open|cup|league|match|game|win on|spread|o/u|over/under|f1|grand prix|boxing|fight|cricket|rugby|golf|pga|nascar|esports|lol|cs2|dota|valorant)\b", re.I)
S = requests.Session(); S.headers["User-Agent"] = "polymarket-lab-research/0.1"
SKIP = re.compile(r"updown|up-or-down|-5m-|-15m-|-4h-", re.I)
POS = f"{D}/converge_positions.jsonl"


def get(url, params, tries=3):
    for i in range(tries):
        try:
            r = S.get(url, params=params, timeout=20)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 429:
                time.sleep(2 + 2 * i); continue
            return None
        except Exception:  # noqa: BLE001
            time.sleep(1 + i)
    return None


positions = []
try:
    positions = [json.loads(l) for l in open(POS)]
except OSError:
    pass
held = {p["id"] for p in positions}
now = dt.datetime.now(dt.timezone.utc)

# 1. settle open positions
n_settled = 0
for p in positions:
    if p.get("resolved"):
        continue
    m = get(f"{GAMMA}/markets/{p['id']}", {})
    if not m:
        continue
    try:
        prices = [float(x) for x in json.loads(m.get("outcomePrices") or "[]")]
    except ValueError:
        continue
    p["now_p"] = prices[0] if prices else None
    if m.get("closed") and prices and max(prices) >= 0.99:
        y = int(prices[0] > prices[1]); win = (y == 1) == (p["side"] == "YES")
        fee = 0.07 * p["ask"] * (1 - p["ask"])
        p.update(resolved=True, y=y, won=int(win), pnl=round(p["shares"] * ((1 if win else 0) - p["ask"] - fee), 2), settled=now.strftime("%Y-%m-%d %H:%M"))
        n_settled += 1

# 2. scan for new candidates
cands = []; offset = 0
while offset < 3000:
    page = get(f"{GAMMA}/markets", {"active": "true", "closed": "false", "limit": 100, "offset": offset, "end_date_min": (now + dt.timedelta(days=DMIN)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                                    "end_date_max": (now + dt.timedelta(days=DMAX)).strftime("%Y-%m-%dT%H:%M:%SZ")})
    if not page:
        break
    offset += 100
    for m in page:
        if m["id"] in held or SKIP.search(m.get("slug") or ""):
            continue
        try:
            prices = [float(x) for x in json.loads(m.get("outcomePrices") or "[]")]; toks = json.loads(m.get("clobTokenIds") or "[]")
            end = dt.datetime.fromisoformat(m["endDate"].replace("Z", "+00:00"))
        except (ValueError, KeyError, TypeError):
            continue
        if len(prices) != 2 or len(toks) != 2 or float(m.get("volumeNum") or 0) < 2000:
            continue
        side = "YES" if LO <= prices[0] <= HI else "NO" if LO <= prices[1] <= HI else None
        ev_title = ((m.get("events") or [{}])[0].get("title") if m.get("events") else "") or ""
        if side and not SPORT.search(f"{m.get('question') or ''} {m.get('slug') or ''} {ev_title}"):
            cands.append((m, side, toks[0] if side == "YES" else toks[1], prices, end))
    if len(page) < 100:
        break
cands.sort(key=lambda c: c[1] != "YES")        # YES first: that is the strategy; NO is the control
print(f"open positions {sum(1 for p in positions if not p.get('resolved'))}, settled now {n_settled}, candidates {len(cands)}", flush=True)

# 3. paper-buy at the real best ask
n_new = 0; n_new_no = 0
for m, side, tok, prices, end in cands[:MAX_NEW * 3]:
    if n_new >= MAX_NEW or (side == "NO" and n_new_no >= MAX_NEW_NO):
        if side == "NO" and n_new < MAX_NEW:
            continue
        break
    book = get(f"{CLOB}/book", {"token_id": tok})
    asks = sorted(((float(a["price"]), float(a["size"])) for a in (book or {}).get("asks", [])), key=lambda x: x[0]) if book else []
    if not asks:
        continue
    ask, size = asks[0]
    if not (LO <= ask <= HI + 0.015) or size * ask < STAKE:
        continue
    shares = round(STAKE / ask, 2)
    positions.append({"id": m["id"], "slug": m.get("slug"), "question": m.get("question"), "side": side, "ask": ask, "ask_size": size, "mid_at_entry": prices[0],
                      "shares": shares, "stake": STAKE, "end": end.strftime("%Y-%m-%d %H:%M"), "days_left": round((end - now).total_seconds() / 86400, 1),
                      "opened": now.strftime("%Y-%m-%d %H:%M"), "volume": float(m.get("volumeNum") or 0), "resolved": False})
    held.add(m["id"]); n_new += 1; n_new_no += side == "NO"
with open(POS, "w") as fh:
    for p in positions:
        fh.write(json.dumps(p, ensure_ascii=False) + "\n")

# 4. report
done = [p for p in positions if p.get("resolved")]; openp = [p for p in positions if not p.get("resolved")]
by_band = defaultdict(lambda: [0, 0, 0.0, 0.0])
for p in done:
    for k in ("0.90-0.94" if p["ask"] < 0.94 else "0.94-0.97+", "side " + p["side"], "sports" if SPORT.search(p["question"] + " " + (p.get("slug") or "")) else "non-sports"):
        b = by_band[k]; b[0] += 1; b[1] += p["won"]; b[2] += p["stake"]; b[3] += p["pnl"]
rep = {"updated": now.strftime("%Y-%m-%d %H:%M"), "open": len(openp), "new_this_run": n_new, "settled": len(done), "won": sum(p["won"] for p in done),
       "pnl": round(sum(p["pnl"] for p in done), 2), "staked_settled": round(sum(p["stake"] for p in done), 2),
       "by_band": {k: {"n": v[0], "won": v[1], "pnl": round(v[3], 2), "ret": round(v[3] / v[2], 4) if v[2] else None} for k, v in by_band.items()},
       "open_mark": round(sum(p["shares"] * ((p["now_p"] if p["side"] == "YES" else 1 - p["now_p"]) - p["ask"]) for p in openp if p.get("now_p") is not None), 2),
       "open_by_side": {sd: sum(1 for p in openp if p["side"] == sd) for sd in ("YES", "NO")},
       "avg_ask": round(sum(p["ask"] for p in positions) / len(positions), 4) if positions else None, "avg_days": round(sum(p["days_left"] for p in positions) / len(positions), 1) if positions else None}
json.dump(rep, open(f"{D}/converge_report.json", "w"), indent=1)
print(json.dumps(rep))
for p in positions[-n_new:] if n_new else []:
    print(f"  new: {p['side']:3} {p['ask']:.3f} x {p['shares']:5.1f} {p['days_left']:4.1f}d  {p['question'][:80]}")
