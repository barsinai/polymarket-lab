"""Download archived weather forecasts (Open-Meteo 'previous runs' API, free) for the cities
Polymarket lists daily-high-temperature markets for.

For every hour since 2024-06-01: temperature_2m (the model's best estimate of what happened),
and temperature_2m_previous_day1 / _day2 (what the forecast said 1 / 2 days earlier).
A 2-day-old forecast is safely public before any bet made 1 day before the date.
Saves data/external/weather/<city>.json.gz {"tz": ..., "time": [...], "t0": [...], "t1": [...], "t2": [...]}
(degrees C, local time).
"""
import gzip, json, os, time
from datetime import date
import requests

# approximate coordinates of each city's main airport (Polymarket resolves on airport stations)
CITIES = {
    "London": (51.505, 0.055), "New York City": (40.777, -73.874), "Paris": (49.009, 2.548),
    "Hong Kong": (22.309, 113.915), "Shanghai": (31.144, 121.808), "Atlanta": (33.637, -84.428),
    "Seoul": (37.469, 126.451), "Beijing": (40.080, 116.585), "Wellington": (-41.327, 174.805),
    "Dallas": (32.847, -96.852), "Seattle": (47.450, -122.309), "Miami": (25.796, -80.287),
    "Tokyo": (35.553, 139.781), "Buenos Aires": (-34.822, -58.536), "Chicago": (41.979, -87.904),
    "Shenzhen": (22.639, 113.811), "Ankara": (40.128, 32.995), "Munich": (48.354, 11.786),
    "Madrid": (40.472, -3.561), "Toronto": (43.677, -79.630), "Chengdu": (30.579, 103.947),
    "Taipei": (25.077, 121.233), "Singapore": (1.364, 103.991), "Chongqing": (29.719, 106.642),
    "Los Angeles": (33.942, -118.408), "Lucknow": (26.761, 80.889), "Sao Paulo": (-23.435, -46.473),
    "São Paulo": (-23.435, -46.473), "Mexico City": (19.436, -99.072), "Moscow": (55.973, 37.415),
    "Istanbul": (41.275, 28.752), "Denver": (39.856, -104.674), "Houston": (29.990, -95.337),
    "Phoenix": (33.434, -112.012), "Boston": (42.366, -71.010), "Washington DC": (38.851, -77.040),
    "San Francisco": (37.619, -122.375), "Philadelphia": (39.872, -75.241), "Austin": (30.194, -97.670),
    "Sydney": (-33.946, 151.177), "Berlin": (52.366, 13.503), "Rome": (41.800, 12.239),
    "Dubai": (25.253, 55.366), "Mumbai": (19.090, 72.866), "Delhi": (28.556, 77.100),
    "Jakarta": (-6.126, 106.656), "Bangkok": (13.690, 100.750), "Cairo": (30.122, 31.406),
    "Wuhan": (30.784, 114.208), "Guangzhou": (23.392, 113.299), "Hangzhou": (30.229, 120.434),
}
S = requests.Session(); S.headers["User-Agent"] = "polymarket-lab-research/0.1"
os.makedirs("data/external/weather", exist_ok=True)
for city, (lat, lon) in CITIES.items():
    out = f"data/external/weather/{city}.json.gz"
    for k in range(4):
        r = S.get("https://previous-runs-api.open-meteo.com/v1/forecast",
                  params={"latitude": lat, "longitude": lon, "timezone": "auto",
                          "hourly": "temperature_2m,temperature_2m_previous_day1,temperature_2m_previous_day2",
                          "start_date": "2024-06-01", "end_date": date.today().isoformat()}, timeout=120)
        if r.status_code == 200:
            break
        print(city, r.status_code, r.text[:300], flush=True); time.sleep(5 * (k + 1))
    if r.status_code != 200:
        continue
    d = r.json(); h = d["hourly"]
    with gzip.open(out, "wt") as f:
        json.dump({"tz": d.get("timezone"), "utc_offset_s": d.get("utc_offset_seconds"), "time": h["time"],
                   "t0": h["temperature_2m"], "t1": h["temperature_2m_previous_day1"],
                   "t2": h["temperature_2m_previous_day2"]}, f)
    n2 = sum(x is not None for x in h["temperature_2m_previous_day2"])
    print(f"{city}: {len(h['time'])} hours, {n2} with 2-day-old forecast", flush=True)
    time.sleep(1)
