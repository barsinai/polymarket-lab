"""Sports favourite-longshot paper tracker (NO ORDERS), 11-13.
Why: in the 15-min order books (10-31..11-13, pre-game full-game moneylines, first snapshot 3-6 h before the start) the
favourite won more often than its ASK at every price from 0.60 to 0.90 (0.60-0.65 won 64% vs 0.62 ... 0.85-0.90 won 97% vs
0.87; +2..+10%/$ after the exact taker fee, ~340 markets / 2 weeks). Classic favourite-longshot bias, but two weeks can be
luck (LESSONS 5) -> forward test at real asks.
Rule: every hourly run, full-game moneylines (sportsMarketType 'moneyline') whose game starts in 1-6 h: buy the favourite
(higher mid) at its best ask if 0.60 <= ask <= 0.92 and >= $20 sits within 1c of it; $10, once per market; taker fee = the
market's feeSchedule rate * p(1-p) per share. Settled from Gamma at resolution. Count by GAME.
State data/slow/sports_fav_positions.jsonl, report data/slow/sports_fav_report.json."""
import json, os, time, datetime as dt, collections
import requests

GAMMA = "https://gamma-api.polymarket.com"; CLOB = "https://clob.polymarket.com"; D = "data/slow"
POS = f"{D}/sports_fav_positions.jsonl"; STAKE = 10.0
LEAGUES = ("sports", "nba", "nfl", "nhl", "mlb", "cfb", "cbb", "ncaab", "wnba", "epl", "ucl", "uel", "la-liga", "serie-a", "bundesliga",
           "ligue-1", "mls", "tennis", "atp", "wta", "esports", "cs2", "counter-strike", "league-of-legends", "dota-2", "valorant", "ufc", "mma")
S = requests.Session(); S.headers["User-Agent"] = "polymarket-lab-research/0.1"
now = dt.datetime.now(dt.timezone.utc)


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


def top(book, side):
    lv = [(float(a["price"]), float(a["size"])) for a in (book or {}).get(side, [])]
    if not lv:
        return None, 0.0
    best = min(p for p, s in lv) if side == "asks" else max(p for p, s in lv)
    depth = sum(p * s for p, s in lv if abs(p - best) <= 0.01 + 1e-9)
    return best, depth


def ts(s):
    try:
        return dt.datetime.fromisoformat(str(s).replace(" ", "T").replace("Z", "+00:00").replace("+00+00:00", "+00:00"))
    except Exception:  # noqa: BLE001
        return None


os.makedirs(D, exist_ok=True)
pos = [json.loads(l) for l in open(POS)] if os.path.exists(POS) else []
held = {p["id"] for p in pos}
# 1. settle
for p in pos:
    if p.get("resolved"):
        continue
    st = ts(p["start"])
    if st and now < st + dt.timedelta(hours=2):
        continue
    m = get(f"{GAMMA}/markets/{p['id']}")
    try:
        pr = [float(x) for x in json.loads((m or {}).get("outcomePrices") or "[]")]
    except Exception:  # noqa: BLE001
        pr = []
    if m and m.get("closed") and pr and max(pr) >= 0.99:
        won = int(pr[p["idx"]] >= 0.99)
        p.update(resolved=True, won=won, pnl=round(p["shares"] * won - STAKE - p["fee"], 3), settled=now.strftime("%Y-%m-%d %H:%M"))
# 2. scan
seen_ev = set(); n_mk = 0; new = 0
for tag in LEAGUES:
    for off in range(0, 600, 100):
        page = get(f"{GAMMA}/events", {"tag_slug": tag, "active": "true", "closed": "false", "limit": 100, "offset": off,
                                       "end_date_min": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                       "end_date_max": (now + dt.timedelta(days=4)).strftime("%Y-%m-%dT%H:%M:%SZ")})
        if not page:
            break
        for e in page:
            if e.get("id") in seen_ev:
                continue
            seen_ev.add(e.get("id"))
            for m in e.get("markets") or []:
                if m.get("sportsMarketType") != "moneyline" or m.get("closed") or m.get("id") in held:
                    continue
                st = ts(m.get("gameStartTime") or e.get("startTime") or "")
                if not st or not (now + dt.timedelta(hours=1) <= st <= now + dt.timedelta(hours=6)):
                    continue
                try:
                    tk = json.loads(m.get("clobTokenIds") or "[]"); names = json.loads(m.get("outcomes") or "[]")
                except ValueError:
                    continue
                if len(tk) != 2:
                    continue
                n_mk += 1
                b0 = get(f"{CLOB}/book", {"token_id": tk[0]}); b1 = get(f"{CLOB}/book", {"token_id": tk[1]}); time.sleep(0.05)
                a0, d0 = top(b0, "asks"); bid0, _ = top(b0, "bids"); a1, d1 = top(b1, "asks"); bid1, _ = top(b1, "bids")
                if None in (a0, bid0, a1, bid1):
                    continue
                fav = 0 if (a0 + bid0) >= (a1 + bid1) else 1
                ask, depth, spr = (a0, d0, a0 - bid0) if fav == 0 else (a1, d1, a1 - bid1)
                if not (0.60 <= ask <= 0.92) or depth < 20:
                    continue
                fs = m.get("feeSchedule") or {}
                rate = float(fs.get("rate") or 0) if m.get("feesEnabled") else 0.0
                sh = STAKE / ask
                pos.append({"id": m["id"], "event": e.get("slug"), "q": m.get("question"), "tag": tag, "start": st.isoformat(), "idx": fav,
                            "side": names[fav] if fav < len(names) else fav, "ask": ask, "spread": round(spr, 3), "depth": round(depth, 1),
                            "hours_before": round((st - now).total_seconds() / 3600, 2), "shares": round(sh, 3), "fee": round(rate * ask * (1 - ask) * sh, 4),
                            "fee_rate": rate, "opened": now.strftime("%Y-%m-%d %H:%M"), "resolved": False})
                held.add(m["id"]); new += 1
        if len(page) < 100:
            break
with open(POS, "w") as fh:
    for p in pos:
        fh.write(json.dumps(p, ensure_ascii=False) + "\n")
done = [p for p in pos if p.get("resolved")]
by = collections.defaultdict(lambda: [0, 0, 0.0, 0.0])
for p in done:
    band = "0.60-0.70" if p["ask"] < 0.70 else "0.70-0.80" if p["ask"] < 0.80 else "0.80-0.92"
    for k in (band, "tag " + p["tag"], "ALL"):
        b = by[k]; b[0] += 1; b[1] += p["won"]; b[2] += p["pnl"]; b[3] += STAKE
rep = {"updated": now.strftime("%Y-%m-%d %H:%M"), "moneylines_in_window": n_mk, "new": new, "open": len(pos) - len(done), "settled": len(done),
       "games_settled": len({p["event"] for p in done}),
       "by": {k: {"n": v[0], "won": v[1], "win_rate": round(v[1] / v[0], 3), "pnl": round(v[2], 2), "ret": round(v[2] / v[3], 4)} for k, v in by.items()}}
json.dump(rep, open(f"{D}/sports_fav_report.json", "w"), indent=1)
print(json.dumps(rep))
