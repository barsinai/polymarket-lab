"""N17 'What price will X hit?' census (cycle 7, 11-13): are touch / barrier ladders calibrated?

Why it could be wrong: a touch ('hit $X any time in the week/month') is roughly TWICE as likely as finishing beyond X
(reflection principle), and retail tends to price touches like closes. Our young NO paper bought NO on 36 'hit (HIGH/LOW)
Week of November 9' stock markets at ~0.60 and lost -$168 (marked): touches came more often than priced. Is that general
(touch YES cheap) or one sell-off week (LESSONS 6)? Exposed to LESSONS 3 (thin ladders: +c and fee stress), 5/6 (strikes of
one event and all events of one week are one bet: count WEEKS), 11 (early YES: entry skips markets already closed at entry),
13 (if it is priced, nothing).
Data: Gamma closed events whose title matches 'hit' (crypto/stocks/commodities, weekly + monthly ladders), CLOB hourly
prices. Clocks: start + 24 h and 50% of the event's life. Read-only, no orders. Writes data/research/hit_report.json.
"""
import json, time, datetime as dt, collections, os, re
import requests

GAMMA = "https://gamma-api.polymarket.com"
CLOB = "https://clob.polymarket.com"
S = requests.Session()
CACHE = "data/research/hit_prices.json"
EVS = "data/research/hit_events.json"
OUT = "data/research/hit_report.json"
TITLE = re.compile(r"\bhit\b", re.I)
CRYPTO = re.compile(r"bitcoin|ethereum|solana|xrp|\bbtc\b|\beth\b|dogecoin|hyperliquid|bnb", re.I)
BUDGET = 42 * 60


def get(url, params=None):
    for i in range(4):
        try:
            r = S.get(url, params=params, timeout=30)
            if r.status_code == 200:
                return r.json()
            if r.status_code in (400, 404):
                return None
        except Exception:
            pass
        time.sleep(1 + 2 * i)
    return None


def ts(s):
    return int(dt.datetime.fromisoformat(s.replace("Z", "+00:00").replace(" ", "T")).timestamp())


def discover():
    if os.path.exists(EVS):
        return json.load(open(EVS))
    out = []; off = 0
    while off < 60000:
        page = get(f"{GAMMA}/events", {"closed": "true", "limit": 200, "offset": off, "order": "endDate", "ascending": "false",
                                      "end_date_min": "2025-06-01T00:00:00Z", "end_date_max": "2026-11-13T00:00:00Z"})
        if not page:
            break
        for e in page:
            t = e.get("title") or ""
            if not TITLE.search(t) or "spotify" in t.lower():
                continue
            ms = []
            for m in e.get("markets") or []:
                try:
                    op = json.loads(m.get("outcomePrices") or "[]"); tok = json.loads(m.get("clobTokenIds") or "[]")[0]
                except Exception:
                    continue
                if len(op) != 2 or 0.01 < float(op[0]) < 0.99:
                    continue
                ms.append({"mid": m["id"], "q": m.get("question"), "tok": tok, "y": int(float(op[0]) >= 0.99),
                           "closed": m.get("closedTime"), "fees": m.get("feesEnabled")})
            if ms and e.get("startDate") and e.get("endDate"):
                period = "week" if re.search(r"week|\d+\s*-\s*\d+", t, re.I) else ("month" if re.search(
                    r"in (january|february|march|april|may|june|july|august|september|october|november|december)", t, re.I) else "other")
                out.append({"event": e.get("slug"), "title": t, "start": e["startDate"], "end": e["endDate"],
                            "kind": "crypto" if CRYPTO.search(t) else "stock/cmdty", "period": period, "markets": ms})
        off += 200
        if len(page) < 200:
            break
        if off % 4000 == 0:
            print("scan", off, "hit events", len(out), flush=True)
    json.dump(out, open(EVS, "w"))
    return out


def price_at(hist, t):
    best = None
    for h in hist:
        if h["t"] <= t:
            best = h["p"]
        else:
            break
    return best


def score(rows, side, lo, hi, c, fee, sub=None):
    n = won = 0; pnl = stake = 0.0; wk = collections.defaultdict(float); ev = collections.defaultdict(float)
    for r in rows:
        if sub and not sub(r):
            continue
        p = r["p"] if side == "YES" else 1 - r["p"]
        if not (lo <= p < hi):
            continue
        cost = min(0.995, p + c) + (0.07 * p * (1 - p) if fee else 0)
        win = r["y"] == (1 if side == "YES" else 0)
        n += 1; won += win; stake += cost; pnl += win - cost
        wk[r["week"]] += win - cost; ev[r["event"]] += win - cost
    if not n:
        return {"n": 0}
    return {"n": n, "won": won, "events": len(ev), "weeks": len(wk), "weeks_pos": sum(v > 0 for v in wk.values()),
            "avg_cost": round(stake / n, 3), "pct_per_$": round(100 * pnl / stake, 1)}


def main():
    t0 = time.time()
    evs = discover()
    print("hit events", len(evs), collections.Counter((e["kind"], e["period"]) for e in evs), flush=True)
    cache = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
    # stocks/commodities first (the young paper question), then crypto
    order = sorted(evs, key=lambda e: (e["kind"] == "crypto", e["end"]), reverse=False)
    k = 0
    for e in order:
        s, en = ts(e["start"]), ts(e["end"])
        for m in e["markets"]:
            if m["mid"] in cache:
                continue
            if time.time() - t0 > BUDGET:
                break
            h = get(f"{CLOB}/prices-history", {"market": m["tok"], "startTs": s, "endTs": en, "fidelity": 60})
            cache[m["mid"]] = sorted(((h or {}).get("history") or []), key=lambda x: x["t"])
            k += 1
            if k % 200 == 0:
                print("hist", k, round(time.time() - t0), flush=True)
                json.dump(cache, open(CACHE, "w"))
            time.sleep(0.1)
    json.dump(cache, open(CACHE, "w"))

    rep = {"updated": time.strftime("%Y-%m-%d %H:%M", time.gmtime()), "events": len(evs),
           "by_kind_period": {f"{a}/{b}": n for (a, b), n in collections.Counter((e["kind"], e["period"]) for e in evs).items()},
           "markets_with_hist": sum(bool(v) for v in cache.values())}
    for clock in ("start+24h", "mid-life"):
        rows = []
        for e in evs:
            s, en = ts(e["start"]), ts(e["end"])
            if en - s < 2 * 86400:
                continue
            t = s + 86400 if clock == "start+24h" else (s + en) // 2
            for m in e["markets"]:
                hist = cache.get(m["mid"])
                if not hist:
                    continue
                if m.get("closed"):
                    try:
                        if ts(m["closed"]) <= t:
                            continue
                    except Exception:
                        pass
                p = price_at(hist, t)
                if p is None or not (0.03 <= p <= 0.97):
                    continue
                q = m["q"] or ""
                d = "LOW" if re.search(r"\(LOW\)|dip|below|fall", q, re.I) else "HIGH"
                rows.append({"p": p, "y": m["y"], "event": e["event"], "kind": e["kind"], "period": e["period"], "dir": d,
                             "week": dt.datetime.utcfromtimestamp(en).strftime("%G-W%V"), "half": "2025" if e["end"] < "2026" else "2026"})
        cal = {}
        for lo, hi in ((0.03, 0.1), (0.1, 0.2), (0.2, 0.35), (0.35, 0.5), (0.5, 0.65), (0.65, 0.8), (0.8, 0.97)):
            for kind in ("stock/cmdty", "crypto"):
                b = [r for r in rows if lo <= r["p"] < hi and r["kind"] == kind]
                if b:
                    cal[f"{kind} {lo:.2f}-{hi:.2f}"] = {"n": len(b), "events": len({r['event'] for r in b}),
                                                        "weeks": len({r['week'] for r in b}),
                                                        "avg_p": round(sum(r["p"] for r in b) / len(b), 3),
                                                        "yes_rate": round(sum(r["y"] for r in b) / len(b), 3)}
        rules = {}
        for kind in ("stock/cmdty", "crypto"):
            K = lambda r, kind=kind: r["kind"] == kind
            for side, lo, hi in (("YES", 0.1, 0.5), ("YES", 0.03, 0.2), ("YES", 0.2, 0.5), ("NO", 0.5, 0.7), ("NO", 0.8, 0.97)):
                for c in (0.01, 0.02, 0.05):
                    rules[f"{kind} {side} {lo}-{hi} +{int(c*100)}c +fee"] = score(rows, side, lo, hi, c, True, K)
            for tag, sub in (("week", lambda r: r["period"] == "week"), ("month", lambda r: r["period"] == "month"),
                             ("HIGH", lambda r: r["dir"] == "HIGH"), ("LOW", lambda r: r["dir"] == "LOW"),
                             ("2025", lambda r: r["half"] == "2025"), ("2026", lambda r: r["half"] == "2026")):
                rules[f"{kind} YES 0.1-0.5 +2c +fee {tag}"] = score(rows, "YES", 0.1, 0.5, 0.02, True, lambda r, sub=sub, K=K: K(r) and sub(r))
        brier = {kind: round(sum((r["p"] - r["y"]) ** 2 for r in rows if r["kind"] == kind) / max(1, sum(r["kind"] == kind for r in rows)), 4)
                 for kind in ("stock/cmdty", "crypto")}
        rep[clock] = {"rows": len(rows), "brier": brier, "calibration": cal, "rules": rules}
    json.dump(rep, open(OUT, "w"), indent=1)
    print(json.dumps(rep, indent=1)[:9000])


if __name__ == "__main__":
    main()
