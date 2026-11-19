"""N95 forward paper tracker (NO ORDERS, public endpoints only): Rotten Tomatoes score ladders, NO side, 1-7 days before end.
Tape (rt_ladder.py, cycle 44, group a, 12 weeks): RT ladder NO at the follower fill +11.4 pts [2.8, 19.8] on 36 films, halves +3.3 /
+19.4; the pre-registered time split 24-168 h before end +12.0 [2.0, 21.4] on 30 films, halves +7.5 / +16.2 (also middle rungs +14.3,
NO price 0.30-0.60 +15.0 - logged here, not filtered). Found by looking (N94 -> N95, LESSONS 22), so this paper run is the real test.
Rule, fixed 11-19 c44 before the first position: every hourly run list open markets whose question names Rotten Tomatoes / the
Tomatometer and 'at least N'; if the market ends 24-168 h from now and is not held: read the NO book, paper-buy $10 at the best NO ask
if 0.05 <= ask <= 0.95 and >= $10 sits at that ask; fee = 0.05 * a(1-a) * shares (movies rate on the tape). One position per market.
Logged per position: rung (top / middle / bottom of the film's open ladder), ask, spread, hours to end. Settled on Gamma outcomePrices.
Decision (pre-registered): unit = film. Kill if forward NO <= +1 pt per share after 15 films; propose (with numbers, wait for Yoav's OK)
only after 30 films and both halves > 0. ~3 films a week -> ~10 weeks. Guard (LESSONS 28): report 'settled' and 'open_past_end'.
State data/slow/rt_positions.jsonl; summary data/slow/rt_report.json."""
import json, os, re, time, datetime as dt, collections
import requests

GAMMA = "https://gamma-api.polymarket.com"; CLOB = "https://clob.polymarket.com"; D = "data/slow"
POS = f"{D}/rt_positions.jsonl"; STAKE = 10.0; LO, HI = 0.05, 0.95; FEE = 0.05
TH = re.compile(r"at least (\d+)", re.I)
S = requests.Session(); S.headers["User-Agent"] = "polymarket-lab-research/0.1"
stats = collections.Counter()


def get(url, params=None):
    for i in range(3):
        try:
            r = S.get(url, params=params, timeout=20)
            if r.status_code == 200:
                return r.json()
            stats[f"http {r.status_code}"] += 1
            if r.status_code != 429:
                return None
        except Exception:  # noqa: BLE001
            stats["http error"] += 1
        time.sleep(1 + 2 * i)
    return None


def best(book, side):
    lv = sorted(((float(a["price"]), float(a["size"])) for a in (book or {}).get(side, [])), key=lambda x: x[0], reverse=(side == "bids"))
    return lv[0] if lv else (None, 0)


def is_rt(q):
    ql = (q or "").lower()
    return ("rotten tomatoes" in ql or "tomatometer" in ql) and TH.search(q or "")


def end_ts(m):
    try:
        return dt.datetime.fromisoformat((m.get("endDate") or "").replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


os.makedirs(D, exist_ok=True)
pos = [json.loads(l) for l in open(POS)] if os.path.exists(POS) else []
held = {p["id"] for p in pos}
now = dt.datetime.now(dt.timezone.utc); NOW = now.timestamp()
for p in pos:
    if p.get("resolved"):
        continue
    m = get(f"{GAMMA}/markets/{p['id']}")
    try:
        pr = [float(x) for x in json.loads((m or {}).get("outcomePrices") or "[]")]
    except ValueError:
        pr = []
    if m and m.get("closed") and pr and max(pr) >= 0.99:
        y = int(pr[0] > pr[1]); win = y == 0
        p.update(resolved=True, y=y, won=int(win), pnl=round(p["shares"] * (1 if win else 0) - STAKE - p["fee"], 2),
                 pts=round(100 * ((1 if win else 0) - p["ask"] - FEE * p["ask"] * (1 - p["ask"])), 2), settled=now.strftime("%Y-%m-%d %H:%M"))

cands = {}; srcs = collections.Counter()
def add(ms, ev, src):
    for m in ms or []:
        if is_rt(m.get("question")) and not m.get("closed"):
            m["_ev"] = ev; cands.setdefault(str(m["id"]), m); srcs[src] += 1
for q in ("rotten tomatoes", "tomatometer"):
    r = get(f"{GAMMA}/public-search", {"q": q, "events_status": "active", "limit_per_type": 50})
    for e in (r or {}).get("events", []) or []:
        ms = e.get("markets")
        if not ms and e.get("id"):
            ms = (get(f"{GAMMA}/events/{e['id']}") or {}).get("markets")
        add(ms, e.get("slug"), "search")
for tag in ("movies", "rotten-tomatoes"):
    for e in get(f"{GAMMA}/events", {"tag_slug": tag, "active": "true", "closed": "false", "limit": 100}) or []:
        add(e.get("markets"), e.get("slug"), "tag")
ladder = collections.defaultdict(list)
for m in cands.values():
    ladder[m["_ev"]].append(int(TH.search(m["question"])[1]))
n_new = 0; in_win = 0; skips = collections.Counter()
for mid, m in cands.items():
    e = end_ts(m)
    if mid in held or e is None:
        continue
    h = (e - NOW) / 3600
    if not 24 <= h <= 168:
        skips["outside 24-168 h"] += 1; continue
    in_win += 1
    try:
        toks = json.loads(m.get("clobTokenIds") or "[]")
    except (ValueError, TypeError):
        toks = []
    if len(toks) != 2:
        skips["not binary"] += 1; continue
    book = get(f"{CLOB}/book", {"token_id": toks[1]})
    ask, size = best(book, "asks"); bid, _ = best(book, "bids")
    if ask is None or not (LO <= ask <= HI):
        skips["ask outside"] += 1; continue
    if ask * size < STAKE:
        skips["thin"] += 1; continue
    v = int(TH.search(m["question"])[1]); vs = sorted(ladder[m["_ev"]])
    rung = "top" if len(vs) > 1 and v == vs[-1] else ("bottom" if len(vs) > 1 and v == vs[0] else "middle")
    sh = round(STAKE / ask, 2)
    pos.append({"id": mid, "event": m["_ev"], "question": m["question"], "side": "NO", "ask": ask, "ask_size": size, "bid": bid,
                "spread": round(ask - bid, 4) if bid else None, "shares": sh, "fee": round(FEE * ask * (1 - ask) * sh, 4), "stake": STAKE,
                "thr": v, "rung": rung, "h_to_end": round(h, 1), "end": m.get("endDate"), "opened": now.strftime("%Y-%m-%d %H:%M"),
                "resolved": False})
    held.add(mid); n_new += 1
with open(POS, "w") as fh:
    for p in pos:
        fh.write(json.dumps(p, ensure_ascii=False) + "\n")
done = [p for p in pos if p.get("resolved")]
films = collections.defaultdict(list)
for p in done: films[p["event"]].append(p["pts"])
past = sum(1 for p in pos if not p.get("resolved") and (end_ts(p) or 9e18) < NOW - 86400)
rep = {"updated": now.strftime("%Y-%m-%d %H:%M"), "rt_markets_seen": len(cands), "sources": dict(srcs), "in_window": in_win,
       "skips": dict(skips), "http": dict(stats), "new": n_new, "open": len(pos) - len(done), "settled": len(done), "open_past_end": past,
       "won": sum(p["won"] for p in done), "pnl": round(sum(p["pnl"] for p in done), 2), "films_settled": len(films),
       "pts_per_share": round(sum(p["pts"] for p in done) / len(done), 2) if done else None,
       "by_rung": {r: [len([p for p in done if p["rung"] == r]), round(sum(p["pts"] for p in done if p["rung"] == r) / max(1, len([p for p in done if p["rung"] == r])), 2)]
                   for r in ("top", "middle", "bottom")}}
json.dump(rep, open(f"{D}/rt_report.json", "w"), indent=1)
print(json.dumps(rep))
