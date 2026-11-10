"""Parity maker backtest (read-only): the 15-minute and 5-minute windows of one asset that END at the same second
resolve on the same final TWAP against different prices to beat, so one share of each 'right side' pays >= $1
(the bot's taker 'pair' rule; riskless fills were rare). Here: post resting BIDS on both legs that add up to TARGET,
no taker fee; a leg counts as filled when its best ask later drops to our bid or below (someone sold into it).
Outcomes: both legs filled -> payoff >= $1 for TARGET (locked profit); one leg filled -> a directional position
(the legging risk); none -> nothing. Tape: data/fast/pairs*.jsonl(.gz) (every 2-s look at every aligned pair)."""
import glob, gzip, json, os, datetime as dt
from collections import defaultdict
D = "data/fast"
M = json.load(open(f"{D}/results_meta.json")); res = {s: md["up"] for s, md in M.items() if md.get("up") is not None}
TARGETS = [float(x) for x in os.environ.get("TARGETS", "0.90,0.95,0.98").split(",")]; R0 = int(os.environ.get("R0", "100"))

tape = defaultdict(list)
for f in sorted(glob.glob(f"{D}/pairs-*.jsonl.gz")) + [f"{D}/pairs.jsonl"]:
    op = gzip.open if f.endswith(".gz") else open; seen = set()
    try:
        with op(f, "rt") as fh:
            for line in fh:
                if hash(line) in seen:
                    continue
                seen.add(hash(line))
                try:
                    o = json.loads(line)
                except ValueError:
                    continue
                if len(o.get("legs", [])) == 2:
                    tape[(o["asset"], o["end"], o["legs"][0][1], o["legs"][1][1])].append(o)
    except Exception:  # noqa: BLE001
        pass
print("aligned pairs on tape:", len(tape), "ticks:", sum(len(v) for v in tape.values()))


def day(ts): return dt.datetime.fromtimestamp(ts, dt.timezone.utc).strftime("%m-%d")


stats = {}
for T in TARGETS:
    st = defaultdict(lambda: {"pairs": 0, "both": 0, "one": 0, "none": 0, "pnl": 0.0, "pnl_one": 0.0, "staked": 0.0, "taker_riskless": 0})
    for key, ticks in tape.items():
        a, end, s1, s2 = key
        if s1 not in res or s2 not in res:
            continue
        ticks.sort(key=lambda o: o["ts"])
        start = [o for o in ticks if o["rem"] <= R0 and o["legs"][0][2] and o["legs"][1][2]]
        if not start:
            continue
        o0 = start[0]; (side1, _, a1, _), (side2, _, a2, _) = o0["legs"]
        d = day(o0["ts"]); s = st[d]; s["pairs"] += 1
        if min(o["sum"] for o in ticks if o["rem"] <= 120) <= 0.995:
            s["taker_riskless"] += 1
        # split the target in proportion to the current asks; shares so that the pair costs $20
        x = round(a1 / (a1 + a2) * T, 2); y = round(T - x, 2); shares = 20.0 / T
        f1 = next((o for o in start if o["legs"][0][2] <= x), None); f2 = next((o for o in start if o["legs"][1][2] <= y), None)
        won1 = res[s1] == (side1 == "Up"); won2 = res[s2] == (side2 == "Up")
        if f1 and f2:
            s["both"] += 1; pay = (1 if won1 else 0) + (1 if won2 else 0)   # >= 1 by construction when the K order holds
            s["pnl"] += shares * (pay - T); s["staked"] += shares * T
        elif f1 or f2:
            s["one"] += 1; px, won = (x, won1) if f1 else (y, won2)
            s["pnl"] += shares * ((1 if won else 0) - px); s["pnl_one"] += shares * ((1 if won else 0) - px); s["staked"] += shares * px
        else:
            s["none"] += 1
    stats[T] = st
    tot = defaultdict(float)
    for d, s in st.items():
        for k, v in s.items():
            tot[k] += v
    print(f"\nTARGET {T:.2f} (bids posted at the first look with <= {R0} s left):")
    print(f"  pairs {int(tot['pairs'])}  both legs filled {int(tot['both'])}  one leg {int(tot['one'])}  none {int(tot['none'])}  | taker riskless (sum<=0.995 at some tick) {int(tot['taker_riskless'])}")
    print(f"  P&L ${tot['pnl']:+.1f} on ${tot['staked']:.0f} staked; of which one-leg positions ${tot['pnl_one']:+.1f}")
    for d in sorted(st):
        s = st[d]; print(f"    {d}: pairs {s['pairs']:3} both {s['both']:3} one {s['one']:3} pnl {s['pnl']:+7.1f} (one-leg {s['pnl_one']:+6.1f})")
json.dump({str(T): dict(st) for T, st in stats.items()}, open(f"{D}/parity_maker.json", "w"))
