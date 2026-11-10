"""Slow-market backtests on resolved Polymarket markets with daily price paths (data/history, from history_pull.py).
Every rule is evaluated on EVERY market/day where it would have fired, settled with the official outcome, taker fee
0.07*p*(1-p) on the price paid, $20 per position, one position per market per rule. Results by month (time split) so a
rule that worked only in one month shows it.

Rules:
  longshot_NO  : buy NO when YES trades in [lo, hi) with d days left (sell the longshot)       bands x days-to-end
  favourite_YES: buy YES when YES trades in [lo, hi) with d days left (buy the sure thing)
  converge     : buy the side priced >= 0.90 with 1-3 days left (resolution approach)
Returns per $ and annualised (by average holding days) per band, plus the hit rate and the worst month.
Note: daily prices are the last trade of the day (CLOB history) - a buy is assumed at that price plus half a 2c spread.
"""
import json, os, glob, math, collections, datetime as dt
D = "data/history"; STAKE = 20.0; SPREAD = 0.02
mk = [json.loads(l) for l in open(f"{D}/markets.jsonl")]
print("markets", len(mk), "with prices", sum(1 for m in mk if m["n_prices"]), "yes won", sum(m["yes_won"] for m in mk))
P = {}
for m in mk:
    try:
        P[m["id"]] = json.load(open(f"{D}/prices/{m['id']}.json"))
    except OSError:
        pass


def end_ts(m): return dt.datetime.fromisoformat(m["end"]).replace(tzinfo=dt.timezone.utc).timestamp()


def month(ts): return dt.datetime.fromtimestamp(ts, dt.timezone.utc).strftime("%Y-%m")


RESULTS = []


def run(name, pick, exit_at=None, stable=None):
    """pick(price, days_left) -> side ('YES'/'NO') or None; first qualifying day per market.
    exit_at: sell when the side's price reaches this level (at exit_at - SPREAD/2) instead of holding to resolution.
    stable: require that the side's price did not fall by more than this over the previous 3 daily points."""
    by = collections.defaultdict(lambda: [0, 0, 0.0, 0.0, 0.0]); rows = []
    for m in mk:
        h = P.get(m["id"])
        if not h: continue
        e = end_ts(m)
        for i, (t, p) in enumerate(h):
            d = (e - t) / 86400
            if d < 0.5: break
            side = pick(p, d)
            if not side: continue
            sp = p if side == "YES" else 1 - p
            if stable is not None and i >= 3:
                prev = [(q if side == "YES" else 1 - q) for _, q in h[i - 3:i]]
                if sp < max(prev) - stable: continue
            price = sp + SPREAD / 2
            if price <= 0.01 or price >= 0.99: break
            fee = 0.07 * price * (1 - price); sh = STAKE / price
            win = (m["yes_won"] == 1) == (side == "YES"); pnl = sh * ((1 if win else 0) - price - fee); hold = d
            if exit_at is not None:
                for t2, p2 in h[i + 1:]:
                    sp2 = p2 if side == "YES" else 1 - p2
                    if sp2 >= exit_at:
                        px2 = exit_at - SPREAD / 2; pnl = sh * (px2 - price - fee - 0.07 * px2 * (1 - px2)); hold = (t2 - t) / 86400; break
            b = by[month(t)]; b[0] += 1; b[1] += win; b[2] += STAKE; b[3] += pnl; b[4] += hold
            rows.append((m["id"], t, side, price, d, win, pnl)); break
    tot = [sum(v[i] for v in by.values()) for i in range(5)]
    if not tot[0]: return
    ann = (tot[3] / tot[2]) * 365 / (tot[4] / tot[0]) if tot[0] else 0
    worst = min((v[3] / v[2], k) for k, v in by.items() if v[2])
    RESULTS.append({"rule": name.strip(), "n": tot[0], "hit": round(tot[1] / tot[0], 4), "ret": round(tot[3] / tot[2], 4), "hold_days": round(tot[4] / tot[0], 1),
                    "ann": round(ann, 3), "worst_month": worst[1], "worst_ret": round(worst[0], 4), "months": {k: [v[0], round(v[3] / v[2], 4)] for k, v in sorted(by.items())}})
    print(f"{name:40} n {tot[0]:5} hit {tot[1] / tot[0]:6.1%} pnl/$ {tot[3] / tot[2]:+7.2%} hold {tot[4] / tot[0]:5.1f}d ann {ann:+7.1%}  worst month {worst[1]} {worst[0]:+.1%} | "
          + " ".join(f"{k}:{v[0]}/{v[3] / v[2]:+.0%}" for k, v in sorted(by.items())))
    return rows


print("\n--- sell the longshot: buy NO when YES is in the band, with the given days left (first day it qualifies) ---")
for lo, hi in ((0.02, 0.05), (0.05, 0.10), (0.10, 0.15), (0.15, 0.25)):
    for dlo, dhi in ((1, 3), (3, 7), (7, 14), (14, 30), (30, 90)):
        run(f"NO  yes in [{lo:.2f},{hi:.2f}) {dlo:2}-{dhi:2}d left", lambda p, d, lo=lo, hi=hi, dlo=dlo, dhi=dhi: "NO" if lo <= p < hi and dlo <= d < dhi else None)
print("\n--- buy the favourite: YES in the band ---")
for lo, hi in ((0.75, 0.85), (0.85, 0.90), (0.90, 0.95), (0.95, 0.98)):
    for dlo, dhi in ((1, 3), (3, 7), (7, 14), (14, 30), (30, 90)):
        run(f"YES yes in [{lo:.2f},{hi:.2f}) {dlo:2}-{dhi:2}d left", lambda p, d, lo=lo, hi=hi, dlo=dlo, dhi=dhi: "YES" if lo <= p < hi and dlo <= d < dhi else None)
print("\n--- favourite variants: stable price filter, early exit at 0.99 ---")
for lo, hi in ((0.90, 0.95), (0.95, 0.98)):
    run(f"YES [{lo:.2f},{hi:.2f}) 3-14d, stable (no 3c drop)", lambda p, d, lo=lo, hi=hi: "YES" if lo <= p < hi and 3 <= d < 14 else None, stable=0.03)
    run(f"YES [{lo:.2f},{hi:.2f}) 3-14d, exit at 0.99", lambda p, d, lo=lo, hi=hi: "YES" if lo <= p < hi and 3 <= d < 14 else None, exit_at=0.99)
    run(f"ANY [{lo:.2f},{hi:.2f}) 3-14d (either side)", lambda p, d, lo=lo, hi=hi: ("YES" if lo <= p < hi else "NO" if lo <= 1 - p < hi else None) if 3 <= d < 14 else None)
    run(f"ANY [{lo:.2f},{hi:.2f}) 3-14d, exit 0.99", lambda p, d, lo=lo, hi=hi: ("YES" if lo <= p < hi else "NO" if lo <= 1 - p < hi else None) if 3 <= d < 14 else None, exit_at=0.99)
print("\n--- buy the 15-25c side (the band where YES resolved more often than priced in the first sample) ---")
for dlo, dhi in ((3, 7), (7, 14), (14, 30), (30, 90)):
    run(f"YES yes in [0.15,0.25) {dlo:2}-{dhi:2}d left", lambda p, d, dlo=dlo, dhi=dhi: "YES" if 0.15 <= p < 0.25 and dlo <= d < dhi else None)
    run(f"YES yes in [0.25,0.40) {dlo:2}-{dhi:2}d left", lambda p, d, dlo=dlo, dhi=dhi: "YES" if 0.25 <= p < 0.40 and dlo <= d < dhi else None)
print("\n--- symmetric: buy whichever side is >= threshold with 1-3 days left (resolution approach) ---")
for th in (0.80, 0.85, 0.90, 0.95):
    run(f"converge side >= {th:.2f}, 1-3d left", lambda p, d, th=th: ("YES" if p >= th else "NO" if p <= 1 - th else None) if 1 <= d < 3 else None)
print("\n--- by category (longshot NO, yes in [0.03,0.12), 3-30d) ---")
cats = collections.defaultdict(list)
for m in mk:
    for t in (m.get("tags") or ["(none)"])[:3]:
        cats[t].append(m)
allm = mk
for cat, ms in sorted(cats.items(), key=lambda x: -len(x[1]))[:14]:
    mk = ms
    run(f"  {cat[:30]:30} ({len(ms)})", lambda p, d: "NO" if 0.03 <= p < 0.12 and 3 <= d < 30 else None)
mk = allm
json.dump({"markets": len(mk), "with_prices": sum(1 for m in mk if m["n_prices"]), "yes_won": sum(m["yes_won"] for m in mk), "results": RESULTS,
           "built": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}, open(f"{D}/backtest.json", "w"), indent=0)
