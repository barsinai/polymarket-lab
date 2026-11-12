"""Nested windows (read-only): a 5-minute and a 15-minute window of the same coin that END at the same second resolve
on the same number F (the Chainlink 60-s TWAP at the end), each against its own price to beat (K5, K15, both known
exactly ~1.5 s after each window starts).

If K5 < K15:  Up5 + Down15 pays at least $1 in every case (F >= K15 -> Up5 wins; F < K15 -> Down15 wins), and $2 when
              K5 <= F < K15.
If K5 > K15:  Up15 + Down5, the same way.
So whenever ask1 + ask2 + taker fees < 1 the pair is riskless. This walks the websocket top-of-book recordings of both
windows from the moment both prices to beat are known to the end, and reports every such moment (with the size
available at the two asks), plus how often F landed between the two K (the $2 case) and the EV of the pair at the
ask when it is not riskless.

Env: BOOKWS_DIR, RESULTS_META, SINCE/UNTIL (archive hours), TOKENS (tokens.jsonl for windows missing tokens in meta).
"""
import glob, gzip, json, os
from collections import defaultdict

D = "data/fast"
BOOKWS = os.environ.get("BOOKWS_DIR") or f"{D}/bookws"
META = os.environ.get("RESULTS_META", f"{D}/results_meta.json")
SINCE, UNTIL = os.environ.get("SINCE", ""), os.environ.get("UNTIL", "9")
FEE = 0.07


def fee(p):
    return FEE * p * (1 - p)


M = json.load(open(META))
tok = {}
for s, md in M.items():
    if len(md.get("tokens") or []) == 2:
        tok[md["tokens"][0]] = (s, 0); tok[md["tokens"][1]] = (s, 1)
try:
    for line in open(os.environ.get("TOKENS", f"{D}/tokens.jsonl")):
        o = json.loads(line)
        if o.get("slug") in M and len(o.get("tokens") or []) == 2:
            tok.setdefault(o["tokens"][0], (o["slug"], 0)); tok.setdefault(o["tokens"][1], (o["slug"], 1))
except OSError:
    pass

# pairs: same coin, 5m window ending where a 15m window ends, both with result and price to beat
by_end = defaultdict(dict)
for s, md in M.items():
    if md.get("up") is None or md.get("ptb") is None or md.get("window") not in (300, 900):
        continue
    by_end[(s.split("-")[0], md["start"] + md["window"])][md["window"]] = s
pairs = {k: v for k, v in by_end.items() if 300 in v and 900 in v}
need = {}
for (coin, end), v in pairs.items():
    s5, s15 = v[300], v[900]
    for s in (s5, s15):
        need[s] = (coin, end)
print(f"pairs with results: {len(pairs)}")

# keep only book records of the paired windows from the 5m start (+2 s) to the end
ev = defaultdict(list)
files = [f for f in sorted(glob.glob(f"{BOOKWS}/*.jsonl*")) if SINCE <= os.path.basename(f)[:13] < UNTIL]
for f in files:
    op = gzip.open if f.endswith(".gz") else open
    try:
        with op(f, "rt") as fh:
            while True:
                try:
                    line = fh.readline()
                except Exception:  # noqa: BLE001
                    break
                if not line:
                    break
                i = line.find('"a":"')
                if i < 0:
                    continue
                a = line[i + 5:line.find('"', i + 5)]
                t = tok.get(a)
                if not t or t[0] not in need:
                    continue
                try:
                    o = json.loads(line)
                except ValueError:
                    continue
                if o.get("t") not in ("top", "book") or not o.get("top"):
                    continue
                coin, end = need[t[0]]
                if not (end - 300 - 30 <= o["rx"] <= end):
                    continue
                ev[(coin, end)].append((o["rx"], t[0], t[1], o["top"][0], o["top"][1] or 0.0))
    except Exception as e:  # noqa: BLE001
        print("skip", f, e)
print(f"files {len(files)}; pairs with book records {len(ev)}")

rows = []
for key, E in ev.items():
    coin, end = key
    s5, s15 = pairs[key][300], pairs[key][900]
    K5, K15 = M[s5]["ptb"], M[s15]["ptb"]
    F = M[s5].get("final") or M[s15].get("final")
    up5, up15 = M[s5]["up"], M[s15]["up"]
    # the riskless pair: (window, side index 0=Up 1=Down)
    legs = ((s5, 0), (s15, 1)) if K5 < K15 else ((s15, 0), (s5, 1))
    win1 = (M[legs[0][0]]["up"] is True)          # leg 1 is an Up token
    win2 = (M[legs[1][0]]["up"] is False)         # leg 2 is a Down token
    payoff = int(win1) + int(win2)
    gap_bp = abs(K5 - K15) / K15 * 1e4
    E.sort(key=lambda e: e[0])
    cur = {}
    best = None; riskless_s = 0.0; last_t = None; first_riskless = None; max_sz = 0.0
    start_ok = end - 300 + 2                        # both K known
    fixed = {}; marks = [240, 180, 120, 60, 30, 10]  # the pair's cost at fixed times before the end (no timing hindsight)
    for rx, s, side, ask, sz in E:
        while marks and rx > end - marks[0]:
            m = marks.pop(0)
            b1 = cur.get(legs[0]); b2 = cur.get(legs[1])
            if b1 and b2 and b1[0] is not None and b2[0] is not None and b1[0] < 1 and b2[0] < 1:
                fixed[m] = round(b1[0] + b2[0] + fee(b1[0]) + fee(b2[0]), 4)
        cur[(s, side)] = (ask, sz)
        if rx < start_ok:
            continue
        a1 = cur.get(legs[0]); a2 = cur.get(legs[1])
        if not a1 or not a2 or a1[0] is None or a2[0] is None or a1[0] >= 1 or a2[0] >= 1:
            continue
        cost = a1[0] + a2[0] + fee(a1[0]) + fee(a2[0])
        if best is None or cost < best[0]:
            best = (cost, round(end - rx, 1), a1[0], a2[0], min(a1[1], a2[1]))
        if cost < 1:
            if first_riskless is None:
                first_riskless = (round(end - rx, 1), a1[0], a2[0], min(a1[1], a2[1]), cost)
            max_sz = max(max_sz, min(a1[1], a2[1]))
    if best:
        rows.append({"coin": coin, "end": end, "gap_bp": round(gap_bp, 2), "payoff": payoff, "best_cost": round(best[0], 4),
                     "best_rem": best[1], "best_asks": best[2:4], "best_sz": best[4], "first_riskless": first_riskless,
                     "max_sz_riskless": round(max_sz, 1), "F": F, "K5": K5, "K15": K15, "fixed": fixed})

print(f"pairs evaluated: {len(rows)}")
if rows:
    n2 = sum(1 for r in rows if r["payoff"] == 2)
    print(f"F between the two prices to beat ($2 payoff): {n2} of {len(rows)} ({n2 / len(rows):.1%}); median |K5-K15| "
          f"{sorted(r['gap_bp'] for r in rows)[len(rows) // 2]:.1f} bp")
    rl = [r for r in rows if r["first_riskless"]]
    print(f"pairs that were ever riskless (asks + fees < $1): {len(rl)} of {len(rows)}")
    for r in sorted(rl, key=lambda r: r["best_cost"])[:30]:
        fr = r["first_riskless"]
        print(f"  {r['coin']:4} end {r['end']} gap {r['gap_bp']:5.1f} bp  best cost {r['best_cost']:.3f} at rem {r['best_rem']:5.1f}s "
              f"asks {r['best_asks']} size {r['best_sz']:.0f}  first riskless rem {fr[0]}s cost {fr[4]:.3f} size {fr[3]:.0f}  payoff {r['payoff']}")
    cs = sorted(r["best_cost"] for r in rows)
    print("best cost per pair percentiles: 10%", cs[len(cs) // 10], "median", cs[len(cs) // 2], "90%", cs[9 * len(cs) // 10])
    # EV of buying the pair at its best moment, riskless or not
    pnl = sum(r["payoff"] - r["best_cost"] for r in rows)
    print(f"buy the pair once at its cheapest moment (hindsight on timing!): mean payoff - cost {pnl / len(rows):+.4f} per pair")
    for lo, hi in ((0, 2), (2, 5), (5, 10), (10, 1e9)):
        R = [r for r in rows if lo <= r["gap_bp"] < hi]
        if R:
            print(f"  |K5-K15| {lo:>2}-{hi if hi < 1e9 else 'inf':>3} bp: n {len(R):4}  $2 rate {sum(r['payoff'] == 2 for r in R) / len(R):.1%}  "
                  f"median best cost {sorted(r['best_cost'] for r in R)[len(R) // 2]:.3f}  riskless {sum(1 for r in R if r['first_riskless'])}")
    print("pair bought at a FIXED time before the end (no hindsight): payoff - cost per pair")
    for m in (240, 180, 120, 60, 30, 10):
        R = [r for r in rows if m in r["fixed"]]
        if R:
            g = [r["payoff"] - r["fixed"][m] for r in R]
            print(f"  {m:3} s before end: n {len(R):4}  mean cost {sum(r['fixed'][m] for r in R) / len(R):.3f}  $2 rate "
                  f"{sum(r['payoff'] == 2 for r in R) / len(R):.1%}  mean payoff - cost {sum(g) / len(g):+.4f}  "
                  f"(cost < 1: {sum(1 for r in R if r['fixed'][m] < 1)})")
out = os.environ.get("OUT")
if out:
    json.dump(rows, open(out, "w"))
