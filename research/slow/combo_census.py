"""Combo (parlay) census from PUBLIC data only (read-only: no keys, no quote requests, no orders).

Polymarket combos are priced by RFQ makers, not by an order book. Two questions:
  H1 (buyer's edge): are combos with logically linked legs priced like independent ones (product of the leg prices)?
  H2 (maker's edge): what do combo buyers lose on average (= what the RFQ makers earn), by number of legs?
Public sources: /v2/biggest-winners (rows of kind 'combo' give wallets that hold combos), /v2/positions/combos?user= (every combo
position of a wallet: legs, entry price, fees, payout, status), Gamma (leg markets), CLOB prices-history (leg price at entry).
Wallets: (a) combo winners (biased towards winners - kept separate), (b) an unbiased sample: recent takers in combo-eligible
markets. This script only collects; the analysis runs locally on data/research/combo_census.json.gz."""
import json, time, gzip, os, random, collections, threading, datetime as dt
from concurrent.futures import ThreadPoolExecutor
import requests

DA = "https://data-api.polymarket.com"; G = "https://gamma-api.polymarket.com"; CLOB = "https://clob.polymarket.com"
RFQ = "https://combos-rfq-api.polymarket.com"
T0 = time.time(); T_MAX = float(os.environ.get("T_MAX", "1700"))
tl = threading.local(); lock = threading.Lock(); nxt = [0.0]; n429 = [0]
DROP = ("icon", "image", "profile_image", "profile_image_optimized", "description", "bio")


def sess():
    if not hasattr(tl, "s"):
        tl.s = requests.Session(); tl.s.headers["User-Agent"] = "polymarket-lab-research/0.1"
    return tl.s


def get(url, params=None, tries=4, pace=0.08, quiet=True):
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
                if not quiet:
                    print("  !", r.status_code, url, str(params)[:120], r.text[:200], flush=True)
                return None
            return r.json()
        except Exception:  # noqa: BLE001
            time.sleep(1 + k)
    return None


def trim(o):
    if isinstance(o, dict):
        return {k: trim(v) for k, v in o.items() if k not in DROP}
    if isinstance(o, list):
        return [trim(x) for x in o]
    return o


def pages(url, params, max_pages, quiet=True):
    out = []; cur = None
    for _ in range(max_pages):
        p = dict(params)
        if cur:
            p["cursor"] = cur
        d = get(url, p, quiet=quiet)
        rows = (d or {}).get("data") if isinstance(d, dict) else None
        if not rows:
            break
        out += rows
        pg = d.get("pagination") or {}
        if not pg.get("has_more") or not pg.get("next_cursor"):
            break
        cur = pg["next_cursor"]
    return out


# 1. biggest winners -> combo rows
winners = []; kinds = collections.Counter()
for tp in (None, "day", "week", "month", "all", "DAY", "WEEK", "MONTH", "ALL"):
    rows = pages(f"{DA}/v2/biggest-winners", dict({"limit": 1000}, **({"time_period": tp} if tp else {})), 6, quiet=False)
    k = collections.Counter(r.get("kind") for r in rows); kinds[str(tp)] = dict(k)
    cw = [trim(r) for r in rows if r.get("kind") == "combo"]
    for r in cw:
        r["_window"] = tp
    winners += cw
    print(f"biggest-winners time_period={tp}: rows {len(rows)} kinds {dict(k)} combo pnl top {[round(float(r.get('pnl') or 0)) for r in cw[:8]]}", flush=True)
if winners:
    print("sample combo winner:", json.dumps(winners[0])[:700], flush=True)
win_wallets = list(dict.fromkeys(r.get("user_id") for r in winners if r.get("user_id")))
print("combo-winner wallets", len(win_wallets), flush=True)

# 2. combo-eligible markets + an unbiased wallet sample from their recent takers
cm = []; cur = None
for _ in range(12):
    d = get(f"{RFQ}/v1/rfq/combo-markets", dict({"limit": 100}, **({"cursor": cur} if cur else {})), quiet=False)
    if not d:
        break
    cm += d.get("markets") or []
    cur = d.get("next_cursor") or (d.get("pagination") or {}).get("next_cursor")
    if not cur:
        break
print("combo markets", len(cm), "tags", collections.Counter(t for m in cm for t in (m.get("tags") or [])).most_common(40), flush=True)
random.seed(11)
samp_w = collections.Counter()
for m in random.sample(cm, min(60, len(cm))):
    d = get(f"{DA}/v2/trades", {"condition_id": m.get("condition_id"), "limit": 500})
    for r in (d or {}).get("data") or []:
        if r.get("proxy_wallet"):
            samp_w[r["proxy_wallet"]] += 1
rand_wallets = [w for w in random.sample(sorted(samp_w), min(2500, len(samp_w))) if w not in set(win_wallets)]
print("unbiased wallet sample", len(rand_wallets), "of", len(samp_w), flush=True)


# 3. combo positions per wallet
def positions(w):
    return w, [trim(r) for r in pages(f"{DA}/v2/positions/combos", {"user": w, "limit": 500}, 8)]


pos = {}; first = True
with ThreadPoolExecutor(5) as ex:
    for w, rows in ex.map(positions, win_wallets[:700] + rand_wallets):
        if rows:
            pos[w] = rows
            if first:
                print("sample combo position:", json.dumps(rows[0])[:2500], flush=True); first = False
        if time.time() - T0 > T_MAX * 0.55:
            ex.shutdown(wait=False, cancel_futures=True); break
n_rand_with = sum(1 for w in rand_wallets if w in pos)
print(f"wallets with combo positions: winners {sum(1 for w in win_wallets if w in pos)}/{len(win_wallets[:700])}, random {n_rand_with}/{len(rand_wallets)}; "
      f"positions {sum(len(v) for v in pos.values())}  ({time.time() - T0:.0f}s, 429s {n429[0]})", flush=True)

# 4. leg markets (Gamma) and leg prices at entry (CLOB minute history)
legc = collections.Counter()
for rows in pos.values():
    for p in rows:
        for lg in p.get("legs") or []:
            if lg.get("leg_condition_id"):
                legc[lg["leg_condition_id"]] += 1
cids = [c for c, _ in legc.most_common(6000)]
mk = {}
for i in range(0, len(cids), 40):
    for m in get(f"{G}/markets", [("condition_ids", c) for c in cids[i:i + 40]] + [("limit", 100)], pace=0.15) or []:
        ev = (m.get("events") or [{}])[0]
        mk[m.get("conditionId")] = {"id": m.get("id"), "slug": m.get("slug"), "q": (m.get("question") or "")[:120], "end": m.get("endDate"),
                                    "closed": m.get("closed"), "op": m.get("outcomePrices"), "tok": m.get("clobTokenIds"), "ev": ev.get("slug"),
                                    "smt": m.get("sportsMarketType"), "gst": m.get("gameStartTime"), "neg": m.get("negRisk")}
    if time.time() - T0 > T_MAX * 0.7:
        break
print("leg markets resolved via Gamma", len(mk), "of", len(cids), flush=True)


def tsof(s):
    try:
        if isinstance(s, (int, float)):
            return float(s) / (1000 if float(s) > 1e11 else 1)
        return dt.datetime.fromisoformat(str(s).replace("Z", "+00:00")).timestamp()
    except Exception:  # noqa: BLE001
        return None


jobs = {}
now = time.time()
allp = [(w, p) for w, rows in pos.items() for p in rows]
random.shuffle(allp)
for w, p in allp:
    t = tsof(p.get("first_entry_at"))
    if not t or now - t > 28 * 86400:
        continue
    for lg in p.get("legs") or []:
        m = mk.get(lg.get("leg_condition_id"))
        try:
            tok = json.loads(m["tok"])[int(lg.get("leg_outcome_index"))] if m else None
        except Exception:  # noqa: BLE001
            tok = None
        if tok:
            jobs[(tok, int(t) // 60 * 60)] = None
    if len(jobs) > 9000:
        break


def price(key):
    tok, t = key
    d = get(f"{CLOB}/prices-history", {"market": tok, "startTs": t - 3600, "endTs": t + 120, "fidelity": 1})
    h = (d or {}).get("history") or []
    pr = [x for x in h if x.get("t", 0) <= t + 60]
    return key, (pr[-1]["p"], pr[-1]["t"]) if pr else None


lp = {}
with ThreadPoolExecutor(5) as ex:
    for key, v in ex.map(price, list(jobs)):
        if v:
            lp[f"{key[0]}|{key[1]}"] = v
        if time.time() - T0 > T_MAX:
            ex.shutdown(wait=False, cancel_futures=True); break
print(f"leg prices at entry: {len(lp)} of {len(jobs)}  ({time.time() - T0:.0f}s, 429s {n429[0]})", flush=True)
os.makedirs("data/research", exist_ok=True)
json.dump({"at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M"), "kinds": kinds, "winners": winners, "win_wallets": win_wallets,
           "rand_wallets": rand_wallets, "positions": pos, "markets": mk, "leg_prices": lp, "combo_markets": [trim(m) for m in cm]},
          gzip.open("data/research/combo_census.json.gz", "wt"), separators=(",", ":"))
print("saved", flush=True)
