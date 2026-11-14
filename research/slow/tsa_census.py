"""N26 TSA checkpoint-passenger bucket markets census (cycle 11, 11-14). Outside the box: never touched.

Idea: 'Number of TSA passengers on <date>?' (130 closed events) resolve on tsa.gov's daily throughput, published the next
morning. Daily volume is very regular (same weekday a year earlier x a slowly moving year-over-year ratio, +-2-3%), so a
crowd that prices buckets by feel could be mis-calibrated, mainly on holiday / weather days.
Exposed to LESSONS 13 (the YoY ratio is public), 9 (needs a model better than the crowd's), 3 (thin bucket books -> +c and
fee), 5 (count EVENTS = days), 16 (no volume filter: every TSA event in data/events_closed.jsonl.gz is used).
Stage 1 (this script, price only): calibration by band + 'buy the favourite side 0.60-0.97' at p + c + fee 0.07p(1-p) at
end-72h / end-24h / end-6h, grouped by event. Also probes whether tsa.gov's throughput page is reachable from Actions
(needed for stage 2, the YoY model). Read-only, no orders. Writes data/research/tsa_report.json (cache tsa_prices.json).
"""
import json, time, gzip, datetime as dt, collections, os
import requests

CLOB = "https://clob.polymarket.com"
S = requests.Session()
CACHE = "data/research/tsa_prices.json"
OUT = "data/research/tsa_report.json"


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


def ts(s):
    if not s:
        return None
    s = s.replace(" ", "T")
    if s.endswith("+00"):
        s += ":00"
    s = s.replace("Z", "+00:00")
    try:
        return int(dt.datetime.fromisoformat(s).timestamp())
    except Exception:
        return None


def price_at(hist, t):
    best = None
    for h in hist:
        if h["t"] <= t:
            best = h["p"]
        else:
            break
    return best


def load_markets():
    out = []
    with gzip.open("data/events_closed.jsonl.gz", "rt") as f:
        for l in f:
            e = json.loads(l)
            ms = e.get("markets") or []
            title = (e.get("title") or "")
            if "tsa" not in title.lower() or "passenger" not in title.lower():
                continue
            for m in ms:
                try:
                    op = [float(x) for x in json.loads(m.get("outcomePrices") or "[]")]
                except Exception:
                    continue
                try:
                    tok = json.loads(m.get("clobTokenIds") or "[]")[0]
                except Exception:
                    tok = None
                if len(op) != 2 or max(op) < 0.99:
                    continue  # unresolved / 50-50
                end = ts(m.get("endDate") or e.get("endDate"))
                closed = ts(m.get("closedTime"))
                q = m.get("question") or ""
                out.append({"mid": str(m.get("id")), "ev": str(e["id"]), "title": title[:80], "q": q[:100], "tok": tok, "y": int(op[0] > 0.5),
                            "end": end, "closed": closed, "fees": bool(m.get("feesEnabled")),
                            "multi": len(ms) > 1})
    return out


def main():
    mk = load_markets()
    print(len(mk), "markets", len({m["ev"] for m in mk}), "events", flush=True)
    cache = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
    meta = cache.setdefault("_meta", {})
    for m in mk:  # the closed-events dump lacks token ids / dates for most markets: fill them from gamma
        if m["tok"] and m["end"]:
            continue
        g = meta.get(m["mid"])
        if g is None:
            g = get(f"https://gamma-api.polymarket.com/markets/{m['mid']}") or {}
            g = {k: g.get(k) for k in ("clobTokenIds", "endDate", "closedTime", "feesEnabled")}
            meta[m["mid"]] = g
            time.sleep(0.12)
        try:
            m["tok"] = m["tok"] or json.loads(g.get("clobTokenIds") or "[]")[0]
        except Exception:
            pass
        m["end"] = m["end"] or ts(g.get("endDate")); m["closed"] = m["closed"] or ts(g.get("closedTime"))
        m["fees"] = m["fees"] or bool(g.get("feesEnabled"))
    mk = [m for m in mk if m["tok"] and m["end"]]
    print(len(mk), "markets with token + end", flush=True)
    for i, m in enumerate(mk):
        if m["tok"] in cache:
            continue
        h = get(f"{CLOB}/prices-history", {"market": m["tok"], "startTs": m["end"] - 8 * 86400, "endTs": m["end"] + 3600, "fidelity": 60})
        cache[m["tok"]] = sorted(((h or {}).get("history") or []), key=lambda x: x["t"])
        time.sleep(0.12)
    json.dump(cache, open(CACHE, "w"))
    probe = {}
    for u in ("https://www.tsa.gov/travel/passenger-volumes", "https://www.tsa.gov/coronavirus/passenger-throughput"):
        try:
            r = S.get(u, timeout=20, headers={"User-Agent": "Mozilla/5.0 research"})
            probe[u] = {"status": r.status_code, "len": len(r.text), "has_table": "<table" in r.text}
        except Exception as ex:
            probe[u] = {"error": str(ex)[:120]}
    rep = {"tsa_probe": probe, "examples": sorted({m["title"] for m in mk})[-8:], "updated": time.strftime("%Y-%m-%d %H:%M", time.gmtime()), "markets": len(mk), "events": len({m["ev"] for m in mk}),
           "with_history": sum(bool(cache.get(m["tok"])) for m in mk)}
    for clock, hrs in (("end-72h", 72), ("end-24h", 24), ("end-6h", 6)):
        rows = []
        for m in mk:
            t = m["end"] - hrs * 3600
            if m["closed"] and m["closed"] <= t:
                continue
            p = price_at(cache.get(m["tok"]) or [], t)
            if p is None or not (0.01 <= p <= 0.99):
                continue
            rows.append(dict(m, p=p, month=time.strftime("%Y-%m", time.gmtime(m["end"]))))
        cal = {}
        for lo, hi in ((0.01, 0.1), (0.1, 0.3), (0.3, 0.5), (0.5, 0.7), (0.7, 0.9), (0.9, 0.99)):
            b = [r for r in rows if lo <= r["p"] < hi]
            if b:
                cal[f"{lo:.2f}-{hi:.2f}"] = {"n": len(b), "events": len({r['ev'] for r in b}),
                                             "avg_p": round(sum(r["p"] for r in b) / len(b), 3),
                                             "yes_rate": round(sum(r["y"] for r in b) / len(b), 3)}
        res = {"n_rows": len(rows), "events": len({r['ev'] for r in rows}), "calibration": cal}
        for lo, hi in ((0.60, 0.80), (0.80, 0.90), (0.90, 0.97), (0.60, 0.97)):
            for c in (0.01, 0.02, 0.03):
                stake = pnl = 0.0
                ev = collections.defaultdict(float); n = w = 0
                half = collections.defaultdict(float); hs = collections.defaultdict(float)
                for r in rows:
                    fp = max(r["p"], 1 - r["p"])
                    if not (lo <= fp < hi):
                        continue
                    side_yes = r["p"] >= 0.5
                    win = (r["y"] == 1) if side_yes else (r["y"] == 0)
                    px = min(fp + c, 0.995)
                    fee = 0.07 * px * (1 - px)
                    cost = px + fee
                    pl = (1 if win else 0) - cost
                    stake += cost; pnl += pl; n += 1; w += win
                    ev[r["ev"]] += pl
                    k = "2025H2+" if r["month"] >= "2025-07" else "before"
                    half[k] += pl; hs[k] += cost
                if n:
                    res[f"fav {lo:.2f}-{hi:.2f} +{int(c*100)}c"] = {
                        "n": n, "won": w, "ret_per_$": round(pnl / stake, 4), "events": len(ev),
                        "events_pos": sum(v > 0 for v in ev.values()),
                        "by_period": {k: round(half[k] / hs[k], 4) for k in half}}
        rep[clock] = res
    json.dump(rep, open(OUT, "w"), indent=1)
    print(json.dumps(rep, indent=1)[:6000])


if __name__ == "__main__":
    main()
