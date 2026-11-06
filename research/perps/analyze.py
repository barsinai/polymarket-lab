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


def basis_series(c, hours):
    """(PM close - HL close) / HL close per hour; None where either is missing"""
    import os
    pp, hp = f"data/perps/pm_candles/{c}.json", f"data/perps/hl_candles/{c}.json"
    if not (os.path.exists(pp) and os.path.exists(hp)):
        return None
    a = {int(datetime.fromisoformat(x["timestamp"].replace("Z", "+00:00")).timestamp() // 3600): float(x["close"]) for x in json.load(open(pp))}
    b = {int(x["t"] // 1000 // 3600): float(x["c"]) for x in json.load(open(hp))}
    return [((a[h] - b[h]) / b[h]) if h in a and h in b else None for h in hours]


def run(diff, enter, exit_, cost, basis=None):
    pos = 0; pnl = 0.0; trades = 0; held = 0; worst = 0.0; eq = 0.0; peak = 0.0; bpnl = 0.0
    for i in range(24, len(diff)):
        if basis is not None and pos and basis[i] is not None and basis[i - 1] is not None:
            d_ = -pos * (basis[i] - basis[i - 1]); pnl += d_; bpnl += d_
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
    run.bpnl = bpnl
    return pnl, trades, held, worst


rows = []
for c in pm:
    if c not in hl:
        continue
    common = sorted(set(pm[c]) & set(hl[c]))
    if len(common) < 300:
        continue
    diff = [pm[c][t] - hl[c][t] for t in common]  # >0: Polymarket longs pay more -> short PM, long HL
    basis = basis_series(c, common)
    for mode in ("taker",):
        pnl, tr, held, dd = run(diff, 3e-5, 1e-5, COST[mode], basis)
        days = len(common) / 24
        rows.append((c, mode, len(common), pnl * 100, pnl / days * 365 * 100, tr, held / len(common), dd * 100, run.bpnl * 100, basis is not None))
print(f"{'coin':8} {'fees':5} {'hours':>5} {'pnl %':>7} {'APR %':>7} {'trades':>6} {'time in':>7} {'max dd %':>8} {'basis %':>8}")
for r in sorted(rows, key=lambda r: -r[4]):
    print(f"{r[0]:8} {r[1]:5} {r[2]:5d} {r[3]:7.2f} {r[4]:7.1f} {r[5]:6d} {r[6]:7.0%} {r[7]:8.2f} {r[8]:8.2f} {'' if r[9] else 'no candles'}")
