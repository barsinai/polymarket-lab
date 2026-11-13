"""N8 mention markets ('What will X say during ...?'), paper tracker (NO ORDERS). Cycle 5, 11-13.
History (mention_census.py, data/research/mention_report.json): YES is systematically rich. Earnings calls (411 markets / 36 calls,
2025-02..2026-02, hourly last prices): words priced 0.20-0.35 said 12%, 0.35-0.50 said 24-26%; NO on YES 0.10-0.40 +14.6%/$ at
+2c + fee (24 h before the call, 29 calls, 22 positive, 4/7 months) and +17.3% (2 h before, 27 calls, 6/7 months), both halves
positive. Other speakers (speeches, pressers; 234-304 events) +9% at 24 h but +1.8% at 2 h; those include week-long 'path'
markets that resolve YES early (LESSONS 11), so they are a shadow rule only.
This checks it at REAL asks: open event whose slug has 'mention' or whose title has ' say ', market end (= event start) in
1..30 h; for each market whose YES mid is 0.10-0.40: buy NO at its best ask if the NO book spread <= 6c and >= $10 at that ask,
fee 0.07p(1-p) when enabled. Rule 'earn' for earnings calls, 'other' otherwise. $10 each, once per market. Count by EVENT (words on
one call are one bet, LESSONS 6). State data/slow/mention_positions.jsonl, summary data/slow/mention_report.json."""
import json, os, re, time, datetime as dt, collections
import requests

GAMMA = "https://gamma-api.polymarket.com"; CLOB = "https://clob.polymarket.com"; D = "data/slow"
POS = f"{D}/mention_positions.jsonl"; STAKE = 10.0; MAXSPREAD = 0.06
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
        y = int(pr[0] > pr[1]); win = y == 0
        p.update(resolved=True, y=y, won=int(win), pnl=round(p["shares"] * (1 if win else 0) - STAKE - p.get("fee", 0), 2), settled=now.strftime("%Y-%m-%d %H:%M"))

seen = 0; n_new = 0; off = 0; spreads = []
while off < 4000:
    page = get(f"{GAMMA}/events", {"active": "true", "closed": "false", "limit": 100, "offset": off,
               "end_date_min": (now + dt.timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
               "end_date_max": (now + dt.timedelta(hours=30)).strftime("%Y-%m-%dT%H:%M:%SZ")})
    if not page:
        break
    off += 100
    for e in page:
        title = e.get("title") or ""; slug = e.get("slug") or ""
        if "mention" not in slug and not re.search(r"\bsay\b", title, re.I):
            continue
        seen += 1
        rule = "earn" if ("earnings" in slug or re.search(r"earnings", title, re.I)) else "other"
        for m in e.get("markets") or []:
            if m.get("closed") or m["id"] in held:
                continue
            try:
                toks = json.loads(m.get("clobTokenIds") or "[]")
                end = dt.datetime.fromisoformat((m.get("endDate") or e.get("endDate")).replace("Z", "+00:00"))
            except Exception:  # noqa: BLE001
                continue
            h = (end - now).total_seconds() / 3600
            if len(toks) != 2 or not (1 <= h <= 30):
                continue
            yb = get(f"{CLOB}/book", {"token_id": toks[0]}); time.sleep(0.05)
            ya, _ = best(yb, "asks"); ybid, _ = best(yb, "bids")
            if ya is None or ybid is None:
                continue
            ymid = (ya + ybid) / 2
            if not (0.10 <= ymid <= 0.40):
                continue
            nb = get(f"{CLOB}/book", {"token_id": toks[1]}); time.sleep(0.05)
            na, nsz = best(nb, "asks"); nbid, _ = best(nb, "bids")
            if na is None or nbid is None:
                continue
            spreads.append(round(na - nbid, 3))
            if na - nbid > MAXSPREAD or na * nsz < STAKE or na > 0.92:
                continue
            sh = STAKE / na
            pos.append({"event": e["id"], "title": title, "rule": rule, "id": m["id"], "question": m.get("question"), "end": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "opened": now.strftime("%Y-%m-%d %H:%M"), "hours_left": round(h, 1), "yes_mid": round(ymid, 3), "side": "NO", "ask": na,
                        "spread": round(na - nbid, 3), "shares": round(sh, 2), "fee": round(0.07 * na * (1 - na) * sh if m.get("feesEnabled") else 0.0, 4),
                        "fees": m.get("feesEnabled"), "resolved": False, "stake": STAKE})
            held.add(m["id"]); n_new += 1
    if len(page) < 100:
        break

with open(POS, "w") as fh:
    for p in pos:
        fh.write(json.dumps(p, ensure_ascii=False) + "\n")
done = [p for p in pos if p.get("resolved")]
by = collections.defaultdict(lambda: {"n": 0, "won": 0, "pnl": 0.0, "events": set()})
for p in done:
    b = by[p["rule"]]; b["n"] += 1; b["won"] += p["won"]; b["pnl"] = round(b["pnl"] + p["pnl"], 2); b["events"].add(p["event"])
rep = {"updated": now.strftime("%Y-%m-%d %H:%M"), "mention_events_seen": seen, "new": n_new, "open": len(pos) - len(done),
       "settled": len(done), "won": sum(p["won"] for p in done), "pnl": round(sum(p["pnl"] for p in done), 2), "staked_settled": STAKE * len(done),
       "events_settled": len({p["event"] for p in done}), "median_no_spread_seen": sorted(spreads)[len(spreads) // 2] if spreads else None,
       "candidates_seen": len(spreads), "by_rule": {k: dict(v, events=len(v["events"])) for k, v in by.items()}}
json.dump(rep, open(f"{D}/mention_report.json", "w"), indent=1)
print(json.dumps(rep))
