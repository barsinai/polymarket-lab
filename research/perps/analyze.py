"""Funding-gap carry, after costs. Position: long the perp on the venue with the LOWER funding, short on the
higher (receive the gap each hour). Enter when the trailing-24h mean gap exceeds ENTER per hour, exit when it
falls under EXIT (or flips). Costs per round trip (open + close, both legs): taker 0.17%, maker 0.055%.
Basis (price difference between venues) is ignored here; candles come later. P&L in % of one leg's notional."""
import gzip, json, collections, sys
from datetime import datetime
pm = collections.defaultdict(dict); hl = collections.defaultdict(dict)
for l in gzip.open("data/perps/pm_funding.jsonl.gz", "rt"):
    d = json.loads(l); c = d["_sym"].split("-")[0]
    pm[c][int(datetime.fromisoformat(d["timestamp"].replace("Z", "+00:00")).timestamp() // 3600)] = float(d["funding_rate"])
for l in gzip.open("data/perps/hl_funding.jsonl.gz", "rt"):
    d = json.loads(l); hl[d["coin"]][int(d["time"] // 1000 // 3600)] = float(d["fundingRate"])
COST = {"taker": 0.0017, "maker": 0.00055}


def run(diff, enter, exit_, cost):
    pos = 0; pnl = 0.0; trades = 0; held = 0; worst = 0.0; eq = 0.0; peak = 0.0
    for i in range(24, len(diff)):
        m = sum(diff[i - 24:i]) / 24
        want = pos
        if pos == 0 and abs(m) > enter:
            want = 1 if m > 0 else -1
        elif pos != 0 and (pos * m < exit_):
            want = 0
        if want != pos:
            pnl -= cost / 2 * (abs(want) + abs(pos)); trades += 1; pos = want
        if pos:
            pnl += pos * diff[i]; held += 1
        peak = max(peak, pnl); worst = min(worst, pnl - peak)
    return pnl, trades, held, worst


rows = []
for c in pm:
    if c not in hl:
        continue
    common = sorted(set(pm[c]) & set(hl[c]))
    if len(common) < 300:
        continue
    diff = [pm[c][t] - hl[c][t] for t in common]  # >0: Polymarket longs pay more -> short PM, long HL
    for mode in ("maker", "taker"):
        pnl, tr, held, dd = run(diff, 3e-5, 1e-5, COST[mode])
        days = len(common) / 24
        rows.append((c, mode, len(common), pnl * 100, pnl / days * 365 * 100, tr, held / len(common), dd * 100))
print(f"{'coin':8} {'fees':5} {'hours':>5} {'pnl %':>7} {'APR %':>7} {'trades':>6} {'time in':>7} {'max dd %':>8}")
for r in sorted(rows, key=lambda r: -r[4]):
    print(f"{r[0]:8} {r[1]:5} {r[2]:5d} {r[3]:7.2f} {r[4]:7.1f} {r[5]:6d} {r[6]:7.0%} {r[7]:8.2f}")
