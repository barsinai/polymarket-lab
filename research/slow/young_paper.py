"""Young-market NO paper tracker (NO ORDERS). History (6,570 resolved markets): markets in their first 10 days priced
YES 0.30-0.50 resolved YES only 24-29% (stand-alone binaries, non-sports: price 0.425 -> YES 0.237). Daily history
prices can be mids of empty books, so this measures it at REAL asks: every run, active stand-alone (not negRisk)
non-sports binaries created in the last 72 h, ending within 60 days, YES mid 0.30-0.50 -> paper-buy NO at the best
ask ($10) if the book has the size. Settles on the official outcome. data/slow/young_positions.jsonl, young_report.json."""
import json, os, re, time, datetime as dt
import requests

GAMMA = "https://gamma-api.polymarket.com"; CLOB = "https://clob.polymarket.com"; D = "data/slow"; os.makedirs(D, exist_ok=True)
S = requests.Session(); S.headers["User-Agent"] = "polymarket-lab-research/0.1"
STAKE = 10.0; POS = f"{D}/young_positions.jsonl"
SPORT = re.compile(r"\b(vs\.?|nba|nfl|nhl|mlb|ncaa|ufc|mma|premier|la liga|serie a|bundesliga|ligue|champions|europa|mls|atp|wta|tennis|open|cup|league|match|game|win on|spread|o/u|over/under|f1|grand prix|boxing|fight|cricket|rugby|golf|pga|nascar|esports|lol|cs2|dota|valorant)\b", re.I)
SKIP = re.compile(r"updown|up-or-down|-5m-|-15m-|-4h-|highest-temperature", re.I)
now = dt.datetime.now(dt.timezone.utc)


def get(url, params=None, tries=3):
    for i in range(tries):
        try:
            r = S.get(url, params=params, timeout=25)
            if r.status_code == 200:
                return r.json()
            time.sleep(1 + i)
        except Exception:  # noqa: BLE001
            time.sleep(1 + i)
    return None


positions = [json.loads(l) for l in open(POS)] if os.path.exists(POS) else []
held = {p["id"] for p in positions}
for p in positions:
    if p.get("resolved"):
        continue
    m = get(f"{GAMMA}/markets/{p['id']}")
    try:
        pr = [float(x) for x in json.loads((m or {}).get("outcomePrices") or "[]")]
    except ValueError:
        continue
    if m and pr:
        p["now_yes"] = pr[0]
        if m.get("closed") and max(pr) >= 0.99:
            y = int(pr[0] > pr[1]); p.update(resolved=True, y=y, won=int(y == 0), pnl=round(p["shares"] * ((1 if y == 0 else 0) - p["ask"]), 2))
n_new = 0; offset = 0; n_seen = 0
while offset < 3000:
    page = get(f"{GAMMA}/markets", {"active": "true", "closed": "false", "limit": 100, "offset": offset, "order": "startDate", "ascending": "false"})
    if not page:
        break
    offset += 100; stop = False
    for m in page:
        try:
            st = dt.datetime.fromisoformat((m.get("startDate") or m.get("createdAt")).replace("Z", "+00:00"))
            end = dt.datetime.fromisoformat(m["endDate"].replace("Z", "+00:00"))
        except (KeyError, ValueError, AttributeError, TypeError):
            continue
        if (now - st).total_seconds() > 72 * 3600:
            stop = True; break
        n_seen += 1
        if m["id"] in held or m.get("negRisk") or SKIP.search(m.get("slug") or "") or SPORT.search(f"{m.get('question')} {m.get('slug')}"):
            continue
        if not (1 <= (end - now).total_seconds() / 86400 <= 60):
            continue
        try:
            pr = [float(x) for x in json.loads(m.get("outcomePrices") or "[]")]; toks = json.loads(m.get("clobTokenIds") or "[]")
        except ValueError:
            continue
        if len(pr) != 2 or len(toks) != 2 or not (0.30 <= pr[0] <= 0.50):
            continue
        bk = get(f"{CLOB}/book", {"token_id": toks[1]})
        asks = sorted((float(a["price"]), float(a["size"])) for a in (bk or {}).get("asks") or [])
        if not asks or asks[0][1] * asks[0][0] < STAKE or not (0.45 <= asks[0][0] <= 0.75):
            continue
        a = asks[0][0]
        positions.append({"id": m["id"], "slug": m.get("slug"), "question": m.get("question"), "created": st.strftime("%Y-%m-%d %H:%M"), "opened": now.strftime("%Y-%m-%d %H:%M"),
                          "end": end.strftime("%Y-%m-%d"), "yes_mid": pr[0], "ask": a, "shares": round(STAKE / a, 2), "resolved": False})
        held.add(m["id"]); n_new += 1
    if stop or len(page) < 100:
        break
with open(POS, "w") as fh:
    for p in positions:
        fh.write(json.dumps(p, ensure_ascii=False) + "\n")
done = [p for p in positions if p.get("resolved")]
rep = {"updated": now.strftime("%Y-%m-%d %H:%M"), "young_markets_seen": n_seen, "new": n_new, "open": len(positions) - len(done), "settled": len(done),
       "won": sum(p["won"] for p in done), "pnl": round(sum(p["pnl"] for p in done), 2), "staked_settled": round(sum(p["shares"] * p["ask"] for p in done), 2),
       "avg_ask": round(sum(p["ask"] for p in positions) / len(positions), 3) if positions else None}
json.dump(rep, open(f"{D}/young_report.json", "w"), indent=1)
print(json.dumps(rep))
for p in positions[-n_new:] if n_new else []:
    print(f"  NO at {p['ask']:.2f} (yes mid {p['yes_mid']:.2f}) ends {p['end']}: {p['question'][:90]}")
