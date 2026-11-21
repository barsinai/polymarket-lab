"""Cycle 55, N117 (outside the box, from c54): Wikipedia attention vs price in multi-outcome culture 'who wins' events.
Runs on GitHub Actions via run_script.yml (needs gamma, clob and Wikimedia; read-only, no keys).
Why the crowd could be wrong: outcome prices in culture ladders (Person of the Year, year-end #1, awards, 'most streamed') are set by
fans and fame (lesson 2), while the deciders follow recent attention, a free public number (Wikimedia daily pageviews) we never used.
Exposed to 13 (pageviews are public: maybe priced), 5/6 (one event per list per year: unit = event), 22 (rule fixed here), 2,
11 (finished events only), 3 (history prices are mids: +1c and a 0.07 p(1-p) fee charged), 4 (lookahead: see below).
Rules fixed BEFORE looking (written here first):
- events: gamma closed events ending 2024-01-01 .. now, tag culture / pop-culture / music / awards / movies, >= 4 markets with a
  groupItemTitle, exactly one market resolved YES; outcomes named 'other', 'none', 'no one', 'someone else', 'tie' dropped.
- entry time T = end - 7 d. Price = last CLOB prices-history point (fidelity 60) at or before T; outcome kept only if price in
  0.01-0.99. Event kept only if >= 4 kept outcomes map to a Wikipedia article with views and the winner is among them.
- attention: en.wikipedia search (top hit for the outcome name) -> daily user pageviews over the 30 days ENDING AT T (c54's wording
  'the 30 d before end' would look ahead 7 days - lesson 4 - so the window ends at the entry).
- LEADER = most views; FAV = highest price. Score per event: leader points = won - (p + 0.01) - 0.07 p(1-p) at T.
DEAD if < 20 events, or leader points <= +3, or leader hit rate <= favourite hit rate. Printed: events where leader != favourite
(the only ones that matter), per-year split, rising-views variant (last 7 d / prior 23 d) leader."""
import json, time, datetime as dt, re, urllib.parse
import requests

GAMMA = "https://gamma-api.polymarket.com"
CLOB = "https://clob.polymarket.com"
WIKI = "https://en.wikipedia.org/w/api.php"
PV = "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/user/{}/daily/{}/{}"
S = requests.Session(); S.headers["User-Agent"] = "polymarket-lab research (read-only; github.com/barsinai/polymarket-lab)"
OUT = "data/research/wiki_attention_report.json"
TAGS = ["culture", "pop-culture", "music", "awards", "movies"]
DROP = re.compile(r"\b(other|none|no one|nobody|someone else|tie|not awarded)\b", re.I)


def get(url, params=None):
    for i in range(4):
        try:
            r = S.get(url, params=params, timeout=25)
            if r.status_code == 200: return r.json()
            if r.status_code in (400, 404): return None
        except Exception:
            pass
        time.sleep(1 + 2 * i)
    return None


def events():
    seen = {}
    for tag in TAGS:
        off = 0
        while off < 3000:
            page = get(f"{GAMMA}/events", dict(tag_slug=tag, closed="true", limit=100, offset=off, end_date_min="2024-01-01T00:00:00Z"))
            if not page: break
            for e in page: seen.setdefault(e["id"], e)
            if len(page) < 100: break
            off += 100
    return list(seen.values())


def jl(x):
    return json.loads(x) if isinstance(x, str) else (x or [])


def price_at(tok, T):
    h = get(f"{CLOB}/prices-history", dict(market=tok, startTs=T - 3 * 86400, endTs=T, fidelity=60))
    pts = [x for x in (h or {}).get("history", []) if x["t"] <= T]
    return pts[-1]["p"] if pts else None


def views(name, T):
    s = get(WIKI, dict(action="query", list="search", srsearch=name, srlimit=1, format="json"))
    hits = ((s or {}).get("query") or {}).get("search") or []
    if not hits: return None
    title = urllib.parse.quote(hits[0]["title"].replace(" ", "_"), safe="")
    d1 = dt.datetime.fromtimestamp(T - 30 * 86400, dt.timezone.utc).strftime("%Y%m%d")
    d2 = dt.datetime.fromtimestamp(T - 86400, dt.timezone.utc).strftime("%Y%m%d")
    j = get(PV.format(title, d1, d2))
    it = (j or {}).get("items") or []
    if not it: return None
    v = [x["views"] for x in it]
    return dict(title=hits[0]["title"], total=sum(v), last7=sum(v[-7:]), prior=sum(v[:-7]) or 1)


rows = []; n_ev = 0; skips = {}
now = time.time()
EV = events()
print("events pulled", len(EV), flush=True)
T0 = time.time()
EV.sort(key=lambda e: e.get("endDate") or "", reverse=True)
for e in EV:
    if time.time() - T0 > 45 * 60: skips["time cap 45 min"] = 1; break
    ms = [m for m in e.get("markets") or [] if m.get("groupItemTitle")]
    if not 4 <= len(ms) <= 40: skips["outcomes not 4-40"] = skips.get("outcomes not 4-40", 0) + 1; continue
    try:
        end = dt.datetime.fromisoformat((e.get("endDate") or ms[0]["endDate"]).replace("Z", "+00:00")).timestamp()
    except Exception:
        continue
    if end > now: continue
    won = [m for m in ms if jl(m.get("outcomePrices"))[:1] == ["1"]]
    if len(won) != 1: skips["winner != 1"] = skips.get("winner != 1", 0) + 1; continue
    T = int(end - 7 * 86400)
    outs = []
    for m in ms:
        name = m["groupItemTitle"].strip()
        if DROP.search(name): continue
        tok = jl(m.get("clobTokenIds"))
        if not tok: continue
        p = price_at(tok[0], T)
        if p is None or not 0.01 <= p <= 0.99: continue
        v = views(name, T)
        if not v: continue
        outs.append(dict(name=name, p=p, won=m is won[0], **v))
    if len(outs) < 4 or not any(o["won"] for o in outs):
        skips["< 4 mapped or winner unmapped"] = skips.get("< 4 mapped or winner unmapped", 0) + 1; continue
    lead = max(outs, key=lambda o: o["total"]); fav = max(outs, key=lambda o: o["p"])
    rise = max(outs, key=lambda o: o["last7"] / 7 / (o["prior"] / 23))
    pts = lambda o: 100 * ((1 if o["won"] else 0) - (o["p"] + 0.01) - 0.07 * o["p"] * (1 - o["p"]))
    rows.append(dict(event=e.get("slug"), end=int(end), n=len(outs), lead=lead["name"], lead_p=lead["p"], lead_won=lead["won"],
                     lead_pts=round(pts(lead), 2), fav=fav["name"], fav_p=fav["p"], fav_won=fav["won"], fav_pts=round(pts(fav), 2),
                     rise=rise["name"], rise_pts=round(pts(rise), 2), rise_won=rise["won"], differ=lead["name"] != fav["name"]))
    print(len(rows), e.get("slug"), "lead", lead["name"], lead["p"], lead["won"], "| fav", fav["name"], fav["p"], fav["won"], flush=True)


def summ(rr, k):
    if not rr: return dict(events=0)
    return dict(events=len(rr), pts=round(sum(r[f"{k}_pts"] for r in rr) / len(rr), 2), hits=sum(r[f"{k}_won"] for r in rr))


out = dict(rule=__doc__.split("Rules fixed BEFORE looking (written here first):")[1].strip(), skips=skips, events_pulled=len(EV),
           leader=summ(rows, "lead"), favourite=summ(rows, "fav"), rising=summ(rows, "rise"),
           leader_when_differ=summ([r for r in rows if r["differ"]], "lead"), fav_when_differ=summ([r for r in rows if r["differ"]], "fav"),
           by_year={y: summ([r for r in rows if dt.datetime.fromtimestamp(r["end"], dt.timezone.utc).year == y], "lead") for y in (2024, 2025, 2026)},
           rows=rows)
L, F = out["leader"], out["favourite"]
ok = L["events"] >= 20 and L["pts"] > 3 and L["hits"] > F["hits"]
out["decision"] = "PASS -> paper tracker on open ladders" if ok else "DEAD"
json.dump(out, open(OUT, "w"), indent=1)
print(json.dumps({k: v for k, v in out.items() if k != "rows"}, indent=1))
