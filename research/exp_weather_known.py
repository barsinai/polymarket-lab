"""Known-outcome test for daily-high temperature markets.
By late evening local time the day's maximum is already in (public airport readings). What did
the WINNING bucket trade at then? If it was still well below $1, buying it is reading the
answer early, not forecasting. Uses our hourly price histories + resolution; local time from
the Open-Meteo city files' UTC offset. Reports price of the eventual winner at 18:00, 21:00,
23:00 local and at +6h after local midnight, with the share of markets where it was < 90c."""
import glob, gzip, json, math, os, re
from collections import defaultdict
from datetime import datetime, timezone, timedelta
import numpy as np
tz = {}
for f in glob.glob("data/external/weather/*.json.gz"):
    d = json.load(gzip.open(f, "rt")); tz[os.path.basename(f)[:-8]] = d.get("utc_offset_s") or 0
RX = re.compile(r"highest temperature in (.+?) be ", re.I)
mk = {}
for f in glob.glob("data/listing/*.gz"):
    for l in gzip.open(f, "rt"):
        if "temperature" not in l:
            continue
        m = json.loads(l); q = m.get("question") or ""
        mm = RX.search(q)
        if not mm or mm.group(1) not in tz:
            continue
        try:
            pr = [float(x) for x in json.loads(m.get("outcomePrices") or "[]")]
            end = datetime.fromisoformat(m["endDate"].replace("Z", "+00:00"))
            md = re.search(r"on (\w+ \d+)\??$", q).group(1)
            day = datetime.strptime(f"{md} {end.year}", "%B %d %Y")
            if day.month == 12 and end.month == 1:
                day = day.replace(year=end.year - 1)
        except Exception:  # noqa: BLE001
            continue
        if len(pr) != 2 or max(pr) < 0.99:
            continue
        won = pr[0] > pr[1]
        local_midnight_utc = day.replace(tzinfo=timezone.utc).timestamp() - tz[mm.group(1)]
        mk[m["id"]] = (won, local_midnight_utc, float(m.get("volumeNum") or 0))
res = defaultdict(list)
n = 0
for f in glob.glob("data/prices/parts/*.jsonl.gz"):
    for l in gzip.open(f, "rt"):
        r = json.loads(l)
        if r["market_id"] not in mk or not r["tokens"] or not r["tokens"][0]["history"]:
            continue
        won, t0, vol = mk[r["market_id"]]
        a = np.array(r["tokens"][0]["history"], float); t_, p_ = a[:, 0], a[:, 1]
        for lab, h in (("18:00 local", 18), ("21:00 local", 21), ("23:00 local", 23), ("06:00 next day", 30)):
            t = t0 + h * 3600
            j = np.searchsorted(t_, t, side="right") - 1
            if j < 0 or t - t_[j] > 2 * 3600:
                continue
            pw = p_[j] if won else 1 - p_[j]  # price of the side that eventually won
            res[lab].append((pw, vol))
        n += 1
print(f"{n} resolved temperature markets with history")
for lab, v in res.items():
    x = np.array(v); pw = x[:, 0]
    print(f"{lab:16} n={len(pw):6} winner's price: median {np.median(pw):.3f}  share <90c {np.mean(pw<0.9):.2f}  share <70c {np.mean(pw<0.7):.2f}  "
          f"profit/$ buying winner at that price (after 0.05*p(1-p) fee): {np.mean(1/pw - 1 - 0.05*(1-pw)):+.3f}")
# but we don't KNOW the winner for sure at 21:00 - how often does the side priced >= 90c at 21:00 lose?
for lab in ("21:00 local", "23:00 local"):
    x = np.array(res[lab]); pw = x[:, 0]
    # markets where SOME side is >= 0.9: if winner's price >= 0.9 it's the favourite; if winner's <= 0.1 the favourite lost
    fav_won = np.sum(pw >= 0.9); fav_lost = np.sum(pw <= 0.1)
    print(f"{lab}: when one side was priced >=90c, it won {fav_won} times and lost {fav_lost} times ({fav_lost/(fav_won+fav_lost):.1%} upsets)")
