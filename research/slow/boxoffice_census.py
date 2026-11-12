"""N2 box-office census (cycle 2, 11-12): do opening-weekend bracket markets process the box-office numbers slowly?

Input: data/research/boxoffice_markets.json (704 closed bracket markets, 143 films, 2024-02..2026-03, from events_closed).
For each market: YES token from gamma, hourly price history (CLOB prices-history, fidelity 60) for Wed..Mon of the
opening weekend. Clock points (UTC; the 'last price at or before'):
  p0 Thu 22:00 (before previews are known)   p1 Fri 18:00 (Thursday previews public since ~14-16 UTC)
  p2 Sat 18:00 (Friday gross incl. previews)  p3 Sun 18:00 (studio weekend estimates, resolution uses Monday actuals)
Tests (independent events = films; brackets of one film are one bet, LESSONS 6):
  A  Brier of p0..p3.
  B  Under-reaction: does the preview move p1-p0 continue to the outcome? Rule: |p1-p0| >= 5c -> buy that side at p1 + c.
  C  Slow favourite on Saturday / Sunday: buy the side priced 0.80-0.97 at p2 (or p3) at p + c.
History prices are trades/mids, not asks (LESSONS 3): every rule is scored with an added cost c = 1, 2, 3 c per share, and
the 0.07 p(1-p) fee as a stress (these markets show feesEnabled false). Read-only, no orders.
"""
import json, time, datetime as dt, statistics as st, collections, os, sys
import requests

GAMMA = "https://gamma-api.polymarket.com"
CLOB = "https://clob.polymarket.com"
S = requests.Session()
IN = "data/research/boxoffice_markets.json"
CACHE = "data/research/boxoffice_prices.json"
OUT = "data/research/boxoffice_report.json"


def get(url, params=None):
    for i in range(4):
        try:
            r = S.get(url, params=params, timeout=20)
            if r.status_code == 200:
                return r.json()
            if r.status_code in (404, 400):
                return None
        except Exception:
            pass
        time.sleep(1 + 2 * i)
    return None


def friday(end):
    d = dt.datetime.fromisoformat(end.replace("Z", "+00:00")).date()
    # opening weekend Fri-Sun; markets end the Monday (or Sunday/Tuesday) after
    back = (d.weekday() - 4) % 7 or 7
    return d - dt.timedelta(days=back)


def ts(day, add_days, hour):
    t = dt.datetime.combine(day + dt.timedelta(days=add_days), dt.time(hour), tzinfo=dt.timezone.utc)
    return int(t.timestamp())


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
    cache = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
    for i, m in enumerate(mk):
        if m["mid"] in cache:
            continue
        g = get(f"{GAMMA}/markets/{m['mid']}")
        tok = None
        if g:
            try:
                tok = json.loads(g.get("clobTokenIds") or "[]")[0]
            except Exception:
                tok = None
        hist = []
        if tok:
            fr = friday(m["end"])
            d = get(f"{CLOB}/prices-history", {"market": tok, "startTs": ts(fr, -2, 0), "endTs": ts(fr, 4, 0), "fidelity": 60})
            hist = sorted((d or {}).get("history") or [], key=lambda h: h["t"])
        cache[m["mid"]] = {"tok": tok, "hist": hist}
        if i % 50 == 0:
            print(i, m["film"], len(hist), flush=True)
            json.dump(cache, open(CACHE, "w"))
        time.sleep(0.05)
    json.dump(cache, open(CACHE, "w"))

    rows = []
    for m in mk:
        h = cache.get(m["mid"], {}).get("hist") or []
        if not h:
            continue
        fr = friday(m["end"])
        pts = [price_at(h, ts(fr, -1, 22)), price_at(h, ts(fr, 0, 18)), price_at(h, ts(fr, 1, 18)), price_at(h, ts(fr, 2, 18))]
        if None in pts:
            continue
        rows.append(dict(film=m["film"], wk=str(fr), y=m["y"], p=pts))
    films = sorted(set(r["film"] for r in rows))
    rep = {"at": dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M"), "markets": len(rows), "films": len(films),
           "weekends": len(set(r["wk"] for r in rows))}
    rep["brier"] = {k: round(st.mean((r["p"][j] - r["y"]) ** 2 for r in rows), 4) for j, k in enumerate(["thu22", "fri18", "sat18", "sun18"])}

    def score(picks, label):
        # picks: list of (film, side_price, won)
        out = {}
        for c in (0.0, 0.01, 0.02, 0.03):
            for fee in (False, True):
                byf = collections.defaultdict(float); stake = 0
                for f, p, w in picks:
                    e = min(p + c, 0.999)
                    fe = 0.07 * e * (1 - e) if fee else 0
                    sh = 10 / (e + fe)
                    byf[f] += (sh if w else 0) - 10; stake += 10
                tot = sum(byf.values())
                out[f"c{int(c*100)}{'_fee' if fee else ''}"] = {"trades": len(picks), "films": len(byf),
                    "pnl": round(tot, 1), "ret": round(tot / stake, 4) if stake else None,
                    "films_pos": sum(v > 0 for v in byf.values())}
        rep[label] = out

    # B under-reaction to previews
    B = []
    for r in rows:
        p0, p1 = r["p"][0], r["p"][1]
        if 0.03 < p1 < 0.97 and abs(p1 - p0) >= 0.05:
            if p1 > p0:
                B.append((r["film"], p1, r["y"] == 1))
            else:
                B.append((r["film"], 1 - p1, r["y"] == 0))
    score(B, "B_preview_momentum")
    mv = [(r["p"][1] - r["p"][0], r["y"] - r["p"][1]) for r in rows if 0.03 < r["p"][1] < 0.97]
    if len(mv) > 3:
        rep["B_corr_move_vs_residual"] = round(st.correlation([a for a, b in mv], [b for a, b in mv]), 3)
    # C slow favourite Saturday / Sunday
    for j, lab in ((2, "C_sat18_fav"), (3, "C_sun18_fav")):
        C = []
        for r in rows:
            p = r["p"][j]
            if 0.80 <= p <= 0.97:
                C.append((r["film"], p, r["y"] == 1))
            elif 0.80 <= 1 - p <= 0.97:
                C.append((r["film"], 1 - p, r["y"] == 0))
        score(C, lab)
        rep[lab]["win_rate"] = round(sum(w for _, _, w in C) / len(C), 3) if C else None
        rep[lab]["avg_price"] = round(st.mean(p for _, p, _ in C), 3) if C else None
    # calibration of fri18 by band
    cal = collections.defaultdict(list)
    for r in rows:
        cal[min(int(r["p"][1] * 10), 9)].append(r["y"])
    rep["fri18_calibration"] = {f"{b/10:.1f}": {"n": len(v), "yes": round(st.mean(v), 3)} for b, v in sorted(cal.items())}
    json.dump(rep, open(OUT, "w"), indent=1)
    print(json.dumps(rep, indent=1))


if __name__ == "__main__":
    main()
