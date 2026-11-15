"""Cycle 20 (N47 follow-up + N48), read-only, runs via run_script.yml (Iowa Mesonet is not reachable from the sandbox).
Question: in 'Where will it rain on <date>' city markets (resolve on the NWS CLI PRECIPITATION >= 0.01 in, LST climate day), were the
tape fills already decided by public hourly METARs at fill time?
  N47 (after the day): fill time >= climate-day end + 15 min -> METAR side = YES if the day's hourly precip sum >= 0.01 else NO.
  N48 (running count, adjacent): fill time inside the climate day and the METAR sum so far (obs <= t - 15 min) >= 0.01 -> YES is locked
       (rain cannot un-happen); take YES fills only.
Rules fixed before looking: fills 0.03-0.97 on the METAR side, points per share = win - price - fee, cluster = date (one weather day).
Also: METAR-final vs resolution agreement, IEM-archived CLI vs resolution (is our station the market's station?), CLI issue time split.
Data: entries_a/b/c (real taker fills, fees, receive order). METARs: IEM ASOS routine hourly p01i (report_type=3, no specials -> no
double count). Output data/research/riskday_metar.json."""
import json, gzip, struct, collections, random, re, time, datetime as dt, requests
ROW = struct.Struct("<IIIhfffHHHIB")
B = "data/research/"
random.seed(48)
ST = {"New York, NY": ("NYC", -5), "Atlanta, GA": ("ATL", -5), "Boston, MA": ("BOS", -5), "Miami, FL": ("MIA", -5),
      "Philadelphia, PA": ("PHL", -5), "Washington, DC": ("DCA", -5), "Chicago, IL": ("ORD", -6), "Dallas, TX": ("DFW", -6),
      "Houston, TX": ("IAH", -6), "New Orleans, LA": ("MSY", -6), "Denver, CO": ("DEN", -7), "Phoenix, AZ": ("PHX", -7),
      "Los Angeles, CA": ("LAX", -8), "San Francisco, CA": ("SFO", -8), "Seattle, WA": ("SEA", -8)}
MON = {m: i for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
                                   "november", "december"], 1)}
R = []; seen = set(); mk = {}
for g in "abc":
    meta = json.load(gzip.open(f"{B}entries_{g}_meta.json.gz")); MK = meta["markets"]
    idx = {}
    for i, m in enumerate(MK):
        if "where-will-it-rain" in m[1]:
            city = re.sub(r" on .*", "", m[3].replace("Will it rain in ", ""))
            mm = re.search(r"on-([a-z]+)-(\d+)-(\d{4})", m[1])
            idx[i] = (city, dt.date(int(mm.group(3)), MON[mm.group(1)], int(mm.group(2))))
    blob = gzip.open(f"{B}entries_{g}.bin.gz").read()
    for t, mi, wi, hb, S, C, F, a, a60, a300, lag, fl in ROW.iter_unpack(blob):
        if mi not in idx or S <= 0 or C <= 0:
            continue
        m = MK[mi]; key = (m[0], t, wi, S, C)
        if key in seen:
            continue
        seen.add(key)
        city, day = idx[mi]
        yes = bool(fl & 1); win = 1 if fl & 2 else 0
        R.append(dict(e=m[1], city=city, day=day, t=t, hb=hb, p=C / S, fee=F / S, yes=yes, win=win, mid=m[0]))
        mk[m[0]] = (city, day, win if yes else 1 - win)
    del blob
print("fills", len(R), "markets", len(mk), "dates", len({r["e"] for r in R}))
days = sorted({r["day"] for r in R}); d0, d1 = days[0] - dt.timedelta(days=1), days[-1] + dt.timedelta(days=2)

Sess = requests.Session(); Sess.headers["User-Agent"] = "polymarket-lab research (read-only)"
obs = {}; cli = {}
for city, (st, off) in ST.items():
    url = "https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py"
    q = {"station": st, "data": "p01i", "year1": d0.year, "month1": d0.month, "day1": d0.day, "year2": d1.year, "month2": d1.month,
         "day2": d1.day, "tz": "Etc/UTC", "format": "onlycomma", "missing": "M", "trace": "0.0001", "report_type": "3"}
    txt = None
    for k in range(3):
        try:
            r = Sess.get(url, params=q, timeout=60)
            if r.status_code == 200:
                txt = r.text; break
            print("http", r.status_code, st)
        except Exception as ex:
            print("err", type(ex).__name__, st)
        time.sleep(3)
    v = []
    for line in (txt or "").splitlines()[1:]:
        p = line.split(",")
        if len(p) < 3 or p[2] in ("M", ""):
            continue
        ts = dt.datetime.strptime(p[1], "%Y-%m-%d %H:%M").replace(tzinfo=dt.timezone.utc).timestamp()
        v.append((ts, float(p[2])))
    obs[city] = v
    for yr in sorted({d.year for d in days}):
        try:
            j = Sess.get("https://mesonet.agron.iastate.edu/json/cli.py", params={"station": "K" + st, "year": yr}, timeout=60).json()
            for x in j.get("results", []):
                cli[(city, x.get("valid"))] = (x.get("precip"), x.get("product"))
        except Exception as ex:
            print("cli err", st, type(ex).__name__)
    print(st, "obs", len(v), "cli", sum(1 for k in cli if k[0] == city))
    time.sleep(1)


def win_lo(city, day):
    off = ST[city][1]
    s = dt.datetime(day.year, day.month, day.day, tzinfo=dt.timezone.utc).timestamp() - off * 3600
    return s, s + 86400


def msum(city, s, e):
    return sum(p for ts, p in obs.get(city, []) if s < ts <= e)


# market-level agreement
agree = collections.Counter(); miss = []
for mid, (city, day, yout) in mk.items():
    s, e = win_lo(city, day)
    ms = msum(city, s, e); n_obs = sum(1 for ts, p in obs.get(city, []) if s < ts <= e)
    met = None if n_obs < 18 else int(ms >= 0.0095)
    c = cli.get((city, day.isoformat()))
    cy = None
    if c and c[0] is not None:
        try:
            cy = int(float(c[0]) >= 0.0095)
        except (TypeError, ValueError):
            cy = int(str(c[0]).upper() not in ("T", "M", "0", "0.00"))
    agree[("metar", met == yout if met is not None else "na")] += 1
    agree[("cli", cy == yout if cy is not None else "na")] += 1
    if met is not None and met != yout:
        miss.append((city, day.isoformat(), "metar_sum", round(ms, 3), "res_yes", yout, "cli", c[0] if c else None))


def stat(rows):
    ev = collections.defaultdict(lambda: [0.0, 0])
    for r in rows:
        ev[r["e"]][0] += r["win"] - r["p"] - r["fee"]; ev[r["e"]][1] += 1
    v = list(ev.values()); n = sum(y[1] for y in v)
    o = {"n": n, "dates": len(v), "pts": round(100 * sum(y[0] for y in v) / n, 2) if n else None,
         "avg_p": round(sum(r["p"] for r in rows) / n, 3) if n else None, "won": sum(r["win"] for r in rows),
         "dates_pos": sum(1 for y in v if y[0] > 0), "usd_at_1sh": round(sum(y[0] for y in v), 2)}
    if len(v) >= 5:
        bs = []
        for _ in range(1000):
            s_ = [v[int(random.random() * len(v))] for _i in v]
            bs.append(sum(y[0] for y in s_) / max(1, sum(y[1] for y in s_)))
        bs.sort(); o["ci"] = [round(100 * bs[25], 1), round(100 * bs[974], 1)]
    return o


LAG = 15 * 60
after, running, after_pre_cli, after_post_cli, fav_after, against = [], [], [], [], [], []
for r in R:
    if not (0.03 <= r["p"] <= 0.97):
        continue
    s, e = win_lo(r["city"], r["day"])
    known = r["t"] - LAG
    if known >= e:
        n_obs = sum(1 for ts, p in obs.get(r["city"], []) if s < ts <= e)
        if n_obs < 18:
            continue
        side_yes = msum(r["city"], s, e) >= 0.0095
        if r["yes"] == side_yes:
            after.append(r)
            c = cli.get((r["city"], r["day"].isoformat()))
            ct = None
            if c and c[1]:
                try:
                    ct = dt.datetime.strptime(c[1][:12], "%Y%m%d%H%M").replace(tzinfo=dt.timezone.utc).timestamp()
                except ValueError:
                    pass
            if ct is not None:
                (after_pre_cli if r["t"] < ct else after_post_cli).append(r)
        else:
            against.append(r)
        if r["p"] >= 0.60:
            fav_after.append(r)
    elif known >= s and r["yes"] and msum(r["city"], s, known) >= 0.0095:
        running.append(r)
out = {"agreement": {f"{k[0]}:{k[1]}": v for k, v in agree.items()}, "metar_mismatch": miss[:40],
       "N47 after-day METAR side": stat(after), "N47 after-day, before the archived CLI product": stat(after_pre_cli),
       "N47 after-day, after the archived CLI product": stat(after_post_cli),
       "after-day favourite 0.60-0.97 (baseline)": stat(fav_after), "after-day fills AGAINST the METAR side": stat(against),
       "N48 running: YES fills after METAR >= 0.01 so far": stat(running)}
for lo, hi in ((0.03, 0.80), (0.80, 0.93), (0.93, 0.97)):
    out[f"N47 after-day METAR side p {lo}-{hi}"] = stat([r for r in after if lo <= r["p"] < hi + 1e-9])
    out[f"N48 running p {lo}-{hi}"] = stat([r for r in running if lo <= r["p"] < hi + 1e-9])
print(json.dumps(out, indent=1, default=str))
json.dump(out, open(f"{B}riskday_metar.json", "w"), indent=1, default=str)
