"""Backfill the lock family from the bot's own 2-second observation tape (read-only).

The paper bot only started recording lock_p/lock_early trades on 11-09; its obs.jsonl, however, holds every
2-second look at every book since 11-07 (v4 lines carry z, ask, rem, k_src, src). Re-running the exact rules on
that tape gives the persistence variants two extra days of history. A gap of more than 6 s between ticks is a
bot restart: the persistence memory is cleared, as the bot's would be.
Validation: the instantaneous 'lock' rule here must reproduce the bot's own by_day counts (52 / 67 / ...).
"""
import glob, gzip, json, os, sys
from collections import defaultdict
D = "data/fast"
SIZE = 20.0; LOCK_Z = 2.5; PERSIST = 2.0
M = json.load(open(f"{D}/results_meta.json"))
res = {s: md["up"] for s, md in M.items() if md.get("up") is not None}
try:
    for l in open(f"{D}/windows.jsonl"):
        o = json.loads(l)
        if o.get("result") is not None and o["slug"] not in res:
            res[o["slug"]] = bool(o["result"])
except OSError:
    pass


def obs_lines():
    files = sorted(glob.glob(f"{D}/obs-*.jsonl.gz")) + [f"{D}/obs.jsonl"]
    for f in files:
        op = gzip.open if f.endswith(".gz") else open
        try:
            with op(f, "rt") as fh:
                for line in fh:
                    try:
                        o = json.loads(line)
                    except ValueError:
                        continue
                    if o.get("v") == 4 and o.get("src") is not None:
                        yield o
        except Exception:  # noqa: BLE001
            pass


# group by tick (ts) -> list of obs; ticks in time order
ticks = defaultdict(list)
for o in obs_lines():
    ticks[o["ts"]].append(o)
print("ticks", len(ticks), "obs", sum(len(v) for v in ticks.values()))

since = {}; done = set(); trades = []; prev_ts = None
for ts in sorted(ticks):
    if prev_ts is not None and ts - prev_ts > 6:
        since.clear()                       # restart: the bot's memory was empty
    prev_ts = ts
    for o in ticks[ts]:
        slug, side, a_px, a_sz, zs, rem = o["slug"], o["side"], o["ask"], o["ask_sz"], o["z"], o["rem"]
        asset = slug.split("-")[0]; w = {"5m": 300, "15m": 900, "4h": 14400}[slug.split("-")[2]]
        k_ok = o["k_src"] in ("ptb", "twap", "chainlink") and o["src"] == "chainlink"
        picks = []
        lock_base = rem <= 60 and 0.50 <= a_px <= 0.97 and k_ok
        lk = (slug, side)
        for zmin in (2.0, 2.5, 3.0):
            key = (lk, zmin)
            if lock_base and zs >= zmin:
                since.setdefault(key, ts)
            else:
                since.pop(key, None)
        A = o["A"] if o.get("A") is not None else o["spot"]
        margin_bp = abs(o["g"] * A + (1 - o["g"]) * o["spot"] - o["K"]) / o["K"] * 1e4
        if lock_base and zs >= LOCK_Z:
            picks.append("lock"); held = ts - since[(lk, LOCK_Z)]
            if margin_bp >= 1.0:
                picks.append("lock_m")
                if held >= PERSIST: picks.append("lock_pm")
            if held >= PERSIST: picks.append("lock_p")
            # cheap variants: the 0.93-0.97 asks (2/3 of the capital) earn ~0 (replay: -0.2%/$); the edge is in asks <= 0.92.
            # With <= 20 s left a cheap ask means the market knows better (first-signal study: 9/15 wins), unless margin >= 1 bp
            if a_px <= 0.92 and (rem > 20 or margin_bp >= 1.0): picks.append("lock_c")
            if a_px <= 0.92 and margin_bp >= 1.0: picks.append("lock_cm")
            if a_px <= 0.92 and rem > 20 and held >= PERSIST: picks.append("lock_cp")
            if held >= 1.0: picks.append("lock_p1")
            if held >= 3.0: picks.append("lock_p3")
            if held >= 5.0: picks.append("lock_p5")
            if held >= PERSIST and asset in ("btc", "eth", "bnb"): picks.append("lock_p_majors")
            if held >= PERSIST and w == 900: picks.append("lock_p_15m")
            if held >= PERSIST: picks.append("lock_p_50")
        ek = (lk, "early")
        if 60 < rem <= 140 and zs >= 2.5 and 0.50 <= a_px <= 0.95 and k_ok:
            since.setdefault(ek, ts)
            if ts - since[ek] >= PERSIST: picks.append("lock_early")
        else:
            since.pop(ek, None)
        if lock_base and zs >= 2.0 and (lk, 2.0) in since and ts - since[(lk, 2.0)] >= PERSIST: picks.append("lock_p_z2")
        if lock_base and zs >= 3.0 and (lk, 3.0) in since and ts - since[(lk, 3.0)] >= PERSIST: picks.append("lock_p_z3")
        for strat in picks:
            if any((strat, slug, s) in done for s in ("Up", "Down")):
                continue
            cap = 50.0 if strat == "lock_p_50" else SIZE
            shares = round(min(a_sz, cap / a_px), 2)
            if shares < 5:
                continue
            done.add((strat, slug, side))
            won = res.get(slug)
            if won is None:
                continue
            win = 1.0 if (won == (side == "Up")) else 0.0
            fee = 0.07 * a_px * (1 - a_px)
            trades.append({"ts": ts, "strat": strat, "slug": slug, "asset": asset, "w": w, "side": side, "price": a_px, "shares": shares,
                           "z": zs, "rem": rem, "margin_bp": round(margin_bp, 2), "won": int(win), "pnl": round(shares * (win - a_px - fee), 2), "stake": round(shares * a_px, 2)})

import datetime as dt
def day(ts): return dt.datetime.fromtimestamp(ts, dt.timezone.utc).strftime("%m-%d")
by = defaultdict(lambda: [0, 0, 0.0, 0.0])
for t in trades:
    for key in (t["strat"], f'{t["strat"]} {day(t["ts"])}'):
        b = by[key]; b[0] += 1; b[1] += t["won"]; b[2] += t["stake"]; b[3] += t["pnl"]
order = ["lock", "lock_m", "lock_pm", "lock_c", "lock_cm", "lock_cp", "lock_p1", "lock_p", "lock_p3", "lock_p5", "lock_p_z2", "lock_p_z3", "lock_p_majors", "lock_p_15m", "lock_p_50", "lock_early"]
print(f"\n{'rule':14} {'n':>5} {'win':>6} {'staked':>9} {'pnl':>9} {'pnl/$':>7}")
for k in order:
    n, w_, st, pnl = by[k]
    if n: print(f"{k:14} {n:5} {w_ / n:6.1%} {st:9.0f} {pnl:+9.1f} {pnl / st if st else 0:+7.1%}")
print("\nby day:")
for k in order:
    row = [f"{d}: n {by[f'{k} {d}'][0]:3} win {by[f'{k} {d}'][1] / max(by[f'{k} {d}'][0], 1):.0%} {by[f'{k} {d}'][3]:+7.1f}" for d in sorted({day(t['ts']) for t in trades}) if by[f'{k} {d}'][0]]
    print(f"{k:14} | " + " | ".join(row))
# per asset / window for lock_p
pa = defaultdict(lambda: [0, 0, 0.0])
for t in trades:
    if t["strat"] == "lock_p":
        b = pa[t["asset"]]; b[0] += 1; b[1] += t["won"]; b[2] += t["pnl"]
        b = pa[f'{t["w"] // 60}m']; b[0] += 1; b[1] += t["won"]; b[2] += t["pnl"]
print("\nlock_p by asset/window:", {k: f"n{v[0]} w{v[1]} {v[2]:+.1f}" for k, v in sorted(pa.items())})
los = [t for t in trades if t["strat"] in ("lock_p", "lock_c") and not t["won"]]
print("\nlock_p / lock_c losers:")
for t in los:
    print(f"  {t['strat']:7} {dt.datetime.fromtimestamp(t['ts'], dt.timezone.utc):%m-%d %H:%M:%S} {t['slug']:28} {t['side']:4} ask {t['price']:.2f} z {t['z']:4.1f} rem {t['rem']:3} margin {t['margin_bp']:5.2f} {t['pnl']:+.1f}")
json.dump(trades, open(f"{D}/lock_variants_replay.json", "w"))
