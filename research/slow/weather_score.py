"""Score weather W1 forecasts against outcomes: Brier of model vs market per bucket, for events whose markets are all closed.

Model p and market price are taken from the FIRST non-same-day obs snapshot of each event (what paper traded on).
Market price = mid of yes bid/ask when both exist, else yes ask. Outcome from Gamma outcomePrices (YES = 1).
Also lists 'dead bucket' same-day cases from sameday.jsonl with their outcome.
Writes data/research/weather_score.json.
"""
import json, time
from collections import defaultdict
import requests

G = "https://gamma-api.polymarket.com"
obs = defaultdict(list)
for line in open("data/weather/obs.jsonl"):
    o = json.loads(line)
    if not o.get("same_day"):
        obs[o["event"]].append(o)
models = {}
for line in open("data/weather/positions.jsonl"):
    p = json.loads(line)
    models.setdefault(p["event"], p.get("model", "?"))

today = time.strftime("%Y-%m-%d", time.gmtime())
rows = []
for ev, L in obs.items():
    if L[0]["date"] >= today:
        continue
    first_ts = min(o["ts"] for o in L)
    snap = {o["market_id"]: o for o in L if o["ts"] == first_ts}
    try:
        r = requests.get(f"{G}/events", params={"slug": ev}, timeout=20).json()
    except Exception as e:  # noqa: BLE001
        print("fetch fail", ev, e); continue
    if not r:
        continue
    mk = r[0].get("markets") or []
    if not mk or not all(m.get("closed") for m in mk):
        continue
    for m in mk:
        o = snap.get(str(m["id"]))
        if not o:
            continue
        try:
            y = float(json.loads(m["outcomePrices"])[0])
        except Exception:  # noqa: BLE001
            continue
        if y not in (0.0, 1.0):
            continue
        a, b = o.get("yes_ask"), o.get("yes_bid")
        mkt = (a + b) / 2 if a is not None and b is not None else a
        if mkt is None or o.get("p") is None:
            continue
        rows.append({"event": ev, "bucket": o["bucket"], "p": o["p"], "mkt": mkt, "y": y, "lead_snapshot": first_ts})
    time.sleep(0.15)

ev_n = len({r["event"] for r in rows})
bm = sum((r["p"] - r["y"]) ** 2 for r in rows) / max(len(rows), 1)
bk = sum((r["mkt"] - r["y"]) ** 2 for r in rows) / max(len(rows), 1)
print(f"settled events {ev_n}, buckets {len(rows)}: Brier model {bm:.4f} vs market {bk:.4f}")
# per-event log-score on the winning bucket
win = [r for r in rows if r["y"] == 1]
print(f"winning bucket: model p mean {sum(r['p'] for r in win) / max(len(win), 1):.3f}  market {sum(r['mkt'] for r in win) / max(len(win), 1):.3f}")
for r in sorted(win, key=lambda r: r["p"] - r["mkt"])[:5] + sorted(win, key=lambda r: r["p"] - r["mkt"])[-5:]:
    print(f"  {r['event'][:55]:55} {r['bucket']:12} model {r['p']:.3f} mkt {r['mkt']:.3f}")

# same-day 'dead bucket' cases: priced >= 1c while METAR max already exceeded them
dead = []
for line in open("data/weather/sameday.jsonl"):
    o = json.loads(line)
    if o.get("dead") and (o.get("yes_bid") or 0) >= 0.01:
        dead.append(o)
print(f"same-day dead buckets still bid >= 1c: {len(dead)} snapshots")
# did any 'dead' bucket actually win? (would mean our station/rounding reading is wrong)
dead_out = {}
for o in dead:
    k = (o["event"], o["bucket"])
    if k in dead_out:
        continue
    try:
        r = requests.get(f"{G}/events", params={"slug": o["event"]}, timeout=20).json()
        m = [m for m in r[0]["markets"] if m.get("groupItemTitle") == o["bucket"] or o["bucket"] in (m.get("question") or "")]
        dead_out[k] = (float(json.loads(m[0]["outcomePrices"])[0]) if m and m[0].get("closed") else None, o["obs_max"], o["yes_bid"])
    except Exception:  # noqa: BLE001
        dead_out[k] = (None, o["obs_max"], o["yes_bid"])
    time.sleep(0.15)
for k, v in dead_out.items():
    print(f"  dead {k[0][:50]:50} {k[1]:12} obs_max {v[1]} bid {v[2]} -> YES outcome {v[0]}")
json.dump({"at": time.strftime("%Y-%m-%d %H:%M", time.gmtime()), "events": ev_n, "buckets": len(rows), "brier_model": bm,
           "brier_market": bk, "rows": rows, "dead_bid": dead[:200], "dead_outcomes": [[k[0], k[1], *v] for k, v in dead_out.items()]}, open("data/research/weather_score.json", "w"))
