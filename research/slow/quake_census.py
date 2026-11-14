"""N24 (outside the box, 11-14 c10): earthquake markets vs the USGS catalog. Read-only.
Question: after a qualifying quake (USGS origin time), how fast does the YES price of 'earthquake M>=X by date / in month' markets go
to >= 0.95, and was there ever an executable-looking gap (hourly last price < 0.90 more than 1 h after the quake)? Also: markets that
resolved NO although a quake within 0.1 of the threshold happened (magnitude revisions = fine print).
Gamma closed events matching 'earthquake' -> markets -> CLOB prices-history (hourly); USGS FDSN M>=5.5 catalog for the span.
Writes data/research/quake_census.json."""
import json, re, time, datetime as dt
import requests
S = requests.Session(); S.headers["User-Agent"] = "polymarket-lab-research/0.1"
G = "https://gamma-api.polymarket.com"


def get(u, p, tries=3):
    for i in range(tries):
        try:
            r = S.get(u, params=p, timeout=30)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 429:
                time.sleep(2 + 2 * i); continue
            return None
        except Exception:  # noqa: BLE001
            time.sleep(1 + i)
    return None


mk = {}
for closed in ("true", "false"):
    for off in range(0, 2000, 100):
        page = get(f"{G}/events", {"closed": closed, "limit": 100, "offset": off, "title_contains": "earthquake"}) or []
        hits = [e for e in page if "earthquake" in (e.get("title") or "").lower()]
        for e in hits:
            for m in e.get("markets") or []:
                mk[m["id"]] = dict(m, ev=e.get("title"))
        if len(page) < 100:
            break
if len(mk) < 5:   # title_contains may be ignored: fall back to the search endpoint
    r = get(f"{G}/public-search", {"q": "earthquake", "limit_per_type": 100, "events_status": "all"}) or {}
    for e in r.get("events") or []:
        full = get(f"{G}/events/{e['id']}", {}) or e
        for m in full.get("markets") or []:
            mk[m["id"]] = dict(m, ev=full.get("title"))
print("markets", len(mk), flush=True)
starts = [m.get("startDate") or m.get("createdAt") for m in mk.values() if m.get("startDate") or m.get("createdAt")]
t0 = min(starts)[:10] if starts else "2024-01-01"
q = get("https://earthquake.usgs.gov/fdsnws/event/1/query", {"format": "geojson", "starttime": t0, "minmagnitude": 5.5, "orderby": "time-asc"}) or {}
quakes = [(f["properties"]["time"] / 1000, f["properties"]["mag"], f["properties"]["place"]) for f in q.get("features", [])]
print("usgs quakes M5.5+ since", t0, len(quakes), flush=True)
rows = []
for m in mk.values():
    text = f"{m.get('question')} {m['ev']}"
    mag = re.search(r"(\d(?:\.\d)?)\s*\+?\s*(?:magnitude|or (?:higher|above|greater))|magnitude\s*(\d(?:\.\d)?)|\bM\s?(\d\.\d)", text, re.I)
    try:
        toks = json.loads(m.get("clobTokenIds") or "[]"); out = [float(x) for x in json.loads(m.get("outcomePrices") or "[]")]
        st = dt.datetime.fromisoformat((m.get("startDate") or m["createdAt"]).replace("Z", "+00:00")).timestamp()
        en = dt.datetime.fromisoformat(m["endDate"].replace("Z", "+00:00")).timestamp()
    except Exception:  # noqa: BLE001
        continue
    if not toks:
        continue
    M = float(next(g for g in mag.groups() if g)) if mag else None
    h = (get("https://clob.polymarket.com/prices-history", {"market": toks[0], "startTs": int(st), "endTs": int(en + 86400), "fidelity": 60}) or {}).get("history") or []
    h = [(int(p["t"]), float(p["p"])) for p in h]
    first = next(((t, mg, pl) for t, mg, pl in quakes if M and st <= t <= en and mg >= M), None)
    near = [(round(mg, 1), pl) for t, mg, pl in quakes if M and st <= t <= en and M - 0.15 <= mg < M]
    r = dict(id=m["id"], q=m.get("question"), M=M, closed=m.get("closed"), yes_won=(out[0] > 0.5) if len(out) == 2 and m.get("closed") else None,
             vol=float(m.get("volumeNum") or 0), n_hist=len(h), qualifying_quake=first[:2] if first else None, near_misses=near[:5])
    if first and h:
        tq = first[0]
        after = [(t, p) for t, p in h if t >= tq]
        r["p_before"] = next((p for t, p in reversed(h) if t < tq), None)
        r["h_to_095"] = next((round((t - tq) / 3600, 1) for t, p in after if p >= 0.95), None)
        r["min_p_after_1h"] = min((p for t, p in after if t >= tq + 3600 and t <= tq + 6 * 3600), default=None)
    rows.append(r)
    time.sleep(0.2)
yes = [r for r in rows if r.get("qualifying_quake")]
summ = dict(markets=len(rows), with_threshold=sum(r["M"] is not None for r in rows), with_qualifying_quake=len(yes),
            hours_to_095=sorted(r["h_to_095"] for r in yes if r.get("h_to_095") is not None),
            gap_after_1h_below_090=[(r["q"], r["min_p_after_1h"], r["vol"]) for r in yes if r.get("min_p_after_1h") is not None and r["min_p_after_1h"] < 0.90],
            resolved_against_catalog=[(r["q"], r["yes_won"], r["qualifying_quake"]) for r in rows if r["closed"] and r["M"] and r["yes_won"] is not None and r["yes_won"] != bool(r["qualifying_quake"])],
            near_miss_markets=[(r["q"], r["near_misses"], r["yes_won"]) for r in rows if r["near_misses"] and not r["qualifying_quake"]][:30])
print(json.dumps(summ, indent=1)[:6000])
json.dump(dict(summary=summ, rows=rows), open("data/research/quake_census.json", "w"), indent=1)
