"""Weather W1 paper tracker (NO ORDERS): daily highest-temperature markets vs weather-model ensembles.

Each run (hourly): for every open event 'highest-temperature-in-<city>-on-<date>' (today .. +2 days):
  1. station: the ICAO code in the rules (METAR at that airport) -> coordinates from aviationweather.gov stationinfo;
     a few cities resolve on a national office instead (Hong Kong Observatory): fixed coordinates.
  2. model: Open-Meteo ensembles (ECMWF IFS 51 + GFS 31 + ICON 40 members), HOURLY 2 m temperature at the station,
     per member the max over the station's local date (the rules count only the hourly reports) -> per-member value +
     Gaussian kernel (sd = KERNEL, station-vs-grid error) -> probability of each whole-degree bucket after the rules'
     rounding (half up). Same-day events: members are floored at the max already observed in today's METARs.
  3. market: best YES ask / bid of every bucket (CLOB books).
  4. log every bucket (model p, ask, bid) to data/weather/obs.jsonl for calibration (Brier model vs market), and paper-buy
     YES where p - ask >= EDGE (ask 0.03-0.70) and NO where (1 - p) - noask >= EDGE, $STAKE, once per bucket.
  5. settle positions of closed events from the market outcome.
"""
import json, math, os, re, time, datetime as dt
from zoneinfo import ZoneInfo
import requests

D = "data/weather"; os.makedirs(D, exist_ok=True)
GAMMA = "https://gamma-api.polymarket.com"; CLOB = "https://clob.polymarket.com"
EDGE = float(os.environ.get("EDGE", "0.08")); STAKE = float(os.environ.get("STAKE", "5")); KERNEL = float(os.environ.get("KERNEL", "1.0"))
S = requests.Session(); S.headers["User-Agent"] = "polymarket-lab-research/0.1"
now = dt.datetime.now(dt.timezone.utc)
FIXED = {"hong-kong": (22.302, 114.174, "Asia/Hong_Kong")}
MODELS = ["ecmwf_ifs025", "gfs_seamless", "icon_seamless"]
_ens_cache = {}


def get(url, params=None, tries=3, timeout=25):
    for i in range(tries):
        try:
            r = S.get(url, params=params, timeout=timeout)
            if r.status_code == 200:
                return r.json()
            time.sleep(1 + i)
        except Exception:  # noqa: BLE001
            time.sleep(1 + i)
    return None


def load(path, default):
    try:
        return json.load(open(path))
    except (OSError, ValueError):
        return default


stations = load(f"{D}/stations.json", {})
pos_path = f"{D}/positions.jsonl"
positions = [json.loads(l) for l in open(pos_path)] if os.path.exists(pos_path) else []
held = {(p["market_id"], p["side"]) for p in positions}

# ---- events
evs = []
for q in ("highest temperature",):
    r = get(f"{GAMMA}/public-search", {"q": q, "limit_per_type": 200, "events_status": "active"})
    evs += [e for e in (r or {}).get("events") or [] if e.get("slug", "").startswith("highest-temperature-in-")]
seen = set(); events = []
for e in evs:
    if e["slug"] in seen:
        continue
    seen.add(e["slug"])
    full = get(f"{GAMMA}/events", {"slug": e["slug"]})
    if full:
        events.append(full[0])
print("open temperature events", len(events), flush=True)


def station_for(ev):
    city = ev["slug"].replace("highest-temperature-in-", "").rsplit("-on-", 1)[0]
    if city in FIXED:
        return city, FIXED[city]
    m = re.search(r"\(([A-Z]{4})\)", ev.get("description") or "")
    if not m:
        return city, None
    icao = m.group(1)
    if icao not in stations:
        info = get("https://aviationweather.gov/api/data/stationinfo", {"ids": icao, "format": "json"})
        if info:
            st = info[0]
            stations[icao] = (st["lat"], st["lon"], None)
    if icao in stations:
        return icao, tuple(stations[icao])
    return icao, None


def tz_of(lat, lon):
    r = get("https://api.open-meteo.com/v1/forecast", {"latitude": lat, "longitude": lon, "hourly": "temperature_2m", "forecast_days": 1, "timezone": "auto"})
    return (r or {}).get("timezone")


def members(lat, lon, tz, date, unit):
    """per-member max of the hourly 2 m temperature over the local date, in the event's unit"""
    vals = []
    for model in MODELS:
        key = (lat, lon, tz, unit, model)
        if key not in _ens_cache:
            _ens_cache[key] = get("https://ensemble-api.open-meteo.com/v1/ensemble", {"latitude": lat, "longitude": lon, "hourly": "temperature_2m", "models": model,
                                  "timezone": tz, "forecast_days": 4, "temperature_unit": "fahrenheit" if unit == "F" else "celsius"}, timeout=40)
        r = _ens_cache[key]
        if not r or "hourly" not in r:
            continue
        h = r["hourly"]; idx = [i for i, t in enumerate(h["time"]) if t.startswith(date)]
        if len(idx) < 20:
            continue
        for k, v in h.items():
            if k.startswith("temperature_2m"):
                xs = [v[i] for i in idx if v[i] is not None]
                if len(xs) >= 20:
                    vals.append(max(xs))
    return vals


def observed_max(icao, tz, date):
    """max hourly METAR temperature so far on the local date (rules: the T-group remark, else the body group)"""
    r = get("https://aviationweather.gov/api/data/metar", {"ids": icao, "format": "json", "hours": 36})
    best = None
    for o in r or []:
        try:
            t = dt.datetime.fromisoformat(str(o.get("reportTime")).replace("Z", "+00:00")).astimezone(ZoneInfo(tz))
        except Exception:  # noqa: BLE001
            continue
        if t.strftime("%Y-%m-%d") != date or str(o.get("rawOb", "")).startswith("SPECI"):
            continue
        m = re.search(r"\sT([01])(\d{3})[01]\d{3}", o.get("rawOb", ""))
        v = (-1 if m.group(1) == "1" else 1) * int(m.group(2)) / 10 if m else o.get("temp")
        if v is not None and (best is None or v > best):
            best = v
    return best


def rnd(x):
    return math.floor(x + 0.5)


def bucket_probs(vals, buckets, floor=None, unit="C"):
    """buckets: list of (lo, hi) whole degrees inclusive (None = open end); P(rounded value in bucket) under a kernel mix"""
    if floor is not None:
        vals = [max(v, floor) for v in vals]
    phi = lambda z: 0.5 * (1 + math.erf(z / math.sqrt(2)))
    k = KERNEL * (1.8 if unit == "F" else 1.0)
    out = []
    for lo, hi in buckets:
        a = -1e9 if lo is None else lo - 0.5; b = 1e9 if hi is None else hi + 0.5   # rounding half up: [n-0.5, n+0.5)
        p = sum(phi((b - v) / k) - phi((a - v) / k) for v in vals) / len(vals)
        out.append(p)
    s = sum(out)
    return [p / s for p in out] if s > 0 else out


def parse_bucket(title):
    t = title.replace("°", "").replace("º", "")
    unit = "F" if "F" in t else "C"
    nums = [int(x) for x in re.findall(r"-?\d+", t)]
    if re.search(r"or below|or lower|or less", t, re.I):
        return (None, nums[0]), unit
    if re.search(r"or higher|or above|or more", t, re.I):
        return (nums[0], None), unit
    if len(nums) == 2:
        return (nums[0], nums[1]), unit
    if len(nums) == 1:
        return (nums[0], nums[0]), unit
    return None, unit


# ---- books for all bucket tokens
rows = []
for ev in events:
    city_date = ev["slug"].replace("highest-temperature-in-", "")
    date_txt = city_date.rsplit("-on-", 1)[1]
    try:
        date = dt.datetime.strptime(date_txt, "%B-%d-%Y").strftime("%Y-%m-%d")
    except ValueError:
        continue
    for m in ev.get("markets") or []:
        if not m.get("active") or m.get("closed"):
            continue
        b, unit = parse_bucket(m.get("groupItemTitle") or "")
        if b is None:
            continue
        try:
            toks = json.loads(m["clobTokenIds"])
        except (KeyError, ValueError):
            continue
        rows.append({"event": ev["slug"], "date": date, "market_id": m["id"], "title": m.get("groupItemTitle"), "bucket": b, "unit": unit, "yes": toks[0], "no": toks[1], "ev": ev})
toks = [r["yes"] for r in rows] + [r["no"] for r in rows]
B = {}
for i in range(0, len(toks), 400):
    try:
        resp = S.post(f"{CLOB}/books", json=[{"token_id": t} for t in toks[i:i + 400]], timeout=40)
        for bk in resp.json():
            asks = sorted((float(a["price"]), float(a["size"])) for a in bk.get("asks") or [])
            bids = sorted(((float(a["price"]), float(a["size"])) for a in bk.get("bids") or []), reverse=True)
            B[bk["asset_id"]] = (asks[0] if asks else None, bids[0] if bids else None)
    except Exception as e:  # noqa: BLE001
        print("books error", e)
print("bucket markets", len(rows), "books", len(B), flush=True)

# ---- model per event
by_ev = {}
for r in rows:
    by_ev.setdefault(r["event"], []).append(r)
obs_out = open(f"{D}/obs.jsonl", "a"); n_new = 0; n_ev = 0
for slug, R in by_ev.items():
    ev = R[0]["ev"]; sid, loc = station_for(ev)
    if not loc:
        print("no station for", slug); continue
    lat, lon, tz = loc
    if not tz:
        tz = tz_of(lat, lon)
        if not tz:
            continue
        if sid in stations:
            stations[sid] = (lat, lon, tz)
    date = R[0]["date"]; unit = R[0]["unit"]
    local_today = now.astimezone(ZoneInfo(tz)).strftime("%Y-%m-%d")
    if date < local_today:
        continue
    vals = members(lat, lon, tz, date, unit)
    if len(vals) < 20:
        print("too few members", slug, len(vals)); continue
    floor = None
    if date == local_today and re.fullmatch(r"[A-Z]{4}", sid):
        om = observed_max(sid, tz, date)
        if om is not None:
            floor = om * 9 / 5 + 32 if unit == "F" else om
    R.sort(key=lambda r: (r["bucket"][0] if r["bucket"][0] is not None else -1e9))
    ps = bucket_probs(vals, [r["bucket"] for r in R], floor, unit)
    n_ev += 1
    for r, p in zip(R, ps):
        ya, yb = B.get(r["yes"], (None, None)); na, _ = B.get(r["no"], (None, None))
        rec = {"ts": now.strftime("%Y-%m-%d %H:%M"), "event": slug, "station": sid, "date": date, "same_day": date == local_today, "bucket": r["title"],
               "market_id": r["market_id"], "p": round(p, 4), "yes_ask": ya[0] if ya else None, "yes_ask_sz": ya[1] if ya else None,
               "yes_bid": yb[0] if yb else None, "no_ask": na[0] if na else None, "n_members": len(vals), "floor": floor,
               "ens_mean": round(sum(vals) / len(vals), 2)}
        obs_out.write(json.dumps(rec) + "\n")
        for side, ask, prob, sz in (("YES", ya[0] if ya else None, p, ya[1] if ya else 0), ("NO", na[0] if na else None, 1 - p, na[1] if na else 0)):
            if ask is None or (r["market_id"], side) in held:
                continue
            if side == "YES" and not (0.03 <= ask <= 0.70):
                continue
            if side == "NO" and not (0.30 <= ask <= 0.97):
                continue
            if prob - ask >= EDGE and sz * ask >= STAKE:
                positions.append({"opened": rec["ts"], "event": slug, "date": date, "same_day": rec["same_day"], "bucket": r["title"], "market_id": r["market_id"],
                                  "side": side, "ask": ask, "shares": round(STAKE / ask, 2), "p": round(prob, 4), "ens_mean": rec["ens_mean"], "floor": floor, "resolved": False})
                held.add((r["market_id"], side)); n_new += 1
obs_out.close()

# ---- settle
n_set = 0
for p in positions:
    if p.get("resolved"):
        continue
    m = get(f"{GAMMA}/markets/{p['market_id']}")
    if not m:
        continue
    try:
        pr = [float(x) for x in json.loads(m.get("outcomePrices") or "[]")]
    except ValueError:
        continue
    if m.get("closed") and pr and max(pr) >= 0.99:
        y = int(pr[0] > pr[1]); win = (y == 1) == (p["side"] == "YES")
        p.update(resolved=True, won=int(win), pnl=round(p["shares"] * ((1 if win else 0) - p["ask"]), 2)); n_set += 1
with open(pos_path, "w") as fh:
    for p in positions:
        fh.write(json.dumps(p) + "\n")
json.dump(stations, open(f"{D}/stations.json", "w"))
done = [p for p in positions if p.get("resolved")]
rep = {"updated": now.strftime("%Y-%m-%d %H:%M"), "events_modelled": n_ev, "new_positions": n_new, "open": sum(1 for p in positions if not p.get("resolved")),
       "settled": len(done), "won": sum(p["won"] for p in done), "pnl": round(sum(p["pnl"] for p in done), 2),
       "staked_settled": round(sum(p["shares"] * p["ask"] for p in done), 2),
       "by_side": {s: {"n": sum(1 for p in done if p["side"] == s), "won": sum(p["won"] for p in done if p["side"] == s),
                       "pnl": round(sum(p["pnl"] for p in done if p["side"] == s), 2)} for s in ("YES", "NO")}}
json.dump(rep, open(f"{D}/report.json", "w"), indent=1)
print(json.dumps(rep))
