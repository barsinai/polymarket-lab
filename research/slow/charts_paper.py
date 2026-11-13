"""N10 ranking-chart favourites, paper tracker (NO ORDERS). Cycle 4, 11-13.
History (charts_census.py, 208 closed Netflix / App Store / Spotify / Billboard events 2025-10..2026-02, hourly last prices):
the event favourite priced 0.60-0.85 won 82% at avg 0.75 (+5.6%/$ at +2c, 49 events, 24 h before the end; +13.6% at 2 h, 26),
Netflix favourites 0.50-0.97 +6.7% (72 events), App Store -6.2% (37), first half -5.4% vs second +6.2% (lumpy). Leaders
priced >= 0.95 won only 92-96% (3-4 losses -> the leader's NO at <= 5c is a hint, not a rule). Fees disabled on these markets.
This checks it at REAL asks. Rule: open negRisk event whose title names Netflix / App Store / Play Store / Spotify / Billboard /
Hot 100, event end in 2..24 h; favourite = market with the highest YES mid; buy YES at its best ask if 0.60 <= ask <= 0.97 and
>= $10 at that ask (rule 'fav', spread <= 10c, fee 0.07p(1-p) when enabled - fees are ON for these markets since 11-13); if the favourite's YES bid >= 0.95, also buy its NO at the ask if <= 0.06 (rule 'tail').
$10 each, once per event and rule. Settles on gamma outcomePrices. State data/slow/charts_positions.jsonl, summary
data/slow/charts_report.json (by kind)."""
import json, os, re, time, datetime as dt, collections
import requests

GAMMA = "https://gamma-api.polymarket.com"; CLOB = "https://clob.polymarket.com"; D = "data/slow"
POS = f"{D}/charts_positions.jsonl"; STAKE = 10.0
PAT = re.compile(r"netflix|app store|play store|spotify|billboard|hot 100", re.I)
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


MAXSPREAD = 0.10  # the census used last prices; wide books (bid 0.41 / ask 0.76 seen 11-13) are not the same favourite


def fee(p, shares, m):
    """taker fee convention of the lab: 0.07 p (1-p) per share when the market has fees enabled"""
    return 0.07 * p * (1 - p) * shares if m.get("feesEnabled") else 0.0


def kind(t):
    t = t.lower()
    for k in ("netflix", "app store", "play store", "spotify", "billboard", "hot 100"):
        if k in t:
            return "billboard" if k == "hot 100" else k
    return "other"


os.makedirs(D, exist_ok=True)
pos = [json.loads(l) for l in open(POS)] if os.path.exists(POS) else []
held = {(p["event"], p["rule"]) for p in pos}
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
        p.update(resolved=True, y=y, won=int(win), pnl=round(p["shares"] * (1 if win else 0) - STAKE - p.get("fee", 0), 2), settled=now.strftime("%Y-%m-%d %H:%M"))

seen = 0; n_new = 0; off = 0
while off < 3000:
    page = get(f"{GAMMA}/events", {"active": "true", "closed": "false", "limit": 100, "offset": off,
               "end_date_min": (now + dt.timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ"),
               "end_date_max": (now + dt.timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ")})
    if not page:
        break
    off += 100
    for e in page:
        title = e.get("title") or ""
        if not PAT.search(title) or re.search(r"say|mention|earnings|subscriber|nflx|spot\)|up or down|\bhit\b|stock|price", title, re.I):
            continue
        seen += 1
        rows = []
        for m in e.get("markets") or []:
            if m.get("closed"):
                continue
            try:
                toks = json.loads(m.get("clobTokenIds") or "[]")
            except ValueError:
                continue
            if len(toks) != 2:
                continue
            yb = get(f"{CLOB}/book", {"token_id": toks[0]})
            ask, asz = best(yb, "asks"); bid, _ = best(yb, "bids")
            if ask is None and bid is None:
                continue
            mid = ((ask or 1) + (bid or 0)) / 2
            rows.append({"m": m, "toks": toks, "ask": ask, "asz": asz, "bid": bid, "mid": mid})
            time.sleep(0.05)
        if not rows:
            continue
        f = max(rows, key=lambda r: r["mid"])
        base = {"event": e["id"], "title": title, "kind": kind(title), "id": f["m"]["id"], "question": f["m"].get("question"),
                "end": e.get("endDate"), "opened": now.strftime("%Y-%m-%d %H:%M"), "fav_bid": f["bid"], "fav_ask": f["ask"],
                "second_mid": round(sorted(r["mid"] for r in rows)[-2], 3) if len(rows) > 1 else None,
                "hours_left": round((dt.datetime.fromisoformat(e["endDate"].replace("Z", "+00:00")) - now).total_seconds() / 3600, 1),
                "fees": f["m"].get("feesEnabled"), "resolved": False, "stake": STAKE}
        if (e["id"], "fav") not in held and f["ask"] is not None and 0.60 <= f["ask"] <= 0.97 and f["ask"] * f["asz"] >= STAKE \
                and f["bid"] is not None and f["ask"] - f["bid"] <= MAXSPREAD:
            pos.append(dict(base, rule="fav", side="YES", ask=f["ask"], spread=round(f["ask"] - f["bid"], 4), shares=round(STAKE / f["ask"], 2),
                            fee=round(fee(f["ask"], STAKE / f["ask"], f["m"]), 4)))
            held.add((e["id"], "fav")); n_new += 1
        if (e["id"], "tail") not in held and (f["bid"] or 0) >= 0.95:
            nb = get(f"{CLOB}/book", {"token_id": f["toks"][1]})
            na, nsz = best(nb, "asks")
            if na is not None and na <= 0.06 and na * nsz >= STAKE:
                pos.append(dict(base, rule="tail", side="NO", ask=na, shares=round(STAKE / na, 2), fee=round(fee(na, STAKE / na, f["m"]), 4)))
                held.add((e["id"], "tail")); n_new += 1
    if len(page) < 100:
        break

with open(POS, "w") as fh:
    for p in pos:
        fh.write(json.dumps(p, ensure_ascii=False) + "\n")
done = [p for p in pos if p.get("resolved")]
by = collections.defaultdict(lambda: {"n": 0, "won": 0, "pnl": 0.0})
for p in done:
    k = f"{p['rule']} {p['kind']}"; by[k]["n"] += 1; by[k]["won"] += p["won"]; by[k]["pnl"] = round(by[k]["pnl"] + p["pnl"], 2)
rep = {"updated": now.strftime("%Y-%m-%d %H:%M"), "chart_events_seen": seen, "new": n_new, "open": len(pos) - len(done),
       "settled": len(done), "won": sum(p["won"] for p in done), "pnl": round(sum(p["pnl"] for p in done), 2),
       "staked_settled": STAKE * len(done), "events": len({p["event"] for p in pos}), "by_rule_kind": dict(by)}
json.dump(rep, open(f"{D}/charts_report.json", "w"), indent=1)
print(json.dumps(rep))
