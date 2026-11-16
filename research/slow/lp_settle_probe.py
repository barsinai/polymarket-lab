"""LP-1 v2 read-out with the leftover inventory valued at what it is really worth (read-only, no orders).

Why (11-16): lp_paper.py never settled a market - its Gamma lookup drops closed markets, so inventory left in markets we stopped
quoting stayed marked at the fair price of our LAST run there (up to two days old; 126 of 128 inventory markets). This probe
values every leftover position at the resolution (closed markets) or at today's price (open markets: the middle of the book when
the spread is <= 10c, else the last trade) and re-states trading P&L for both fill models, by kind and for the $200 slice.
Reads data/slow/lp_paper_state.json; writes nothing."""
import json, os, re, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import collect  # noqa: E402

st = json.load(open("data/slow/lp_paper_state.json")); ms = st["markets"]; now = time.time()
inv = [c for c, x in ms.items() if abs(x.get("inv", 0)) > 1e-9 or abs(x.get("inv2", 0)) > 1e-9]
gm = {}
for flag in (None, "true"):
    for i in range(0, len(inv), 40):
        p = [("condition_ids", c) for c in inv[i:i + 40]] + [("limit", 100)] + ([("closed", "true")] if flag else [])
        for m in collect.get(f"{collect.GAMMA}/markets", p, tries=3) or []:
            gm[m.get("conditionId")] = m


def value(c):
    """value of one YES share now: (value, 'resolved' | 'open' | 'unknown')"""
    m = gm.get(c)
    if not m:
        return None, "unknown"
    try:
        pr = [float(p) for p in json.loads(m.get("outcomePrices") or "[]")]
    except Exception:  # noqa: BLE001
        pr = []
    if m.get("closed") and len(pr) == 2:
        if max(pr) >= 0.99:
            return (1.0 if pr[0] >= 0.99 else 0.0), "resolved"
        if abs(pr[0] - 0.5) < 0.01:
            return 0.5, "resolved"
    try:
        bb, ba = float(m.get("bestBid") or 0), float(m.get("bestAsk") or 0)
    except Exception:  # noqa: BLE001
        bb = ba = 0.0
    if 0 < bb < ba < 1 and ba - bb <= 0.10:
        return (bb + ba) / 2, "open"
    try:
        lt = float(m.get("lastTradePrice") or 0)
    except Exception:  # noqa: BLE001
        lt = 0.0
    if 0 < lt < 1:
        return lt, "open"
    return (pr[0] if len(pr) == 2 else None), "open" if len(pr) == 2 else "unknown"


val = {}; kind = {}
for c in inv:
    v, k = value(c); val[c] = v; kind[c] = k
print(f"LP-1 v2: started {time.strftime('%m-%d %H:%M', time.gmtime(st['started']))} UTC, {st['runs']} runs, {(now - st['started']) / 86400:.2f} days, {len(ms)} markets ever quoted")
print(f"markets holding leftover inventory: {len(inv)}; resolved {sum(1 for k in kind.values() if k == 'resolved')}, still open {sum(1 for k in kind.values() if k == 'open')}, "
      f"not found {sum(1 for k in kind.values() if k == 'unknown')}")


def pnl(c, x, model, true_value=True):
    cash, q = (x["cash"], x["inv"]) if model == 1 else (x.get("cash2", 0.0), x.get("inv2", 0.0))
    v = val.get(c) if (true_value and val.get(c) is not None) else (x.get("fair") or 0)
    return cash + q * v


isw = lambda x: "temperature" in x["q"].lower()   # noqa: E731
iscount = lambda x: bool(re.search(r"\bsay\b|\bposts?\b|tweets?\b|mention|on stream|\bviews\b", x["q"].lower()))   # noqa: E731
N35_FROM, N38_FROM = 1794697200, 1794711600


def block(name, items):
    r = sum(x["reward"] for c, x in items)
    a1, a2 = sum(pnl(c, x, 1, False) for c, x in items), sum(pnl(c, x, 2, False) for c, x in items)
    b1, b2 = sum(pnl(c, x, 1) for c, x in items), sum(pnl(c, x, 2) for c, x in items)
    print(f"   {name:34} markets {len(items):3}  formula reward ${r:8.2f} | trading P&L, tape fills: report ${a1:+8.2f} -> true ${b1:+8.2f} | pessimistic: report ${a2:+8.2f} -> true ${b2:+8.2f}"
          f" | true pessimistic / formula {100 * b2 / r if r else 0:+5.0f}%")
    return r, b1, b2


items = list(ms.items())
print("\n== trading P&L: as lp_paper reports it (leftovers at the last fair price) -> with leftovers at their real value")
R, T1, T2 = block("ALL", items)
block("weather (same-day temperature)", [(c, x) for c, x in items if isw(x)])
block("live count / mention / views", [(c, x) for c, x in items if not isw(x) and iscount(x)])
block("core (everything else)", [(c, x) for c, x in items if not isw(x) and not iscount(x)])
block("forward core (opened >= 11-15 01h)", [(c, x) for c, x in items if not isw(x) and not iscount(x) and x["opened"] >= N38_FROM])
block("forward other (opened >= 11-14 21h)", [(c, x) for c, x in items if not isw(x) and x["opened"] >= N35_FROM])
block("only resolved-inventory + flat markets", [(c, x) for c, x in items if kind.get(c, "resolved") == "resolved"])
print(f"\n== net = formula reward x payout ratio + true trading P&L (tape fills | pessimistic)")
for f in (1.0, 0.5, 0.2):
    print(f"   paid {int(100 * f):3}% of the formula: ${R * f + T1:+9.2f} | ${R * f + T2:+9.2f}")
print(f"   break-even payout ratio: tape {100 * -T1 / R:.0f}% | pessimistic {100 * -T2 / R:.0f}%")
# the simulated $200 / 48 h test: markets in entry order, largest pool first, while capital fits
sl, cap = [], 0.0
for c, x in sorted(items, key=lambda cx: (cx[1]["opened"], -(cx[1].get("rate") or 0))):
    k = x.get("capital") or 0.0
    if cap + k <= 200:
        sl.append((c, x)); cap += k
print(f"\n== the $200 slice ({len(sl)} markets, ${cap:.0f} of quotes)")
r, b1, b2 = block("$200 slice", sl)
for f in (1.0, 0.5, 0.2):
    print(f"   paid {int(100 * f):3}%: ${r * f + b1:+8.2f} | ${r * f + b2:+8.2f}")
for c, x in sl:
    print(f"      reward ${x['reward']:6.2f} quoted {(x['last_ts'] - x['opened']) / 3600:5.1f} h  tape {pnl(c, x, 1):+7.2f} pess {pnl(c, x, 2):+7.2f}  {kind.get(c, 'flat'):8} {x.get('why_off') or 'active':28} {x['q'][:60]}")
print("\n== largest changes once leftovers are valued properly (pessimistic model)")
ch = sorted(((pnl(c, ms[c], 2) - pnl(c, ms[c], 2, False), c) for c in inv), key=lambda t: t[0])
for d, c in ch[:8] + ch[-8:]:
    x = ms[c]
    print(f"   {d:+8.2f}  inv2 {x.get('inv2', 0):+7.1f} last fair {x.get('fair'):.3f} -> {val[c] if val[c] is not None else float('nan'):.3f} ({kind[c]})  {x['q'][:66]}")
