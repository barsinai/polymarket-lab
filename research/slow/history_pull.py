"""Pull the history we need for the slow-market backtests (read-only): resolved Polymarket markets of the last
MONTHS months with their daily price path, from Gamma (market list, outcome) and the CLOB prices-history endpoint.
Writes data/history/markets.jsonl (one line per market: question, category tags, end/start, final outcome, volume,
liquidity) and data/history/prices/<market id>.json (daily YES prices). Skips the crypto Up/Down windows (there are
thousands, and they are their own study). Resumable: markets already on disk are not fetched again.
"""
import json, os, re, time, collections, datetime as dt
from concurrent.futures import ThreadPoolExecutor
import requests

GAMMA = "https://gamma-api.polymarket.com"; CLOB = "https://clob.polymarket.com"
D = "data/history"; os.makedirs(f"{D}/prices", exist_ok=True)
MONTHS = float(os.environ.get("MONTHS", "6")); MIN_VOL = float(os.environ.get("MIN_VOL", "2000")); MAX_MARKETS = int(os.environ.get("MAX_MARKETS", "6000"))
S = requests.Session(); S.headers["User-Agent"] = "polymarket-lab-research/0.1"
SKIP = re.compile(r"updown|up-or-down|-5m-|-15m-|-4h-|will-.*-be-above|price-of-.*-on", re.I)


def get(url, params, tries=4):
    for i in range(tries):
        try:
            r = S.get(url, params=params, timeout=25)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 429:
                time.sleep(3 + 3 * i); continue
            return None
        except Exception:  # noqa: BLE001
            time.sleep(1 + i)
    return None


have = set()
try:
    for l in open(f"{D}/markets.jsonl"):
        have.add(json.loads(l)["id"])
except OSError:
    pass
since = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=30.5 * MONTHS)
out = open(f"{D}/markets.jsonl", "a"); n_new = 0; offset = 0
todo = []; n_seen = 0; n_skip = collections.Counter(); seen_ids = set()
# Gamma caps how deep an offset can go, so walk the period in 7-day end-date windows
win_end = dt.datetime.now(dt.timezone.utc)
while win_end > since and len(todo) + len(have) < MAX_MARKETS:
    win_start = max(since, win_end - dt.timedelta(days=7)); offset = 0
    while offset < 20000:
        page = get(f"{GAMMA}/markets", {"closed": "true", "limit": 100, "offset": offset, "end_date_min": win_start.strftime("%Y-%m-%dT%H:%M:%SZ"), "end_date_max": win_end.strftime("%Y-%m-%dT%H:%M:%SZ")})
        if not page:
            break
        offset += 100; n_seen += len(page)
        for m in page:
            if m["id"] in seen_ids:
                continue
            seen_ids.add(m["id"])
            try:
                end = dt.datetime.fromisoformat((m.get("endDate") or "").replace("Z", "+00:00"))
            except ValueError:
                n_skip["no_end"] += 1; continue
            if m["id"] in have:
                n_skip["have"] += 1; continue
            if SKIP.search(m.get("slug") or ""):
                n_skip["updown"] += 1; continue
            if float(m.get("volumeNum") or 0) < MIN_VOL:
                n_skip["volume"] += 1; continue
            try:
                prices = [float(x) for x in json.loads(m.get("outcomePrices") or "[]")]; toks = json.loads(m.get("clobTokenIds") or "[]")
            except ValueError:
                n_skip["parse"] += 1; continue
            if len(prices) != 2 or max(prices) < 0.99 or len(toks) != 2:
                n_skip["unresolved_or_multi"] += 1; continue
            todo.append((m, end, prices, toks))
        if len(page) < 100:
            break
    print(f"window {win_start:%m-%d}..{win_end:%m-%d}: pages {offset // 100}, todo so far {len(todo)}", flush=True)
    win_end = win_start
print("markets seen", n_seen, "skipped", dict(n_skip))
print("resolved binary markets to fetch:", len(todo), "(already had", len(have), ")", flush=True)


def fetch(item):
    m, end, prices, toks = item
    start = m.get("startDate") or m.get("createdAt") or ""
    try:
        st = dt.datetime.fromisoformat(start.replace("Z", "+00:00"))
    except ValueError:
        st = end - dt.timedelta(days=60)
    span_days = max(1, (end - st).days + 1)
    fid = "max" if span_days > 30 else "1m"
    h = get(f"{CLOB}/prices-history", {"market": toks[0], "interval": fid, "fidelity": 1440 if span_days > 30 else 360})
    hist = [(int(p["t"]), float(p["p"])) for p in (h or {}).get("history", [])] if h else []
    rec = {"id": m["id"], "slug": m.get("slug"), "question": m.get("question"), "end": end.strftime("%Y-%m-%dT%H:%M"), "start": st.strftime("%Y-%m-%dT%H:%M"),
           "yes_won": int(prices[0] > prices[1]), "volume": float(m.get("volumeNum") or 0), "liquidity": float(m.get("liquidityNum") or 0),
           "event": ((m.get("events") or [{}])[0].get("title") if m.get("events") else None), "tags": [t.get("label") for t in (m.get("tags") or []) if isinstance(t, dict)],
           "neg_risk": bool(m.get("negRisk")), "n_prices": len(hist), "yes_token": toks[0]}
    if hist:
        json.dump(hist, open(f"{D}/prices/{m['id']}.json", "w"))
    return rec


with ThreadPoolExecutor(4) as ex:
    for rec in ex.map(fetch, todo):
        out.write(json.dumps(rec, ensure_ascii=False) + "\n"); n_new += 1
        if n_new % 200 == 0:
            out.flush(); print("fetched", n_new, flush=True)
out.close()
print("done: new markets", n_new, "total", len(have) + n_new)
