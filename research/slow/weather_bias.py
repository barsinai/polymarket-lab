"""Per-station calibration for the weather tracker (read-only, free public data).
For every station in data/weather/stations.json: the last DAYS days of
  - outcomes: the max of the ROUTINE hourly METAR temperatures per local date (IEM ASOS archive, report_type=3), the
    quantity the markets resolve on;
  - forecasts: Open-Meteo 'previous runs' hourly 2 m temperature as forecast 1 and 2 days before (temperature_2m_previous_day1/2)
    -> its max over the same local date.
bias = mean(outcome - forecast), sd = std of the residual, per station and lead. Writes data/weather/bias.json.
weather_paper.py shifts the ensemble members by the bias and uses the residual sd (lead 1) as its kernel."""
import csv, io, json, math, os, time, datetime as dt
from collections import defaultdict
from zoneinfo import ZoneInfo
import requests

D = "data/weather"; DAYS = int(os.environ.get("DAYS", "60"))
S = requests.Session(); S.headers["User-Agent"] = "polymarket-lab-research/0.1"
stations = json.load(open(f"{D}/stations.json"))
end = dt.date.today(); start = end - dt.timedelta(days=DAYS)
out = {}
for sid, (lat, lon, tz) in stations.items():
    if not tz or len(sid) != 4:
        continue
    # 1. METAR outcomes (IEM: routine METARs only, temperature in C, UTC timestamps)
    url = "https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py"
    params = {"station": sid, "data": "tmpc", "year1": start.year, "month1": start.month, "day1": start.day, "year2": end.year, "month2": end.month, "day2": end.day,
              "tz": "Etc/UTC", "format": "onlycomma", "latlon": "no", "missing": "empty", "trace": "empty", "report_type": "3"}
    try:
        r = S.get(url, params=params, timeout=60)
        rows = list(csv.DictReader(io.StringIO(r.text)))
    except Exception as e:  # noqa: BLE001
        print(sid, "IEM error", e); continue
    obs = defaultdict(lambda: -1e9)
    for row in rows:
        try:
            t = dt.datetime.strptime(row["valid"], "%Y-%m-%d %H:%M").replace(tzinfo=dt.timezone.utc).astimezone(ZoneInfo(tz))
            v = float(row["tmpc"])
        except (ValueError, KeyError, TypeError):
            continue
        d = t.strftime("%Y-%m-%d"); obs[d] = max(obs[d], v)
    # 2. archived forecasts at 1 and 2 days lead
    try:
        f = S.get("https://previous-runs-api.open-meteo.com/v1/forecast", params={"latitude": lat, "longitude": lon, "timezone": tz, "past_days": DAYS, "forecast_days": 1,
                  "hourly": "temperature_2m,temperature_2m_previous_day1,temperature_2m_previous_day2"}, timeout=60).json()
        h = f["hourly"]
    except Exception as e:  # noqa: BLE001
        print(sid, "open-meteo error", e); continue
    fc = {1: defaultdict(lambda: -1e9), 2: defaultdict(lambda: -1e9), 0: defaultdict(lambda: -1e9)}
    for i, t in enumerate(h["time"]):
        d = t[:10]
        for lead, key in ((0, "temperature_2m"), (1, "temperature_2m_previous_day1"), (2, "temperature_2m_previous_day2")):
            v = h.get(key, [None] * len(h["time"]))[i]
            if v is not None:
                fc[lead][d] = max(fc[lead][d], v)
    res = {}
    for lead in (0, 1, 2):
        e = [obs[d] - fc[lead][d] for d in obs if d in fc[lead] and obs[d] > -1e8 and fc[lead][d] > -1e8 and d < end.isoformat()]
        if len(e) >= 15:
            mu = sum(e) / len(e); sd = math.sqrt(sum((x - mu) ** 2 for x in e) / (len(e) - 1))
            res[lead] = {"n": len(e), "bias": round(mu, 2), "sd": round(sd, 2)}
    out[sid] = res
    print(f"{sid}: METAR days {sum(1 for v in obs.values() if v > -1e8)}  " + "  ".join(f"lead{l}: bias {v['bias']:+.2f} sd {v['sd']:.2f} (n {v['n']})" for l, v in res.items()), flush=True)
    time.sleep(0.5)
json.dump(out, open(f"{D}/bias.json", "w"), indent=1)
print("stations calibrated", len(out))
