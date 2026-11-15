"""N41 checks (cycle 17), read-only: (a) are 'ships transit' count markets live now, with what books and which resolution source;
(b) is the resolving source (IMF PortWatch daily chokepoint transits, ArcGIS) reachable from Actions, and how fresh is its last day.
No orders, no account. Output: data/research/transit_check.json"""
import json, time, datetime as dt, requests
GAMMA = "https://gamma-api.polymarket.com"; CLOB = "https://clob.polymarket.com"
S = requests.Session(); S.headers["User-Agent"] = "polymarket-lab research (read-only)"
out = {"at": dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M"), "markets": [], "closed_examples": [], "portwatch": {}}


def get(url, params=None):
    for i in range(3):
        try:
            r = S.get(url, params=params, timeout=30)
            if r.status_code == 200:
                return r.json()
            print("http", r.status_code, url[:90])
        except Exception as e:
            print("err", type(e).__name__, url[:90])
        time.sleep(2)
    return None


seen = {}
for q in ("ships transit", "transit the Strait", "Strait of Hormuz", "Bab el-Mandeb", "Hormuz"):
    for closed in ("false", "true"):
        d = get(f"{GAMMA}/public-search", {"q": q, "limit_per_type": 50, "events_status": "closed" if closed == "true" else "active"})
        for ev in (d or {}).get("events", []) or []:
            for m in ev.get("markets", []) or []:
                s = m.get("slug", "")
                if s and ("transit" in s or "hormuz" in s or "mandeb" in s):
                    seen[s] = (m, ev)
print("search hits", len(seen))
for s, (m, ev) in seen.items():
    row = {"slug": s, "q": m.get("question"), "end": m.get("endDate"), "closed": m.get("closed"), "active": m.get("active"),
           "outcomePrices": m.get("outcomePrices"), "volume": m.get("volume"), "resolutionSource": m.get("resolutionSource") or ev.get("resolutionSource"),
           "desc": (m.get("description") or ev.get("description") or "")[:700]}
    if not m.get("closed"):
        try:
            tok = json.loads(m.get("clobTokenIds") or "[]")
        except Exception:
            tok = []
        books = []
        for t in tok[:2]:
            b = get(f"{CLOB}/book", {"token_id": t})
            if b:
                bids = sorted((float(x["price"]), float(x["size"])) for x in b.get("bids", []))
                asks = sorted((float(x["price"]), float(x["size"])) for x in b.get("asks", []))
                books.append({"bid": bids[-1] if bids else None, "ask": asks[0] if asks else None})
        row["books"] = books
        out["markets"].append(row)
    elif len(out["closed_examples"]) < 15:
        out["closed_examples"].append(row)
print("live", len(out["markets"]), "closed examples", len(out["closed_examples"]))
for r in out["markets"][:30]:
    print("LIVE", r["end"], r["q"], r.get("books"))
for r in out["closed_examples"][:3]:
    print("CLOSED", r["end"], r["q"], "| src:", r["resolutionSource"], "|", r["desc"][:400].replace("\n", " "))

# (b) PortWatch daily chokepoints (public ArcGIS feature service)
PW = "https://services9.arcgis.com/weJ1QsnbMYJlCHdG/arcgis/rest/services/Daily_Chokepoints_Data/FeatureServer/0/query"
for name in ("Strait of Hormuz", "Bab el-Mandeb Strait"):
    d = get(PW, {"where": f"portname='{name}'", "outFields": "date,portname,n_total,n_tanker,n_cargo", "orderByFields": "date DESC",
                 "resultRecordCount": 10, "f": "json"})
    feats = [f.get("attributes") for f in (d or {}).get("features", [])]
    for f in feats:
        if isinstance(f.get("date"), (int, float)):
            f["date"] = dt.datetime.utcfromtimestamp(f["date"] / 1000).strftime("%Y-%m-%d")
    out["portwatch"][name] = feats or (d if d else "unreachable")
    print("PORTWATCH", name, feats[:4] if feats else str(d)[:300])
json.dump(out, open("data/research/transit_check.json", "w"), indent=1)
