"""N6 earnings-beat census (cycle 3, 11-13): are 'Will X beat quarterly earnings?' markets priced below the beat base rate?

Why it could work: ~73% of these markets resolved YES (470 closed, 2025-09..2026-03) and US companies beat consensus
~75% of the time (sandbagged guidance). If the crowd prices a typical name near 50-65%, YES is cheap on base rate alone.
Exposed to LESSONS 3 (history prices are trades/mids -> +c cost), 5/6 (names in one earnings season move together:
count seasons and months, replicate 2025 vs 2026), 9 (no model, just a base rate), 2 (cheap for a reason: weak names).

Input: data/research/earnings_markets.json (built from data/events_closed.jsonl.gz: market id, stated release date D,
outcome). For each market: YES token + feesEnabled from Gamma, hourly prices-history D-6..D+1.
Entry clock: D-1 20:00 UTC (before an after-close release on D-1? no: the stated date is D; BMO on D is ~10-12 UTC,
AMC on D ~20-21 UTC, so D-1 20:00 is before either) and D-3 20:00 as a check. Score: buy YES (or NO) at p + c,
c = 1/2/3c, and with the 0.07 p(1-p) fee as a stress. Read-only, no orders. Writes data/research/earnings_report.json.
"""
import json, time, datetime as dt, collections, os
import requests

GAMMA = "https://gamma-api.polymarket.com"
CLOB = "https://clob.polymarket.com"
S = requests.Session()
IN = "data/research/earnings_markets.json"
CACHE = "data/research/earnings_prices.json"
OUT = "data/research/earnings_report.json"


def get(url, params=None):
    for i in range(4):
        try:
            r = S.get(url, params=params, timeout=20)
            if r.status_code == 200:
                return r.json()
            if r.status_code in (400, 404):
                return None
        except Exception:
            pass
        time.sleep(1 + 2 * i)
    return None


def ts(day, add, hour):
    return int(dt.datetime.combine(day + dt.timedelta(days=add), dt.time(hour), tzinfo=dt.timezone.utc).timestamp())


def price_at(hist, t):
    best = None
    for h in hist:
        if h["t"] <= t:
            best = h["p"]
        else:
            break
    return best


def score(rows, side, lo, hi, c, fee):
    n = won = 0; pnl = 0.0; stake = 0.0; groups = collections.defaultdict(float)
    for r in rows:
        p = r["p"] if side == "YES" else 1 - r["p"]
        if not (lo <= p < hi):
            continue
        cost = min(0.995, p + c) + (0.07 * p * (1 - p) if fee else 0)
        win = r["y"] == (1 if side == "YES" else 0)
        n += 1; won += win; stake += cost; pnl += (1 if win else 0) - cost
        groups[r["date"][:7]] += (1 if win else 0) - cost
    return {"n": n, "won": won, "avg_p": round((stake / n) if n else 0, 3), "pct_per_$": round(100 * pnl / stake, 1) if stake else None,
            "months_pos": f"{sum(v >= 0 for v in groups.values())}/{len(groups)}", "by_month": {k: round(v, 2) for k, v in sorted(groups.items())}}


def main():
    mk = json.load(open(IN))
    cache = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
    for i, m in enumerate(mk):
        if m["mid"] in cache:
            continue
        g = get(f"{GAMMA}/markets/{m['mid']}")
        tok = None; fees = None
        if g:
            try:
                tok = json.loads(g.get("clobTokenIds") or "[]")[0]
            except Exception:
                tok = None
            fees = g.get("feesEnabled")
        hist = []
        if tok:
            d = dt.date.fromisoformat(m["date"])
            h = get(f"{CLOB}/prices-history", {"market": tok, "startTs": ts(d, -6, 0), "endTs": ts(d, 2, 0), "fidelity": 60})
            hist = sorted(((h or {}).get("history") or []), key=lambda x: x["t"])
        cache[m["mid"]] = {"tok": tok, "fees": fees, "hist": hist}
        if i % 50 == 0:
            print(i, len(mk), flush=True)
            json.dump(cache, open(CACHE, "w"))
        time.sleep(0.15)
    json.dump(cache, open(CACHE, "w"))

    rep = {"updated": time.strftime("%Y-%m-%d %H:%M", time.gmtime()), "markets": len(mk), "base_rate_yes": round(sum(m["y"] for m in mk) / len(mk), 3),
           "fees_enabled": collections.Counter(str(cache.get(m["mid"], {}).get("fees")) for m in mk)}
    for clock, add in (("D-1_20utc", -1), ("D-3_20utc", -3)):
        rows = []
        for m in mk:
            hist = cache.get(m["mid"], {}).get("hist") or []
            d = dt.date.fromisoformat(m["date"])
            p = price_at(hist, ts(d, add, 20))
            if p is None or not (0.02 <= p <= 0.98):
                continue
            rows.append({"p": p, "y": m["y"], "date": m["date"], "ticker": m["ticker"]})
        if not rows:
            rep[clock] = {"rows": 0}; continue
        cal = {}
        for lo in (0.0, 0.3, 0.5, 0.6, 0.7, 0.8, 0.9):
            hi = {0.0: 0.3, 0.3: 0.5, 0.5: 0.6, 0.6: 0.7, 0.7: 0.8, 0.8: 0.9, 0.9: 1.0}[lo]
            b = [r for r in rows if lo <= r["p"] < hi]
            if b:
                cal[f"{lo:.1f}-{hi:.1f}"] = {"n": len(b), "avg_p": round(sum(r["p"] for r in b) / len(b), 3), "yes_rate": round(sum(r["y"] for r in b) / len(b), 3)}
        brier = sum((r["p"] - r["y"]) ** 2 for r in rows) / len(rows)
        base = sum(r["y"] for r in rows) / len(rows)
        rules = {}
        for name, side, lo, hi in (("YES all", "YES", 0.02, 0.98), ("YES 0.40-0.80", "YES", 0.40, 0.80), ("YES 0.50-0.70", "YES", 0.50, 0.70),
                                   ("YES 0.80-0.95", "YES", 0.80, 0.95), ("NO 0.40-0.80", "NO", 0.40, 0.80), ("NO 0.80-0.97", "NO", 0.80, 0.97)):
            for c in (0.01, 0.02, 0.03):
                rules[f"{name} +{int(c*100)}c"] = score(rows, side, lo, hi, c, False)
            rules[f"{name} +2c +fee"] = score(rows, side, lo, hi, 0.02, True)
        halves = {}
        for tag, f in (("2025", lambda r: r["date"] < "2026"), ("2026", lambda r: r["date"] >= "2026")):
            sub = [r for r in rows if f(r)]
            halves[tag] = {"YES 0.40-0.80 +2c": score(sub, "YES", 0.40, 0.80, 0.02, False), "YES all +2c": score(sub, "YES", 0.02, 0.98, 0.02, False)}
        rep[clock] = {"rows": len(rows), "brier_market": round(brier, 4), "brier_base_rate": round(sum((base - r["y"]) ** 2 for r in rows) / len(rows), 4),
                      "avg_p": round(sum(r["p"] for r in rows) / len(rows), 3), "yes_rate": round(base, 3), "calibration": cal, "rules": rules, "halves": halves}
    json.dump(rep, open(OUT, "w"), indent=1)
    print(json.dumps({k: v for k, v in rep.items()}, indent=1)[:6000])


if __name__ == "__main__":
    main()
