"""Research-track forecast journal (paper only).

  add:     python research/slow/forecast_log.py add <slug> <my_p> "<rationale>" "<source1>|<source2>"
           looks the market up in data/slow/candidates.json, records market price, my probability, the implied paper
           position (buy YES if my_p > market + EDGE, buy NO if my_p < market - EDGE, else none) at $STAKE, appends to
           data/research/forecasts.jsonl. Re-adding a slug on a later day records a new forecast (the latest counts).
  score:   python research/slow/forecast_log.py score     (run on the generic runner: needs Gamma for resolutions)
           settles resolved markets, prints Brier (mine vs market), hit rate, paper P&L; writes data/research/scoreboard.json
Fee: Polymarket taker fee 0.07*p*(1-p) per share on the price paid (same model as the fast bot)."""
import json, os, sys, time, datetime as dt
D = "data/research"; os.makedirs(D, exist_ok=True); LOG = f"{D}/forecasts.jsonl"
EDGE = float(os.environ.get("EDGE", "0.08")); STAKE = float(os.environ.get("STAKE", "20"))


def load():
    try:
        return [json.loads(l) for l in open(LOG)]
    except OSError:
        return []


if sys.argv[1:2] == ["add"]:
    slug, my_p, rationale = sys.argv[2], float(sys.argv[3]), sys.argv[4]
    sources = [s for s in (sys.argv[5] if len(sys.argv) > 5 else "").split("|") if s]
    C = {c["slug"]: c for c in json.load(open("data/slow/candidates.json"))}
    c = C[slug]; mkt = c["yes"]
    side = "YES" if my_p > mkt + EDGE else "NO" if my_p < mkt - EDGE else None
    kind = "conviction" if side else None
    if side is None and my_p <= 0.04 and mkt - my_p >= 0.02:
        side, kind = "NO", "longshot"            # the documented bias: dead longshots priced at 3-7%
    elif side is None and my_p >= 0.96 and my_p - mkt >= 0.02:
        side, kind = "YES", "longshot"
    price = mkt if side == "YES" else 1 - mkt if side == "NO" else None
    rec = {"date": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M"), "slug": slug, "id": c["id"], "question": c["question"], "end": c["end"],
           "market_p": mkt, "my_p": my_p, "side": side, "price": price, "stake": STAKE if side else 0, "shares": round(STAKE / price, 2) if side else 0,
           "kind": kind, "rationale": rationale, "sources": sources, "tags": c.get("tags"), "resolved": None}
    with open(LOG, "a") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"logged {slug}: market {mkt:.2f} mine {my_p:.2f} -> {side or 'no position'}" + (f" at {price:.2f} x {rec['shares']}" if side else ""))

elif sys.argv[1:2] == ["score"]:
    import requests
    recs = load(); latest = {}
    for r in recs:
        latest[r["slug"]] = r                      # the last forecast per market counts
    S = requests.Session(); out = []
    for slug, r in latest.items():
        ev = None
        for i in range(3):
            try:
                ev = S.get("https://gamma-api.polymarket.com/events", params={"slug": slug}, timeout=20).json(); break
            except Exception:  # noqa: BLE001
                time.sleep(2)
        m = None
        if ev:
            for e in ev:
                for mm in e.get("markets", []):
                    if mm.get("slug") == slug or str(mm.get("id")) == str(r["id"]):
                        m = mm
        if not m:
            m = (S.get("https://gamma-api.polymarket.com/markets", params={"slug": slug}, timeout=20).json() or [None])[0]
        if not m:
            continue
        prices = [float(x) for x in json.loads(m.get("outcomePrices") or "[0,0]")]
        resolved = bool(m.get("closed")) and max(prices) >= 0.99
        y = int(prices[0] > prices[1]) if resolved else None
        r = dict(r, now_p=prices[0], resolved=resolved, y=y)
        if resolved and r["side"]:
            win = (y == 1) == (r["side"] == "YES"); fee = 0.07 * r["price"] * (1 - r["price"])
            r["pnl"] = round(r["shares"] * ((1 if win else 0) - r["price"] - fee), 2)
        out.append(r)
    done = [r for r in out if r["resolved"]]
    bs = lambda p, y: (p - y) ** 2
    sb = {"forecasts": len(out), "resolved": len(done),
          "brier_mine": round(sum(bs(r["my_p"], r["y"]) for r in done) / len(done), 4) if done else None,
          "brier_market": round(sum(bs(r["market_p"], r["y"]) for r in done) / len(done), 4) if done else None,
          "positions": sum(1 for r in out if r["side"]), "pnl": round(sum(r.get("pnl", 0) for r in done), 2),
          "staked_resolved": round(sum(r["stake"] for r in done if r["side"]), 2), "updated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M"),
          "rows": [{k: r.get(k) for k in ("slug", "date", "market_p", "my_p", "side", "price", "now_p", "resolved", "y", "pnl")} for r in out]}
    json.dump(sb, open(f"{D}/scoreboard.json", "w"), indent=1)
    print(json.dumps({k: v for k, v in sb.items() if k != "rows"}))
    for r in out:
        print(f"  {r['slug'][:60]:60} mkt {r['market_p']:.2f} mine {r['my_p']:.2f} {str(r['side'] or '-'):4} now {r['now_p']:.2f} {'RESOLVED ' + str(r['y']) if r['resolved'] else ''} {r.get('pnl', '')}")
else:
    for r in load():
        print(f"{r['date']} {r['slug'][:55]:55} mkt {r['market_p']:.2f} mine {r['my_p']:.2f} {str(r['side'] or '-'):4}")
