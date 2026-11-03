"""Longer price history for the market-making universe: hourly prices for the last DAYS days for
every reward market, from the CLOB prices-history endpoint (fidelity 60).

Two outputs:
  data/live/volfeat/<date>.json.gz   {cid: [std of hourly moves, max abs hourly move, n_hours]} over
                                     the last 14 days - what the quoter's ranking uses (small, daily)
  data/live/hist/<date>.json.gz      full histories {cid: [[ts, p], ...]} - only when FULL=1 (one-off,
                                     for the replay; ~30 MB)
Incremental is not needed: one call per market returns the window.
"""
import glob, gzip, json, os, sys, time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import collect  # noqa: E402

DAYS = int(os.environ.get("DAYS", "14"))
FULL = os.environ.get("FULL") == "1"
budget = time.time() + float(os.environ.get("BUDGET_MIN", "120")) * 60
files = sorted(glob.glob("data/live/rewards/*.jsonl.gz"))
toks = {}
for m in collect.read_jsonl_gz(files[-1]):
    r = m.get("rewards") or {}
    rate = sum(x.get("rewards_daily_rate") or 0 for x in r.get("rates") or [])
    t = m.get("tokens") or []
    if rate > 0 and t:
        toks[m["condition_id"]] = str(t[0]["token_id"])
print(f"{len(toks)} reward markets", flush=True)
now = int(time.time())


def fetch(item):
    cid, tok = item
    if time.time() > budget:
        return cid, None
    # the API caps startTs/endTs windows (~2 weeks at fidelity 60?): use the interval shorthand, then 7-day windows
    d = collect.get(f"{collect.CLOB}/prices-history", {"market": tok, "interval": "1m", "fidelity": 60})
    hist = (d or {}).get("history") or []
    if len(hist) < 12:
        hist = []
        t = now - DAYS * 86400
        while t < now:
            d = collect.get(f"{collect.CLOB}/prices-history", {"market": tok, "startTs": t, "endTs": min(t + 7 * 86400, now), "fidelity": 60})
            hist += (d or {}).get("history") or []
            t += 7 * 86400
    h = sorted({(int(x["t"]), float(x["p"])) for x in hist if "t" in x and "p" in x})
    return cid, [list(x) for x in h]


feat, full = {}, {}
done = 0
with ThreadPoolExecutor(6) as ex:
    for cid, h in ex.map(fetch, list(toks.items())):
        done += 1
        if h is None:
            continue
        if FULL:
            full[cid] = h
        ps = [p for _, p in h]
        if len(ps) >= 12:
            d = [abs(b - a) for a, b in zip(ps, ps[1:])]
            feat[cid] = [round((sum(x * x for x in d) / len(d)) ** 0.5, 5), round(max(d), 4), len(ps)]
        if done % 2000 == 0:
            print(f"{done} markets, {len(feat)} with features", flush=True)
day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
os.makedirs("data/live/volfeat", exist_ok=True)
with gzip.open(f"data/live/volfeat/{day}.json.gz", "wt") as fh:
    json.dump(feat, fh, separators=(",", ":"))
if FULL:
    os.makedirs("data/live/hist", exist_ok=True)
    with gzip.open(f"data/live/hist/{day}.json.gz", "wt") as fh:
        json.dump(full, fh, separators=(",", ":"))
print(f"finished: {done} markets, {len(feat)} features, full={len(full)}")
