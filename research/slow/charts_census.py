"""N10 ranking-chart markets census (cycle 4, 11-13): Netflix top 10, Apple App Store / Play Store #1, Spotify #1 song,
Billboard Hot 100 #1 - weekly/daily multi-outcome (negRisk) events that resolve on a public chart.

Why the crowd could be wrong: the resolution chart is readable (or nowcastable) before the event ends - Spotify and
App Store charts update daily/hourly, FlixPatrol has daily Netflix ranks before Netflix's Tuesday top 10, Hot 100 tracking
week ends Thursday with mid-week projections. If few traders read those, the leader near the end should be underpriced
(a favourite at 0.80 that is really 0.95). Exposed to LESSONS 2 (cheap for a reason), 3 (thin books: +c and fee),
5 (count events, not markets; kinds and months), 13 (if the chart is public, it may already be in the price).

Cheapest decisive test (price only, no chart data yet): calibration and favourite yield at end-24h / end-6h / end-2h
(event endDate), buying the event favourite at p + c (c = 1/2/3c, +fee stress). Only if the favourite is underpriced is it
worth fetching the chart sources. Input data/research/charts_markets.json (from data/events_closed.jsonl.gz, top 6
markets by volume per event). Read-only, no orders. Writes data/research/charts_report.json.
"""
import json, time, datetime as dt, collections, os
import requests

GAMMA = "https://gamma-api.polymarket.com"
CLOB = "https://clob.polymarket.com"
S = requests.Session()
IN = "data/research/charts_markets.json"
CACHE = "data/research/charts_prices.json"
OUT = "data/research/charts_report.json"
TOP = 6


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


def price_at(hist, t):
    best = None
    for h in hist:
        if h["t"] <= t:
            best = h["p"]
        else:
            break
    return best


def main():
    mk = json.load(open(IN))
    by_ev = collections.defaultdict(list)
    for m in mk:
        by_ev[m["event"]].append(m)
    sel = []
    for ev, ms in by_ev.items():
        sel += sorted(ms, key=lambda m: -m["vol"])[:TOP]
    cache = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
    for i, m in enumerate(sel):
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
            end = int(dt.datetime.fromisoformat(m["end"].replace("Z", "+00:00")).timestamp())
            h = get(f"{CLOB}/prices-history", {"market": tok, "startTs": end - 4 * 86400, "endTs": end + 86400, "fidelity": 60})
            hist = sorted(((h or {}).get("history") or []), key=lambda x: x["t"])
        cache[m["mid"]] = {"tok": tok, "fees": fees, "hist": hist}
        if i % 100 == 0:
            print(i, len(sel), flush=True)
            json.dump(cache, open(CACHE, "w"))
        time.sleep(0.12)
    json.dump(cache, open(CACHE, "w"))

    rep = {"updated": time.strftime("%Y-%m-%d %H:%M", time.gmtime()), "events": len(by_ev), "markets_fetched": len(sel),
           "with_history": sum(bool(cache.get(m["mid"], {}).get("hist")) for m in sel),
           "fees_enabled": dict(collections.Counter(str(cache.get(m["mid"], {}).get("fees")) for m in sel))}
    for clock, hrs in (("end-24h", 24), ("end-6h", 6), ("end-2h", 2)):
        rows = []; favs = []
        for ev, ms in by_ev.items():
            pts = []
            for m in sorted(ms, key=lambda m: -m["vol"])[:TOP]:
                hist = cache.get(m["mid"], {}).get("hist") or []
                end = int(dt.datetime.fromisoformat(m["end"].replace("Z", "+00:00")).timestamp())
                t = end - hrs * 3600
                if m.get("closed"):
                    try:
                        ct = dt.datetime.fromisoformat(m["closed"].replace(" ", "T").replace("+00", "+00:00")).timestamp()
                        if ct <= t:
                            continue  # already resolved at entry time
                    except Exception:
                        pass
                p = price_at(hist, t)
                if p is None:
                    continue
                pts.append({"p": p, "y": m["y"], "kind": m["kind"], "month": m["end"][:7], "ev": ev})
            rows += [r for r in pts if 0.01 <= r["p"] <= 0.99]
            if pts:
                f = max(pts, key=lambda r: r["p"])
                favs.append(f)
        cal = {}
        for lo, hi in ((0.0, 0.1), (0.1, 0.3), (0.3, 0.5), (0.5, 0.7), (0.7, 0.85), (0.85, 0.95), (0.95, 1.0)):
            b = [r for r in rows if lo <= r["p"] < hi]
            if b:
                cal[f"{lo:.2f}-{hi:.2f}"] = {"n": len(b), "events": len({r['ev'] for r in b}), "avg_p": round(sum(r["p"] for r in b) / len(b), 3),
                                             "yes_rate": round(sum(r["y"] for r in b) / len(b), 3)}

        def fav_rule(lo, hi, c, fee, sub=None):
            fs = [f for f in favs if lo <= f["p"] < hi and (sub is None or sub(f))]
            if not fs:
                return {"n": 0}
            stake = pnl = 0.0; by = collections.defaultdict(float)
            for f in fs:
                cost = min(0.995, f["p"] + c) + (0.07 * f["p"] * (1 - f["p"]) if fee else 0)
                stake += cost; pnl += f["y"] - cost; by[f["kind"]] += f["y"] - cost
            return {"n": len(fs), "won": sum(f["y"] for f in fs), "avg_p": round(sum(f["p"] for f in fs) / len(fs), 3),
                    "pct_per_$": round(100 * pnl / stake, 1), "by_kind_$": {k: round(v, 2) for k, v in by.items()}}
        rules = {}
        for lo, hi in ((0.5, 0.97), (0.6, 0.85), (0.85, 0.97)):
            for c in (0.01, 0.02, 0.03):
                rules[f"fav {lo}-{hi} +{int(c*100)}c"] = fav_rule(lo, hi, c, False)
            rules[f"fav {lo}-{hi} +2c +fee"] = fav_rule(lo, hi, 0.02, True)
        for k in ("netflix", "app store", "spotify", "billboard"):
            rules[f"fav 0.5-0.97 +2c {k}"] = fav_rule(0.5, 0.97, 0.02, False, lambda f, k=k: f["kind"] == k)
        for tag, sub in (("<=2025-12", lambda f: f["month"] <= "2025-12"), (">=2026-01", lambda f: f["month"] >= "2026-01")):
            rules[f"fav 0.5-0.97 +2c {tag}"] = fav_rule(0.5, 0.97, 0.02, False, sub)
        brier = sum((r["p"] - r["y"]) ** 2 for r in rows) / len(rows) if rows else None
        rep[clock] = {"rows": len(rows), "events_with_fav": len(favs), "fav_won": sum(f["y"] for f in favs),
                      "brier": round(brier, 4) if brier else None, "calibration": cal, "rules": rules}
    json.dump(rep, open(OUT, "w"), indent=1)
    print(json.dumps(rep, indent=1)[:8000])


if __name__ == "__main__":
    main()
