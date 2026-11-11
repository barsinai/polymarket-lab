"""Polymarket vs a sharp bookmaker (Pinnacle, via The Odds API) on the same games (read-only, NO ORDERS).

Needs the repository secret ODDS_API_KEY (free plan: 500 credits a month; one call = one sport x one market x one
region, so a snapshot of SPORTS x MARKETS costs ~len(SPORTS)*len(MARKETS) credits -> a few snapshots a day at most).
For every upcoming game Pinnacle prices: remove Pinnacle's margin (proportional) -> fair probabilities; match the game
on Polymarket ('<Team> vs. <Team>' moneyline, and totals 'O/U x.5' at the same line) by team-name tokens and start
time; read the real best asks. Logs every pair to data/sharp/snapshots.jsonl (fair p, Polymarket ask/bid, gap) and
prints the distribution of gaps plus every Polymarket ask that is below Pinnacle's fair value by >= EDGE.
The decisive question: how often, and by how much, is Polymarket cheaper than the sharp price, at what size?"""
import json, os, re, time, datetime as dt
import requests

KEY = os.environ.get("ODDS_API_KEY")
D = "data/sharp"; os.makedirs(D, exist_ok=True)
EDGE = float(os.environ.get("EDGE", "0.03"))
SPORTS = os.environ.get("SPORTS", "icehockey_nhl,basketball_nba,americanfootball_nfl,soccer_epl,soccer_uefa_champs_league,soccer_spain_la_liga").split(",")
MARKETS = os.environ.get("MARKETS", "h2h,totals").split(",")
S = requests.Session(); S.headers["User-Agent"] = "polymarket-lab-research/0.1"
GAMMA = "https://gamma-api.polymarket.com"; CLOB = "https://clob.polymarket.com"
TAGS = {"icehockey_nhl": "nhl", "basketball_nba": "nba", "americanfootball_nfl": "nfl", "soccer_epl": "epl", "soccer_uefa_champs_league": "ucl",
        "soccer_spain_la_liga": "la-liga", "soccer_italy_serie_a": "serie-a", "soccer_germany_bundesliga": "bundesliga", "americanfootball_ncaaf": "cfb",
        "basketball_ncaab": "cbb", "mma_mixed_martial_arts": "ufc"}
now = dt.datetime.now(dt.timezone.utc)
STOP = {"fc", "cf", "afc", "sc", "the", "club", "de", "real", "city", "united", "of"}


def toks(name):
    return {w for w in re.findall(r"[a-z0-9]+", name.lower()) if w not in STOP and len(w) > 2}


if not KEY:
    raise SystemExit("ODDS_API_KEY is not set: add it as a repository secret (Settings > Secrets and variables > Actions)")

snap = []; credits = None
for sport in SPORTS:
    # 1. Pinnacle prices
    r = S.get(f"https://api.the-odds-api.com/v4/sports/{sport}/odds", params={"apiKey": KEY, "regions": "eu", "markets": ",".join(MARKETS),
              "bookmakers": "pinnacle", "oddsFormat": "decimal", "dateFormat": "iso"}, timeout=30)
    credits = r.headers.get("x-requests-remaining", credits)
    if r.status_code != 200:
        print(sport, "odds api", r.status_code, r.text[:200]); continue
    games = r.json()
    # 2. Polymarket games of the same league
    pm = []
    for off in (0, 100, 200):
        page = S.get(f"{GAMMA}/events", params={"tag_slug": TAGS.get(sport, sport), "active": "true", "closed": "false", "limit": 100, "offset": off}, timeout=30).json()
        pm += page
        if len(page) < 100:
            break
    print(f"{sport}: pinnacle games {len(games)}, polymarket events {len(pm)}", flush=True)
    for g in games:
        try:
            start = dt.datetime.fromisoformat(g["commence_time"].replace("Z", "+00:00"))
        except (KeyError, ValueError):
            continue
        if start < now:
            continue                                     # pre-game only: live games are a different (faster) market
        bk = next((b for b in g.get("bookmakers", []) if b["key"] == "pinnacle"), None)
        if not bk:
            continue
        th, ta = toks(g["home_team"]), toks(g["away_team"])
        ev = None
        for e in pm:
            et = toks(e.get("title") or "")
            if th & et and ta & et:
                ev = e; break
        if not ev:
            continue
        for mk in bk.get("markets", []):
            outs = mk.get("outcomes", [])
            inv = [1 / o["price"] for o in outs if o.get("price")]
            if len(inv) != len(outs) or not inv:
                continue
            fair = [x / sum(inv) for x in inv]; margin = sum(inv) - 1
            for o, fp in zip(outs, fair):
                # find the Polymarket market + outcome token for this selection
                for m in ev.get("markets") or []:
                    q = m.get("question") or ""; mtype = m.get("sportsMarketType") or ""
                    try:
                        names = json.loads(m.get("outcomes") or "[]"); tk = json.loads(m.get("clobTokenIds") or "[]")
                    except ValueError:
                        continue
                    idx = None
                    if mk["key"] == "h2h" and mtype == "moneyline" and len(names) == 2:
                        for i, n in enumerate(names):
                            if toks(n) & toks(o["name"]):
                                idx = i
                    elif mk["key"] == "h2h" and o["name"] == "Draw" and re.search(r"draw", q, re.I) and "halftime" not in q.lower():
                        idx = 0
                    elif mk["key"] == "h2h" and len(outs) == 3 and re.search(r"\bwin\b", q, re.I) and toks(q) & toks(o["name"]) and "halftime" not in q.lower():
                        idx = 0                                   # soccer: 'Will <team> win on <date>?' (Yes token)
                    elif mk["key"] == "totals" and mtype == "totals" and o.get("point") is not None and re.search(rf"O/U {o['point']}\b", q):
                        idx = 0 if o["name"] == "Over" else 1
                    if idx is None or idx >= len(tk):
                        continue
                    snap.append({"ts": now.strftime("%Y-%m-%d %H:%M"), "sport": sport, "game": f"{g['away_team']} @ {g['home_team']}", "start": g["commence_time"],
                                 "market": mk["key"], "selection": o["name"], "point": o.get("point"), "pin_price": o["price"], "pin_margin": round(margin, 4),
                                 "fair": round(fp, 4), "pm_question": q, "pm_token": tk[idx], "pm_market_id": m.get("id"), "event": ev.get("slug")})
                    break
    time.sleep(1)

# 3. real Polymarket books for every matched selection
tok = list({s["pm_token"] for s in snap}); B = {}
for i in range(0, len(tok), 400):
    resp = S.post(f"{CLOB}/books", json=[{"token_id": t} for t in tok[i:i + 400]], timeout=40)
    for b in resp.json():
        asks = sorted((float(a["price"]), float(a["size"])) for a in b.get("asks") or [])
        bids = sorted(((float(a["price"]), float(a["size"])) for a in b.get("bids") or []), reverse=True)
        B[b["asset_id"]] = (asks[0] if asks else None, bids[0] if bids else None)
gaps = []
with open(f"{D}/snapshots.jsonl", "a") as fh:
    for s in snap:
        a, b = B.get(s["pm_token"], (None, None))
        s.update(pm_ask=a[0] if a else None, pm_ask_sz=a[1] if a else None, pm_bid=b[0] if b else None)
        if a:
            s["edge"] = round(s["fair"] - a[0], 4); gaps.append(s)
        fh.write(json.dumps(s) + "\n")
print(f"\nmatched selections {len(snap)}, with a Polymarket ask {len(gaps)}; odds-api credits left {credits}")
if gaps:
    e = sorted(x["edge"] for x in gaps); n = len(e)
    mid = [((x["pm_ask"] + (x["pm_bid"] or x["pm_ask"])) / 2 - x["fair"]) for x in gaps if x["pm_bid"]]
    print(f"fair - ask: p10 {e[n // 10]:+.3f} median {e[n // 2]:+.3f} p90 {e[9 * n // 10]:+.3f} max {e[-1]:+.3f}; |mid - fair| median {sorted(abs(m) for m in mid)[len(mid) // 2]:.3f}")
    for x in sorted(gaps, key=lambda x: -x["edge"]):
        if x["edge"] < EDGE:
            break
        print(f"  +{x['edge']:.3f} {x['sport']:22} {x['game'][:40]:40} {x['market']:6} {x['selection']} {x['point'] or ''} fair {x['fair']:.3f} ask {x['pm_ask']:.3f} x {x['pm_ask_sz']:.0f} | {x['pm_question'][:50]}")
