"""Maker version of the persistent lock: once the lock has held PERSIST s, post a BID one tick under the best ask on the
winning side (no fee, better price) and wait for a seller. Fill = a SELL print on that token at or below our bid
before the window ends (and before the lock breaks, when we would cancel). Compared with the taker version that
lifts the ask at the same moment. Read-only, from the websocket recordings + episodes.json (run lifetimes.py first).
"""
import glob, gzip, json, os
from collections import defaultdict
D = "data/fast"
PERSIST = float(os.environ.get("PERSIST", "2.0"))
E = json.load(open(f"{D}/episodes.json"))
M = json.load(open(f"{D}/results_meta.json"))
tok_of = {}
for o in (json.loads(l) for l in open(f"{D}/tokens.jsonl")):
    tok_of[(o["slug"], "Up")] = o["tokens"][0]; tok_of[(o["slug"], "Down")] = o["tokens"][1]
for s, md in M.items():
    if md.get("tokens"):
        tok_of[(s, "Up")] = md["tokens"][0]; tok_of[(s, "Down")] = md["tokens"][1]
# trades (ltp) and top-of-book per token
ltp = defaultdict(list); tops = defaultdict(list)
for f in sorted(glob.glob(f"{D}/bookws/*.jsonl*")):
    op = gzip.open if f.endswith(".gz") else open
    seen = set()   # archives appended more than once hold duplicate lines
    try:
        with op(f, "rt") as fh:
            while True:
                try:
                    line = fh.readline()
                except Exception:  # noqa: BLE001
                    break
                if not line:
                    break
                h = hash(line)
                if h in seen:
                    continue
                seen.add(h)
                try:
                    o = json.loads(line)
                except ValueError:
                    continue
                if o.get("t") == "ltp":
                    ltp[o["a"]].append((o["rx"], float(o["p"]), float(o["s"]), o.get("side")))
                elif o.get("t") in ("top", "book") and o.get("top") and o["top"][0] is not None:
                    tops[o["a"]].append((o["rx"], o["top"][0], o["top"][1] or 0.0, o["top"][2], o["top"][3] or 0.0))
    except Exception:  # noqa: BLE001
        pass
for a in ltp:
    ltp[a].sort(key=lambda x: x[0])
for a in tops:
    tops[a].sort(key=lambda x: x[0])
print("tokens with trades:", len(ltp), "episodes:", len(E))

# episodes.json lacks the open time; rebuild it from tops: find the first top record where ask == ask0 within the window end-60..end
res = {"taker": [0, 0, 0.0, 0.0], "maker": [0, 0, 0.0, 0.0], "maker_unfilled": 0}
rows = []
for e in E:
    if e["life"] < PERSIST:
        continue
    tok = tok_of.get((e["slug"], e["side"]))
    md = M.get(e["slug"])
    if not tok or not md or tok not in tops:
        continue
    end = md["start"] + md["window"]
    # locate the episode start: first top record in [end-60, end] with ask == ask0 (approximation)
    t0 = None
    for rx, ask, sz, bid, bsz in tops[tok]:
        if end - 60 <= rx <= end and abs(ask - e["ask0"]) < 1e-9:
            t0 = rx; break
    if t0 is None:
        continue
    t_act = t0 + PERSIST
    # state at t_act
    ask_at = bid_at = None
    for rx, ask, sz, bid, bsz in tops[tok]:
        if rx <= t_act:
            ask_at, bid_at = ask, bid
        else:
            break
    if ask_at is None or not (0.5 <= ask_at <= 0.97):
        continue
    won = 1.0 if e["won"] else 0.0
    # taker: lift the ask
    fee = 0.07 * ask_at * (1 - ask_at); stake = 20.0
    res["taker"][0] += 1; res["taker"][1] += e["won"]; res["taker"][2] += stake; res["taker"][3] += stake / ask_at * (won - ask_at - fee)
    # maker: bid one tick under the ask (tick 0.01), filled by a SELL print <= bid before the end (lock break ignored: conservative enough since fills are rare)
    my_bid = round(ask_at - 0.01, 2)
    fill = None
    for rx, p, s, side in ltp.get(tok, []):
        if t_act < rx <= end and side == "SELL" and p <= my_bid + 1e-9:
            fill = (rx, p, s); break
    if fill:
        res["maker"][0] += 1; res["maker"][1] += e["won"]; res["maker"][2] += stake; res["maker"][3] += stake / my_bid * (won - my_bid)
    else:
        res["maker_unfilled"] += 1
    rows.append((e["slug"], e["side"], ask_at, my_bid, bool(fill), e["won"], round(t_act - (end - 60), 1)))
for k in ("taker", "maker"):
    n, w, st, pnl = res[k]
    print(f"{k:6}: fills {n:4} won {w / n if n else 0:.3f} stake ${st:,.0f} pnl ${pnl:+,.1f} ({pnl / st if st else 0:+.1%})")
print("maker unfilled:", res["maker_unfilled"], "of", res["maker"][0] + res["maker_unfilled"], "episodes")
unf = [r for r in rows if not r[4]]; print("unfilled episodes' outcomes: won", sum(r[5] for r in unf), "of", len(unf))
fl = [r for r in rows if r[4]]; print("filled episodes' outcomes: won", sum(r[5] for r in fl), "of", len(fl))
