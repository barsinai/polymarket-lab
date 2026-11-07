"""Replay a two-sided maker ("set-seller") in the Up/Down markets against the real trade tape. Read-only.

Idea (copied from a wallet that made +4%/$ over 231 windows without ever buying): mint N complete sets
(N Up + N Down for $N), post an ASK on each side a little above that side's last traded price, keep the two
asks summing to > $1, re-post as prices move. Makers pay no fee. Whatever is unsold resolves ($1 for the
winning side, $0 for the loser; leftover complete sets merge back for free).

Fill rule (conservative): a resting ask at A on side S is lifted only by a later BUY print of S at a price
STRICTLY above A (the taker would have hit our better price first); partial by the print's size.
Quotes are refreshed from the print tape, i.e. our price information is as stale as the public tape.
"""
import gzip, json, math, os, sys
from collections import defaultdict

D = "data/fast"
SPREAD = float(os.environ.get("SPREAD", "0.03"))     # ask = last price + SPREAD (per side)
N_SETS = float(os.environ.get("N_SETS", "20"))        # sets minted per window ($)
STOP_S = int(os.environ.get("STOP_S", "60"))          # stop quoting with this many seconds left
MIN_SUM = float(os.environ.get("MIN_SUM", "1.04"))    # the two asks must sum to at least this
WINDOW = int(os.environ.get("WINDOW", "300"))
M = json.load(open(f"{D}/results_meta.json"))
tape = defaultdict(list)
with gzip.open(f"{D}/tape.jsonl.gz", "rt") as fh:
    for line in fh:
        t = json.loads(line)
        if t["slug"] in M and M[t["slug"]]["window"] == WINDOW and M[t["slug"]]["up"] is not None:
            tape[t["slug"]].append(t)


def tick_up(x):
    return math.ceil(x * 100 - 1e-9) / 100


def run(slug, prints, spread=SPREAD, n_sets=N_SETS, stop_s=STOP_S, min_sum=MIN_SUM):
    md = M[slug]; st, end = md["start"], md["start"] + md["window"]
    prints = sorted(prints, key=lambda t: t["ts"])
    inv = {"Up": n_sets, "Down": n_sets}
    last = {"Up": 0.5, "Down": 0.5}
    ask = {"Up": tick_up(0.5 + spread), "Down": tick_up(0.5 + spread)}
    cash = -n_sets; fills = []
    for t in prints:
        if t["ts"] < st:
            continue
        rem = end - t["ts"]
        s = t["o"]
        if t["side"] == "BUY" and rem > stop_s and inv[s] > 0 and t["p"] > ask[s] + 1e-9:
            q = min(t["s"], inv[s]); inv[s] -= q; cash += q * ask[s]; fills.append((rem, s, ask[s], q))
        # update our view of prices from the public print and re-quote
        last[s] = t["p"]; last["Up" if s == "Down" else "Down"] = min(last["Up" if s == "Down" else "Down"], 1 - t["p"] + spread)
        for side in ("Up", "Down"):
            ask[side] = tick_up(last[side] + spread)
        if ask["Up"] + ask["Down"] < min_sum:
            lo = "Up" if ask["Up"] < ask["Down"] else "Down"
            ask[lo] = tick_up(min_sum - ask["Up" if lo == "Down" else "Down"])
    win = "Up" if md["up"] else "Down"
    merged = min(inv["Up"], inv["Down"])
    cash += merged + (inv[win] - merged)
    return cash, fills, inv


if __name__ == "__main__":
    tot = 0.0; n = 0; nf = 0; per = []; by_rem = defaultdict(lambda: [0.0, 0.0]); sold_sum = 0.0
    for slug, prints in tape.items():
        pnl, fills, inv = run(slug, prints)
        tot += pnl; n += 1; nf += len(fills); per.append(pnl)
        win = "Up" if M[slug]["up"] else "Down"
        for rem, s, a, q in fills:
            b = "<=60" if rem <= 60 else "<=120" if rem <= 120 else "<=180" if rem <= 180 else ">180"
            by_rem[b][0] += q * a; by_rem[b][1] += q * (a - (1.0 if s == win else 0.0))
            sold_sum += q * a
    per.sort()
    print(f"windows {n} fills {nf} sold ${sold_sum:,.0f}  P&L ${tot:,.1f} = {tot / (n * N_SETS):+.3%} of capital per window; "
          f"median window {per[len(per) // 2]:+.2f}, worst {per[0]:+.2f}, best {per[-1]:+.2f}, positive windows {sum(p > 0 for p in per) / n:.0%}")
    print("  sales by time left (sold $, edge vs outcome per $):", {k: (round(v[0]), f"{v[1] / v[0]:+.3f}") for k, v in sorted(by_rem.items()) if v[0]})
    print("\nparameter sweep (P&L % of capital per window / positive windows):")
    for spread in (0.02, 0.03, 0.05, 0.08):
        for stop_s in (30, 60, 120):
            for min_sum in (1.02, 1.06, 1.10):
                tot = 0.0; pos = 0
                for slug, prints in tape.items():
                    pnl, _, _ = run(slug, prints, spread=spread, stop_s=stop_s, min_sum=min_sum)
                    tot += pnl; pos += pnl > 0
                print(f"  spread {spread:.2f} stop {stop_s:3}s min_sum {min_sum:.2f}: {tot / (n * N_SETS):+.3%}  pos {pos / n:.0%}")
