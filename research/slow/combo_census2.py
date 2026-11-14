"""Combo (parlay) census, complete version (PUBLIC data only: no keys, no quote requests, no orders).

The default /v2/positions/combos listing hides redeemed winners, so the first census saw only losses. Here every position of the
wallets found there is pulled with explicit statuses (RESOLVED_WIN, RESOLVED_LOSS, OPEN), newest first, back to CUTOFF_DAYS:
  - maker wallets (hold the NO side of combos they quoted): their positions are close to the full list of executed combos, not
    selected by any bettor's outcome -> realised maker margin (H2) and calibration of combo prices;
  - bettor wallets from the unbiased sample -> what buyers lose, whether any requester wins consistently (H1).
For a sample of recent 2-3 leg combos the leg prices at the entry minute are fetched (CLOB minute history) -> combo price vs the
product of its legs, and whether 'cheap' combos (price below the product, legs in different games) hit more often than priced.
Output: data/research/combo_census2.json.gz (compact records)."""
import json, time, gzip, os, random, collections, threading, datetime as dt
from concurrent.futures import ThreadPoolExecutor
import requests

DA = "https://data-api.polymarket.com"; G = "https://gamma-api.polymarket.com"; CLOB = "https://clob.polymarket.com"
T0 = time.time(); T_MAX = float(os.environ.get("T_MAX", "2400")); CUTOFF_DAYS = float(os.environ.get("CUTOFF_DAYS", "45"))
tl = threading.local(); lock = threading.Lock(); nxt = [0.0]; n429 = [0]
W = json.load(open("data/research/combo_wallets.json"))
NOW = time.time(); CUT = NOW - CUTOFF_DAYS * 86400


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
            r = sess().get(url, params=params, timeout=60)
            if r.status_code == 429:
                n429[0] += 1; time.sleep(2.0 * (k + 1)); continue
            if r.status_code != 200:
                if not quiet:
                    print("  !", r.status_code, url, str(params)[:140], r.text[:200], flush=True)
                return None
            return r.json()
        except Exception:  # noqa: BLE001
            time.sleep(1 + k)
    return None


def tsof(s):
    try:
        return dt.datetime.fromisoformat(str(s).replace("Z", "+00:00")).timestamp()
    except Exception:  # noqa: BLE001
        return None


MK = {}            # market_id -> [slug, sports_market_type, event_id, question (non-sports only)]
SORT = [None]      # working sort params, found on the first call


def compact(p):
    legs = []
    for lg in p.get("legs") or []:
        m = lg.get("market") or {}
        mid = m.get("market_id")
        if mid and mid not in MK:
            MK[mid] = [m.get("slug"), m.get("sports_market_type"), (m.get("event") or {}).get("event_id"),
                       None if m.get("sports_market_type") else (m.get("question") or "")[:70]]
        legs.append([mid, lg.get("leg_outcome_index"), (lg.get("leg_status") or "")[:10], m.get("line")])
    return {"oi": p.get("outcome_index"), "st": p.get("status"), "px": p.get("entry_avg_price_usdc"), "cost": p.get("entry_cost_usdc"),
            "fee": p.get("entry_fees_usdc"), "pay": p.get("realized_payout_usdc"), "size": p.get("current_size"),
            "t": tsof(p.get("first_entry_at")), "tr": tsof(p.get("resolved_at")), "n": p.get("legs_total"), "legs": legs}


def wallet(args):
    w, max_pages = args
    out = []
    for st in ("RESOLVED_WIN", "RESOLVED_LOSS", "OPEN"):
        cur = None
        for _ in range(max_pages):
            p = {"user": w, "limit": 1000, "status": st}
            if SORT[0]:
                p.update(SORT[0])
            if cur:
                p["cursor"] = cur
            d = get(f"{DA}/v2/positions/combos", p)
            rows = (d or {}).get("data") if isinstance(d, dict) else None
            if not rows:
                break
            old = 0
            for r in rows:
                c = compact(r)
                if c["t"] and c["t"] < CUT:
                    old += 1; continue
                out.append(c)
            pg = d.get("pagination") or {}
            if (SORT[0] and old == len(rows)) or not pg.get("has_more") or not pg.get("next_cursor"):
                break
            cur = pg["next_cursor"]
    return w, out


# sort params that the endpoint accepts (newest entries first lets us stop at the cutoff)
for cand in ({"sort_by": "FIRST_ENTRY", "sort_direction": "DESC"}, {"sort_by": "FIRST_ENTRY", "sort_direction": "desc"},
             {"sort_by": "FIRST_ENTRY", "sortDirection": "DESC"}, {"sort_by": "FIRST_ENTRY"}):
    d = get(f"{DA}/v2/positions/combos", dict({"user": W["makers"][0], "limit": 3, "status": "RESOLVED_WIN"}, **cand), quiet=False)
    rows = (d or {}).get("data") if isinstance(d, dict) else None
    if rows:
        print("sort", cand, "->", [r.get("first_entry_at") for r in rows], flush=True)
        if rows[0].get("first_entry_at", "") >= rows[-1].get("first_entry_at", ""):
            SORT[0] = cand; break
print("using sort", SORT[0], flush=True)

pos = {}
with ThreadPoolExecutor(5) as ex:
    jobs = [(w, 60) for w in W["makers"]] + [(w, 6) for w in W["bettors"]]
    for w, rows in ex.map(wallet, jobs):
        pos[w] = rows
        if w in W["makers"]:
            c = collections.Counter(r["st"] for r in rows)
            print(f"maker {w[:10]} positions {len(rows)} {dict(c)}  ({time.time() - T0:.0f}s)", flush=True)
        if time.time() - T0 > T_MAX * 0.5:
            ex.shutdown(wait=False, cancel_futures=True); break
print(f"wallets {len(pos)}, positions {sum(len(v) for v in pos.values())}, leg markets {len(MK)}  ({time.time() - T0:.0f}s, 429s {n429[0]})", flush=True)

# leg prices at the entry minute for a sample of recent maker-side combos with 2-3 legs
random.seed(5)
cand = [(w, i) for w in W["makers"] for i, r in enumerate(pos.get(w, [])) if r["t"] and NOW - r["t"] < 12 * 86400 and r["n"] in (2, 3)
        and r["oi"] == 1 and all(l[0] for l in r["legs"])]
random.shuffle(cand); cand = cand[:5000]
mids = sorted({l[0] for w, i in cand for l in pos[w][i]["legs"]})
tok = {}
for i in range(0, len(mids), 40):
    for extra in ([("closed", "true")], []):                    # list endpoints leave closed markets out unless asked
        for m in get(f"{G}/markets", [("id", x) for x in mids[i:i + 40]] + [("limit", 100)] + extra, pace=0.15) or []:
            try:
                tok[str(m.get("id"))] = [json.loads(m.get("clobTokenIds") or "[]"), m.get("gameStartTime"), m.get("volumeNum"), m.get("liquidityNum")]
            except Exception:  # noqa: BLE001
                pass
    if time.time() - T0 > T_MAX * 0.65:
        break
print("leg tokens", len(tok), "of", len(mids), flush=True)
jobs = {}
for w, i in cand:
    r = pos[w][i]
    for l in r["legs"]:
        t = tok.get(str(l[0]))
        try:
            tk = t[0][int(l[1])]
        except Exception:  # noqa: BLE001
            tk = None
        if tk:
            jobs[(tk, int(r["t"]) // 60 * 60)] = (str(l[0]), int(l[1]))


def price(key):
    tk, t = key
    d = get(f"{CLOB}/prices-history", {"market": tk, "startTs": t - 1800, "endTs": t + 60, "fidelity": 1})
    h = (d or {}).get("history") or []
    if not h:                                                  # older closed markets may keep only coarser history
        d = get(f"{CLOB}/prices-history", {"market": tk, "startTs": t - 7200, "endTs": t + 60, "fidelity": 10})
        h = (d or {}).get("history") or []
    pr = [x for x in h if x.get("t", 0) <= t + 30]
    return key, (pr[-1]["p"], pr[-1]["t"]) if pr else None


lp = {}
with ThreadPoolExecutor(5) as ex:
    for key, v in ex.map(price, list(jobs)):
        if v:
            mid, oi = jobs[key]
            lp[f"{mid}|{oi}|{key[1]}"] = v
        if time.time() - T0 > T_MAX:
            ex.shutdown(wait=False, cancel_futures=True); break
print(f"leg prices at entry {len(lp)} of {len(jobs)}  ({time.time() - T0:.0f}s, 429s {n429[0]})", flush=True)
json.dump({"at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M"), "cutoff_days": CUTOFF_DAYS, "makers": W["makers"], "positions": pos,
           "markets": MK, "tok": tok, "leg_prices": lp, "sample": [[w, i] for w, i in cand]},
          gzip.open("data/research/combo_census2.json.gz", "wt"), separators=(",", ":"))
print("saved", flush=True)
