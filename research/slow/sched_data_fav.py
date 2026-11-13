"""N5 (cycle 3, adjacent to slow favourites): favourite 0.90-0.98 in SCHEDULED-DATA bucket markets (CPI, GDP, payrolls,
unemployment, Fed rate, PCE, jobless claims) 1-7 days before the end, vs all other non-sports slow markets.
Why: a public nowcast/consensus pins these; holders sell early; but releases surprise (fat tails) -> cheap for a reason?
Daily last-trade prices (data/history), buy at p + 1c/2c + 0.07p(1-p) fee. Independent events = release (event title)."""
import json, re, collections, datetime as dt
D = "data/history"
mk = [json.loads(l) for l in open(f"{D}/markets.jsonl")]
SCHED = re.compile(r"\b(cpi|inflation|gdp|payroll|nonfarm|jobs report|unemployment|fed\b|fomc|interest rate|rate cut|bps|pce|jobless|ppi|retail sales)\b", re.I)
SPORT = re.compile(r"\b(vs\.?|nba|nfl|nhl|mlb|ufc|premier|league|cup|match|game|open|f1|tennis|win on)\b", re.I)
res = collections.defaultdict(lambda: collections.defaultdict(list))
for m in mk:
    try:
        P = json.load(open(f"{D}/prices/{m['id']}.json"))
    except OSError:
        continue
    q = m["question"] + " " + (m.get("event") or "")
    if SPORT.search(q):
        continue
    grp = "sched" if SCHED.search(q) else "other"
    end = dt.datetime.fromisoformat(m["end"]).replace(tzinfo=dt.timezone.utc).timestamp()
    for lo, hi in ((0.90, 0.95), (0.95, 0.98)):
        for dmin, dmax in ((1, 3), (3, 7)):
            for t, p in P:
                d = (end - t) / 86400
                if dmin <= d < dmax:
                    for side, pp, win in (("YES", p, m["yes_won"] == 1), ("NO", 1 - p, m["yes_won"] == 0)):
                        if lo <= pp < hi:
                            res[grp][(f"{lo}-{hi}", f"{dmin}-{dmax}d")].append((pp, win, m.get("event") or m["question"], m["end"][:7]))
                    break
for grp in ("sched", "other"):
    print("==", grp)
    for k, L in sorted(res[grp].items()):
        ev = collections.defaultdict(list)
        for x in L:
            ev[x[2]].append(x)
        out = []
        for c in (0.01, 0.02):
            cost = sum(min(.995, p + c) + 0.07 * p * (1 - p) for p, w, *_ in L)
            pnl = sum((1 if w else 0) - min(.995, p + c) - 0.07 * p * (1 - p) for p, w, *_ in L)
            out.append(f"+{int(c*100)}c {100*pnl/cost:+.1f}%")
        evloss = sum(1 for v in ev.values() if not all(w for _, w, *_ in v))
        print(k, "n", len(L), "events", len(ev), "events w/ a loss", evloss, "won", f"{sum(w for _, w, *_ in L)/len(L):.3f}", "avg p", f"{sum(p for p, *_ in L)/len(L):.3f}", *out)
