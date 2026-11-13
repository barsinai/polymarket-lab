"""Mention markets at EXECUTABLE prices, on Kalshi's public history (read-only).
Polymarket history said YES is rich in 'what will X say' markets (+14.6%/$ for NO on earnings calls), but only from hourly
LAST TRADE prices (a YES-buyer tape prints near the ask, LESSONS 3). Kalshi publishes hourly candles with the yes BID and ASK,
so the same bias can be checked at prices one could have traded. Steps:
  1. series whose title/category says mention / 'say' (Kalshi 'Mentions' category);
  2. their settled markets (result yes/no), grouped by event;
  3. per event a reference time T = the earliest close among its markets (a word said early closes its market; otherwise the
     scheduled end), so T-3h / T-24h are before the event;
  4. hourly candles -> yes bid/ask at T-24h and T-3h; NO bought at 1 - yes_bid, YES at yes_ask; fee 0.07 p(1-p) per contract.
Output: data/research/kalshi_mentions.json + printed table by YES-price band, counted by EVENT."""
import json, time, collections, random, datetime as dt
import requests

B = "https://api.elections.kalshi.com/trade-api/v2"
S = requests.Session(); S.headers["User-Agent"] = "polymarket-lab-research/0.1"
OUT = "data/research/kalshi_mentions.json"
T0 = time.time()


def get(path, params=None):
    for k in range(4):
        try:
            r = S.get(B + path, params=params, timeout=30)
            if r.status_code == 429:
                time.sleep(1 + 2 * k); continue
            if r.status_code != 200:
                print("  !", r.status_code, path, str(params)[:120], r.text[:150]); return None
            return r.json()
        except Exception as e:  # noqa: BLE001
            print("  !", path, e); time.sleep(1 + k)
    return None


# 1. series
series = []; cur = None
for i in range(50):
    d = get("/series", dict({"limit": 1000}, **({"cursor": cur} if cur else {})))
    if not d:
        break
    series += d.get("series") or []
    cur = d.get("cursor")
    if not cur:
        break
print("series total", len(series), "categories", collections.Counter(s.get("category") for s in series).most_common(15), flush=True)
ms = [s for s in series if (s.get("category") or "").lower().startswith("mention") or "mention" in (s.get("title") or "").lower()
      or " say " in f" {(s.get('title') or '').lower()} " or "MENTION" in (s.get("ticker") or "")]
print("mention series", len(ms), [s.get("ticker") for s in ms[:40]], flush=True)

# 2. settled markets per series
mk = []
for s in ms:
    cur = None
    for i in range(20):
        d = get("/markets", dict({"series_ticker": s["ticker"], "status": "settled", "limit": 1000}, **({"cursor": cur} if cur else {})))
        if not d:
            break
        for m in d.get("markets") or []:
            if m.get("result") in ("yes", "no") and m.get("close_time"):
                mk.append({"series": s["ticker"], "event": m.get("event_ticker"), "ticker": m["ticker"], "result": m["result"],
                           "close": m["close_time"], "open": m.get("open_time"), "title": m.get("title") or m.get("yes_sub_title"),
                           "volume": m.get("volume") or m.get("volume_fp")})
        cur = d.get("cursor")
        if not cur or time.time() - T0 > 900:
            break
print("settled mention markets", len(mk), "events", len({m["event"] for m in mk}), flush=True)


def ts(s):
    return int(dt.datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp())


ev = collections.defaultdict(list)
for m in mk:
    ev[m["event"]].append(m)
evs = sorted(ev, key=lambda e: -min(ts(m["close"]) for m in ev[e]))   # newest first
random.seed(7)
pick = evs[:400]
rows = []
n_calls = 0
for e in pick:
    L = ev[e]; T = min(ts(m["close"]) for m in L)
    for m in L:
        if time.time() - T0 > 3000:
            break
        d = get(f"/series/{m['series']}/markets/{m['ticker']}/candlesticks", {"start_ts": T - 30 * 3600, "end_ts": T, "period_interval": 60})
        n_calls += 1
        if not d:
            continue
        snap = {}
        for c in d.get("candlesticks") or []:
            end = c.get("end_period_ts")
            yb = (c.get("yes_bid") or {}).get("close"); ya = (c.get("yes_ask") or {}).get("close")
            if yb is None and (c.get("yes_bid") or {}).get("close_dollars") is not None:
                yb = float(c["yes_bid"]["close_dollars"]) * 100; ya = float(c["yes_ask"]["close_dollars"]) * 100
            if end is None or yb is None or ya is None:
                continue
            for H in (24, 3):
                if end <= T - H * 3600:
                    snap[H] = (end, float(yb) / 100, float(ya) / 100)
        for H, (end, yb, ya) in snap.items():
            if not (0 < yb < ya < 1):
                continue
            rows.append({"event": e, "series": m["series"], "ticker": m["ticker"], "H": H, "yes_bid": yb, "yes_ask": ya, "y": int(m["result"] == "yes")})
    if time.time() - T0 > 3000:
        print("time cap", flush=True); break
print("candle calls", n_calls, "rows", len(rows), flush=True)
json.dump({"at": time.strftime("%Y-%m-%d %H:%M"), "series": [s.get("ticker") for s in ms], "rows": rows}, open(OUT, "w"))

# 3. table: by H and YES mid band; NO at 1 - yes_bid, YES at yes_ask; event-averaged returns
for H in (24, 3):
    print(f"\n== {H} h before the first close of the event ==")
    for lo, hi in ((0.03, 0.10), (0.10, 0.20), (0.20, 0.30), (0.30, 0.40), (0.40, 0.55), (0.55, 0.70), (0.70, 0.85), (0.85, 0.97)):
        R = [r for r in rows if r["H"] == H and lo <= (r["yes_bid"] + r["yes_ask"]) / 2 < hi]
        if len(R) < 10:
            continue
        g_no = collections.defaultdict(list); g_yes = collections.defaultdict(list)
        for r in R:
            na = 1 - r["yes_bid"]; ya = r["yes_ask"]
            g_no[r["event"]].append(((1 - r["y"]) - na - 0.07 * na * (1 - na)) / na)
            g_yes[r["event"]].append((r["y"] - ya - 0.07 * ya * (1 - ya)) / ya)
        en = [sum(v) / len(v) for v in g_no.values()]; ey = [sum(v) / len(v) for v in g_yes.values()]
        mid = sum((r["yes_bid"] + r["yes_ask"]) / 2 for r in R) / len(R); spr = sorted(r["yes_ask"] - r["yes_bid"] for r in R)[len(R) // 2]
        print(f"  YES mid {lo:.2f}-{hi:.2f}: markets {len(R):5} events {len(en):4}  mid {mid:.3f} said {sum(r['y'] for r in R) / len(R):.3f} "
              f"median spread {spr:.3f}  NO at ask {sum(en) / len(en):+.1%}/$ (events +: {sum(1 for x in en if x > 0)}/{len(en)})  YES at ask {sum(ey) / len(ey):+.1%}/$")
