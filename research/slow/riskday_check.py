"""N47 checks (cycle 19), read-only: (a) resolution rules and live books of 'Which cities face tornado risk on <date>' and 'Where will it
rain on <date>' markets; (b) is the SPC convective outlook (the likely tornado source) reachable from Actions and when was it issued.
No orders, no account. Output: data/research/riskday_check.json"""
import json, time, datetime as dt, requests
GAMMA = "https://gamma-api.polymarket.com"; CLOB = "https://clob.polymarket.com"
S = requests.Session(); S.headers["User-Agent"] = "polymarket-lab research (read-only)"
out = {"at": dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M"), "events": {}, "spc": {}}


def get(url, params=None, js=True):
    for i in range(3):
        try:
            r = S.get(url, params=params, timeout=30)
            if r.status_code == 200:
                return r.json() if js else r.text
            print("http", r.status_code, url[:90])
        except Exception as e:
            print("err", type(e).__name__, url[:90])
        time.sleep(2)
    return None


today = dt.date.today()
for fam, pat in (("tornado", "which-cities-face-tornado-risk-on-{m}-{d}-{y}"), ("rain", "where-will-it-rain-on-{m}-{d}-{y}")):
    for k in range(-10, 4):
        day = today + dt.timedelta(days=k)
        slug = pat.format(m=day.strftime("%B").lower(), d=day.day, y=day.year)
        d = get(f"{GAMMA}/events", {"slug": slug})
        if not d:
            continue
        ev = d[0]; rows = []
        for m in ev.get("markets", []) or []:
            row = {"q": m.get("question"), "end": m.get("endDate"), "closed": m.get("closed"), "prices": m.get("outcomePrices"),
                   "vol": m.get("volume")}
            if not m.get("closed") and len(rows) < 12:
                try:
                    tok = json.loads(m.get("clobTokenIds") or "[]")
                except Exception:
                    tok = []
                if tok:
                    b = get(f"{CLOB}/book", {"token_id": tok[0]})
                    if b:
                        bids = sorted((float(x["price"]), float(x["size"])) for x in b.get("bids", []))
                        asks = sorted((float(x["price"]), float(x["size"])) for x in b.get("asks", []))
                        row["yes_bid"] = bids[-1] if bids else None; row["yes_ask"] = asks[0] if asks else None
            rows.append(row)
        out["events"][slug] = {"end": ev.get("endDate"), "src": ev.get("resolutionSource"), "desc": (ev.get("description") or "")[:1500],
                               "n_markets": len(rows), "markets": rows}
        print(slug, ev.get("endDate"), len(rows), "markets")
for slug, e in list(out["events"].items())[:1] + [x for x in out["events"].items() if "rain" in x[0]][:1]:
    print("RULE", slug, "|", e["src"], "|", e["desc"].replace("\n", " "))
for slug, e in out["events"].items():
    for r in e["markets"]:
        if not r["closed"]:
            print("LIVE", slug[-22:], r["q"], r["prices"], r.get("yes_bid"), r.get("yes_ask"))
# (b) SPC Day 1 categorical outlook GeoJSON (public NOAA product)
for name, url in (("day1_cat", "https://www.spc.noaa.gov/products/outlook/day1otlk_cat.lyr.geojson"),
                  ("day1_torn", "https://www.spc.noaa.gov/products/outlook/day1otlk_torn.lyr.geojson"),
                  ("day2_cat", "https://www.spc.noaa.gov/products/outlook/day2otlk_cat.lyr.geojson")):
    g = get(url)
    if g:
        feats = g.get("features", [])
        out["spc"][name] = [{k: f.get("properties", {}).get(k) for k in ("LABEL", "LABEL2", "VALID", "EXPIRE", "ISSUE", "DN")} for f in feats]
        print("SPC", name, out["spc"][name])
    else:
        out["spc"][name] = None; print("SPC", name, "unreachable")
json.dump(out, open("data/research/riskday_check.json", "w"), indent=1)
