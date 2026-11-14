"""N2b box-office Saturday favourite, paper tracker (NO ORDERS).
History (boxoffice_census.py, 134 films / 78 weekends 2024-02..2026-03, hourly last prices): on Saturday 14-02 UTC (Friday's
gross incl. previews is public) the side of an opening-weekend bracket priced 0.80-0.97 won 95% at an average 0.91:
+4.1%/$ at +1c cost, +2.9% at +2c; 2024..2025H1 -2%, 2025H2..2026Q1 +6..+8%. This checks it at REAL asks.
Entry window: Saturday 14:00 .. Sunday 02:00 UTC; markets whose question names 'Box Office' and end within 4 days; side with
best ask in 0.80-0.97 and >= $10 at that ask; $10 each, once per market. Settles on gamma outcomePrices.
State data/slow/boxoffice_positions.jsonl; summary data/slow/boxoffice_report.json. Env FORCE=1 enters outside the window."""
import json, os, time, datetime as dt
import requests

GAMMA = "https://gamma-api.polymarket.com"; CLOB = "https://clob.polymarket.com"; D = "data/slow"
POS = f"{D}/boxoffice_positions.jsonl"; STAKE = 10.0; LO, HI = 0.80, 0.97
S = requests.Session(); S.headers["User-Agent"] = "polymarket-lab-research/0.1"


def get(url, params=None):
    for i in range(3):
        try:
            r = S.get(url, params=params, timeout=20)
            if r.status_code == 200:
                return r.json()
            if r.status_code != 429:
                return None
        except Exception:  # noqa: BLE001
            pass
        time.sleep(1 + 2 * i)
    return None


def best(book, side):
    lv = sorted(((float(a["price"]), float(a["size"])) for a in (book or {}).get(side, [])), key=lambda x: x[0], reverse=(side == "bids"))
    return lv[0] if lv else (None, 0)


os.makedirs(D, exist_ok=True)
pos = [json.loads(l) for l in open(POS)] if os.path.exists(POS) else []
held = {p["id"] for p in pos}
now = dt.datetime.now(dt.timezone.utc)
for p in pos:
    if p.get("resolved"):
        continue
    m = get(f"{GAMMA}/markets/{p['id']}")
    try:
        pr = [float(x) for x in json.loads((m or {}).get("outcomePrices") or "[]")]
    except ValueError:
        pr = []
    if m and m.get("closed") and pr and max(pr) >= 0.99:
        y = int(pr[0] > pr[1]); win = (y == 1) == (p["side"] == "YES")
        p.update(resolved=True, y=y, won=int(win), pnl=round(p["shares"] * (1 if win else 0) - STAKE, 2), settled=now.strftime("%Y-%m-%d %H:%M"))

in_window = (now.weekday() == 5 and now.hour >= 14) or (now.weekday() == 6 and now.hour < 2) or os.environ.get("FORCE") == "1"
def candidates():
    """11-14 c13 fix: the old loop paged every market ending in 4 days with a 4,000 offset cap; up/down crypto markets fill that
    window, so on the first live Saturday it saw 0 box-office markets while LP-1 was quoting 'Ebenezer Opening Weekend'.
    Now: text search + event listings first (few calls), the paged scan only as a fallback. Returns {market id: market}."""
    out = {}; srcs = {}
    def add(ms, src):
        for m in ms or []:
            if "box office" in (m.get("question") or "").lower() and not m.get("closed"):
                out.setdefault(str(m["id"]), m); srcs[src] = srcs.get(src, 0) + 1
    for q in ("box office", "opening weekend"):
        r = get(f"{GAMMA}/public-search", {"q": q, "events_status": "active", "limit_per_type": 50})
        for e in (r or {}).get("events", []) or []:
            ms = e.get("markets")
            if not ms and e.get("id"):
                ms = (get(f"{GAMMA}/events/{e['id']}") or {}).get("markets")
            add(ms, "search")
    for tag in ("box-office", "movies"):
        for e in get(f"{GAMMA}/events", {"tag_slug": tag, "active": "true", "closed": "false", "limit": 100}) or []:
            add(e.get("markets"), "tag")
    if not out:
        off = 0
        while off < 20000:
            page = get(f"{GAMMA}/markets", {"active": "true", "closed": "false", "limit": 100, "offset": off,
                       "end_date_min": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "end_date_max": (now + dt.timedelta(days=6)).strftime("%Y-%m-%dT%H:%M:%SZ")})
            if not page:
                break
            add(page, "paged"); off += 100
            if len(page) < 100:
                break
    return out, srcs


n_new = 0; seen = 0; sources = {}
if in_window:
    cands, sources = candidates()
    for mid, m in cands.items():
        q = m.get("question") or ""
        end = m.get("endDate") or ""
        try:
            if dt.datetime.fromisoformat(end.replace("Z", "+00:00")) > now + dt.timedelta(days=6):
                continue
        except ValueError:
            pass
        if m["id"] in held:
            continue
        try:
            toks = json.loads(m.get("clobTokenIds") or "[]")
        except (ValueError, TypeError):
            continue
        if len(toks) != 2:
            continue
        seen += 1
        for side, tok in (("YES", toks[0]), ("NO", toks[1])):
            book = get(f"{CLOB}/book", {"token_id": tok})
            ask, size = best(book, "asks"); bid, _ = best(book, "bids")
            if ask is None or not (LO <= ask <= HI) or ask * size < STAKE:
                continue
            pos.append({"id": m["id"], "question": q, "side": side, "ask": ask, "ask_size": size, "bid": bid,
                        "spread": round(ask - bid, 4) if bid else None, "shares": round(STAKE / ask, 2), "stake": STAKE,
                        "end": m.get("endDate"), "opened": now.strftime("%Y-%m-%d %H:%M"), "resolved": False})
            held.add(m["id"]); n_new += 1
            break
with open(POS, "w") as fh:
    for p in pos:
        fh.write(json.dumps(p, ensure_ascii=False) + "\n")
done = [p for p in pos if p.get("resolved")]
sp = [p["spread"] for p in pos if p.get("spread") is not None]
rep = {"updated": now.strftime("%Y-%m-%d %H:%M"), "in_window": in_window, "box_office_markets_seen": seen, "sources": sources, "new": n_new,
       "open": len(pos) - len(done), "settled": len(done), "won": sum(p["won"] for p in done), "pnl": round(sum(p["pnl"] for p in done), 2),
       "staked_settled": STAKE * len(done), "median_spread": sorted(sp)[len(sp) // 2] if sp else None,
       "weekends": len({p["opened"][:10] for p in pos})}
json.dump(rep, open(f"{D}/boxoffice_report.json", "w"), indent=1)
print(json.dumps(rep))
