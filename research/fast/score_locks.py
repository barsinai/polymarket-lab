"""Score the paper bot's lock-family rules against the official results (read-only).

Usage: python research/fast/score_locks.py [since_iso_utc]   (default: the 11-09 21:39 restart)
Prints per-rule n / win rate / staked / P&L / P&L per $ since the given time, a per-day table, and the losers
with their margin_bp (distance of our estimated final TWAP from the price to beat, in basis points).
"""
import json, sys, datetime as dt
from collections import defaultdict
D = "data/fast"
since = dt.datetime.fromisoformat(sys.argv[1]).replace(tzinfo=dt.timezone.utc).timestamp() if len(sys.argv) > 1 else dt.datetime(2026, 11, 9, 21, 39, tzinfo=dt.timezone.utc).timestamp()
M = json.load(open(f"{D}/results_meta.json"))
res = {s: md["up"] for s, md in M.items() if md.get("up") is not None}
try:
    for l in open(f"{D}/windows.jsonl"):
        o = json.loads(l)
        if o.get("result") is not None and o["slug"] not in res:
            res[o["slug"]] = bool(o["result"])
except OSError:
    pass


def day(ts): return dt.datetime.fromtimestamp(ts, dt.timezone.utc).strftime("%m-%d")


by = defaultdict(lambda: [0, 0, 0.0, 0.0, 0]); rows = []
for l in open(f"{D}/trades.jsonl"):
    try:
        t = json.loads(l)
    except ValueError:
        continue
    if t.get("ts", 0) < since or not str(t.get("strat", "")).startswith("lock"):
        continue
    s = t["strat"]; won = res.get(t["slug"])
    for key in (s, f"{s} {day(t['ts'])}"):
        by[key][0] += 1
        if won is None:
            by[key][4] += 1
    if won is None:
        continue
    win = won == (t["side"] == "Up"); px = t["price"]; sh = t["shares"]; fee = 0.07 * px * (1 - px)
    pnl = sh * ((1.0 if win else 0.0) - px - fee)
    for key in (s, f"{s} {day(t['ts'])}"):
        by[key][1] += win; by[key][2] += sh * px; by[key][3] += pnl
    rows.append((t["ts"], s, t["slug"], t["side"], px, t.get("z"), t.get("margin_bp"), win, pnl))

order = ["lock", "lock_m", "lock_pm", "lock_p1", "lock_p", "lock_p3", "lock_p5", "lock_p_z2", "lock_p_z3", "lock_p_majors", "lock_p_15m", "lock_p_50", "lock_early"]
order += sorted(k for k in by if " " not in k and k not in order)
print(f"since {dt.datetime.fromtimestamp(since, dt.timezone.utc):%m-%d %H:%M} UTC\n{'rule':14}{'n':>5}{'open':>5}{'win':>7}{'staked':>8}{'pnl':>8}{'pnl/$':>8}")
for k in order:
    if k not in by:
        continue
    n, w, st, p, op = by[k]; nn = n - op
    print(f"{k:14}{n:5}{op:5}{(w / nn if nn else 0):7.1%}{st:8.0f}{p:+8.1f}{(p / st if st else 0):+8.1%}")
days = sorted({day(r[0]) for r in rows})
if len(days) > 1:
    print("\nby day (settled only):")
    for k in order:
        cells = []
        for d in days:
            b = by.get(f"{k} {d}")
            if b and b[0] - b[4]:
                cells.append(f"{d}: n {b[0] - b[4]:3} win {b[1] / (b[0] - b[4]):4.0%} {b[3]:+7.1f}")
        if cells:
            print(f"{k:14} | " + " | ".join(cells))
print("\nlosers (all lock rules):")
for r in sorted(rows):
    if not r[7]:
        md = M.get(r[2], {}); ptb, fin = md.get("ptb"), md.get("final")
        off = f"official |final-ptb| {abs(float(fin) - float(ptb)) / float(ptb) * 1e4:.2f} bp" if ptb and fin else ""
        print(f"  {dt.datetime.fromtimestamp(r[0], dt.timezone.utc):%m-%d %H:%M:%S} {r[1]:10} {r[2]:26} {r[3]:4} ask {r[4]:.2f} z {r[5]} margin {r[6]} bp {r[8]:+.1f}  {off}")
print("\nlock_m / lock_pm trades:")
for r in sorted(rows):
    if r[1] in ("lock_m", "lock_pm"):
        print(f"  {dt.datetime.fromtimestamp(r[0], dt.timezone.utc):%m-%d %H:%M:%S} {r[1]:8} {r[2]:26} {r[3]:4} ask {r[4]:.2f} z {r[5]} margin {r[6]} bp {'W' if r[7] else 'L'} {r[8]:+.1f}")
