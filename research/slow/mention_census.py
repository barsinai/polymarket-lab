"""N8 mention-market census (cycle 5, 11-13): are 'What will X say?' word markets calibrated?

Why it could work: traders guess word odds from headlines; the per-word base rate (past transcripts, the speaker's habits) is
tedious to compute, so prices may be biased (e.g. YES on exotic words too rich, YES on habitual words too cheap).
Exposed to LESSONS 13 (base rates are priced), 3 (thin books: hourly last prices + c cost, fee stress), 5/6 (words on one call
are one bet: count CALLS/EVENTS and months), 11 (path questions - 'during the week' - resolve YES early; earnings calls are a
single event at the endDate, so they are clean; for the rest we report but trust less).
Input: data/research/mention_markets.json (from data/events_closed.jsonl.gz: market id, event, endDate, outcome, kind).
All earnings-call markets (504 / 42 calls) + up to 4 markets per other event (sampled, seed 7).
Clock: endDate - 24 h and endDate - 2 h (earnings endDate = call start). Read-only. Writes data/research/mention_report.json.
"""
import json, time, datetime as dt, collections, os, random
import requests

GAMMA = "https://gamma-api.polymarket.com"
CLOB = "https://clob.polymarket.com"
S = requests.Session()
IN = "data/research/mention_markets.json"
CACHE = "data/research/mention_prices.json"
OUT = "data/research/mention_report.json"


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


def score(rows, side, lo, hi, c, fee):
    n = won = 0; pnl = 0.0; stake = 0.0; ev = collections.defaultdict(float); mo = collections.defaultdict(float)
    for r in rows:
        p = r["p"] if side == "YES" else 1 - r["p"]
        if not (lo <= p < hi):
            continue
        cost = min(0.995, p + c) + (0.07 * p * (1 - p) if fee else 0)
        win = r["y"] == (1 if side == "YES" else 0)
        n += 1; won += win; stake += cost; pnl += (1 if win else 0) - cost
        ev[r["event"]] += (1 if win else 0) - cost; mo[r["end"][:7]] += (1 if win else 0) - cost
    return {"n": n, "won": won, "events": len(ev), "events_pos": sum(v > 0 for v in ev.values()), "avg_p": round(stake / n, 3) if n else None,
            "pct_per_$": round(100 * pnl / stake, 1) if stake else None, "months_pos": f"{sum(v >= 0 for v in mo.values())}/{len(mo)}",
            "by_month": {k: round(v, 2) for k, v in sorted(mo.items())}}


def main():
    allm = json.load(open(IN))
    rnd = random.Random(7); byev = collections.defaultdict(list)
    for m in allm:
        byev[m["event"]].append(m)
    mk = []
    for e, ms in byev.items():
        if ms[0]["kind"] == "earnings":
            mk += ms
        else:
            rnd.shuffle(ms); mk += ms[:4]
    print("markets", len(mk), collections.Counter(m["kind"] for m in mk), flush=True)
    cache = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
    t0 = time.time()
    for i, m in enumerate(mk):
        if m["mid"] in cache or not m.get("end"):
            continue
        if time.time() - t0 > 40 * 60:
            print("time budget hit at", i); break
        tok = m.get("tok")
        if not tok:
            g = get(f"{GAMMA}/markets/{m['mid']}")
            try:
                tok = json.loads((g or {}).get("clobTokenIds") or "[]")[0]
            except Exception:
                tok = None
        hist = []
        if tok:
            end = int(dt.datetime.fromisoformat(m["end"].replace("Z", "+00:00")).timestamp())
            h = get(f"{CLOB}/prices-history", {"market": tok, "startTs": end - 3 * 86400, "endTs": end + 3600, "fidelity": 60})
            hist = sorted(((h or {}).get("history") or []), key=lambda x: x["t"])
        cache[m["mid"]] = {"tok": tok, "hist": hist}
        if i % 100 == 0:
            print(i, len(mk), flush=True); json.dump(cache, open(CACHE, "w"))
        time.sleep(0.1)
    json.dump(cache, open(CACHE, "w"))

    rep = {"updated": time.strftime("%Y-%m-%d %H:%M", time.gmtime()), "markets": len(mk), "with_history": sum(1 for m in mk if (cache.get(m["mid"]) or {}).get("hist"))}
    for kind in ("earnings", "other_all"):
        sub = [m for m in mk if (m["kind"] == "earnings") == (kind == "earnings")]
        for clock, h_before in (("end-24h", 24), ("end-2h", 2)):
            rows = []
            for m in sub:
                hist = (cache.get(m["mid"]) or {}).get("hist") or []
                if not hist or not m.get("end"):
                    continue
                end = int(dt.datetime.fromisoformat(m["end"].replace("Z", "+00:00")).timestamp())
                p = price_at(hist, end - h_before * 3600)
                if p is None or not (0.02 <= p <= 0.98):
                    continue
                rows.append({"p": p, "y": m["y"], "event": m["event"], "end": m["end"]})
            if not rows:
                rep[f"{kind} {clock}"] = {"rows": 0}; continue
            cal = {}
            for lo, hi in ((0.02, 0.1), (0.1, 0.2), (0.2, 0.35), (0.35, 0.5), (0.5, 0.65), (0.65, 0.8), (0.8, 0.9), (0.9, 0.98)):
                b = [r for r in rows if lo <= r["p"] < hi]
                if b:
                    cal[f"{lo:.2f}-{hi:.2f}"] = {"n": len(b), "events": len({r['event'] for r in b}), "avg_p": round(sum(r["p"] for r in b) / len(b), 3),
                                                 "yes_rate": round(sum(r["y"] for r in b) / len(b), 3)}
            rules = {}
            for name, side, lo, hi in (("YES all", "YES", 0.02, 0.98), ("NO on YES 0.10-0.40", "NO", 0.60, 0.90), ("NO on YES 0.40-0.60", "NO", 0.40, 0.60),
                                       ("YES 0.60-0.90", "YES", 0.60, 0.90), ("YES 0.90-0.98", "YES", 0.90, 0.98), ("NO on YES 0.02-0.10", "NO", 0.90, 0.98)):
                for c in (0.01, 0.02):
                    rules[f"{name} +{int(c*100)}c"] = score(rows, side, lo, hi, c, False)
                rules[f"{name} +2c +fee"] = score(rows, side, lo, hi, 0.02, True)
            mid = sorted(r["end"] for r in rows)[len(rows) // 2]
            halves = {tag: {"NO on YES 0.10-0.40 +2c": score([r for r in rows if f(r)], "NO", 0.60, 0.90, 0.02, False),
                            "YES 0.60-0.90 +2c": score([r for r in rows if f(r)], "YES", 0.60, 0.90, 0.02, False)}
                      for tag, f in (("first", lambda r: r["end"] < mid), ("second", lambda r: r["end"] >= mid))}
            rep[f"{kind} {clock}"] = {"rows": len(rows), "events": len({r['event'] for r in rows}), "avg_p": round(sum(r["p"] for r in rows) / len(rows), 3),
                                     "yes_rate": round(sum(r["y"] for r in rows) / len(rows), 3),
                                     "brier": round(sum((r["p"] - r["y"]) ** 2 for r in rows) / len(rows), 4), "calibration": cal, "rules": rules, "halves": halves}
    json.dump(rep, open(OUT, "w"), indent=1)
    print(json.dumps(rep, indent=1)[:8000])


if __name__ == "__main__":
    main()
