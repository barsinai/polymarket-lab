"""Slow strategy #1: patient bids. Backtest on the random-sample trade tape (data/trades, ~54k closed markets).

Idea: in thin long-dated markets an impatient seller sometimes walks the book down far below where the market
traded over the previous day. A resting bid X below the trailing reference would be filled by that print.
We then either hold to resolution or sell back a day later. No speed involved: the bid rests for hours.

For every print at Yes-price p (converted so both outcomes are in Yes terms):
  ref  = $-weighted average Yes-price of trades in the previous 24 h (>= 5 trades, >= $200, 0.10 <= ref <= 0.90)
  hit  = p <= ref - X   (a seller reached our bid at b = ref - X; we buy Yes at b)      [mirror for buyers: buy No]
  exit = VWAP of trades from 1 h to 25 h after the hit, minus 1c (we sell into the market) / or resolution
Filters: not within the last 24 h before the market closes (resolution news), one fill per market per day,
markets whose tape is truncated are skipped unless the print itself is >= $100 (those are complete).
Output: data/slow/patient_bids.json + printed tables by X, time-to-close and reference level.
"""
import glob, gzip, json, os, sys
import numpy as np

T_REF, T_EXIT0, T_EXIT1 = 24 * 3600, 3600, 25 * 3600
XS = (0.06, 0.10, 0.15, 0.20)
os.makedirs("data/slow", exist_ok=True)

# resolved markets: winner index and close time, from the listing
winner, close = {}, {}
for f in sorted(glob.glob("data/listing/*.jsonl.gz")):
    for line in gzip.open(f, "rt"):
        m = json.loads(line)
        try:
            pr = json.loads(m.get("outcomePrices") or "[]")
            if len(pr) == 2 and max(float(x) for x in pr) >= 0.99:
                winner[int(m["id"])] = 0 if float(pr[0]) > float(pr[1]) else 1
                e = m.get("closedTime") or m.get("endDate") or m.get("end_date_iso") or ""
                close[int(m["id"])] = e
        except (ValueError, TypeError, KeyError):
            pass
from datetime import datetime, timezone  # noqa: E402
def ts_of(s):
    try:
        s = s.replace("Z", "+00:00")
        if s.endswith("+00"):
            s += ":00"
        return datetime.fromisoformat(s).timestamp()
    except Exception:  # noqa: BLE001
        return None
close_ts = {k: ts_of(v) for k, v in close.items()}
print(f"resolved markets in listing: {len(winner)}", flush=True)

rows_out = []   # (mid, X, side(+1 yes/-1 no), t, ref, b, size_usd, exit_vwap, Y, days_to_close, truncated)
n_mk = 0
for f in sorted(glob.glob("data/trades/parts/*.jsonl.gz")):
    for line in gzip.open(f, "rt"):
        r = json.loads(line); mid = int(r["market_id"])
        if mid not in winner or close_ts.get(mid) is None:
            continue
        rows = r["trades"] + r.get("big", [])
        if len(rows) < 10:
            continue
        n_mk += 1
        a = np.unique(np.array(rows, dtype=np.float64), axis=0); a = a[np.argsort(a[:, 0], kind="stable")]
        ts, side, oc, px, sz, wi = a.T
        yes = np.where(oc == 0, px, 1 - px)                       # Yes-price of every print
        usd = sz * px
        d = np.where((side == 1) == (oc == 0), 1.0, -1.0)           # +1 = buying Yes (or selling No), -1 = selling Yes
        Y = 1.0 if winner[mid] == 0 else 0.0
        cum_usd = np.concatenate([[0.0], np.cumsum(usd)]); cum_pu = np.concatenate([[0.0], np.cumsum(usd * yes)]); cum_n = np.arange(len(ts) + 1)
        i0 = np.searchsorted(ts, ts - T_REF, side="left")            # first index inside the trailing day
        n_ref = cum_n[np.arange(len(ts))] - cum_n[i0]; usd_ref = cum_usd[np.arange(len(ts))] - cum_usd[i0]
        with np.errstate(invalid="ignore", divide="ignore"):
            ref = (cum_pu[np.arange(len(ts))] - cum_pu[i0]) / usd_ref
        ok = (n_ref >= 5) & (usd_ref >= 200) & (ref >= 0.10) & (ref <= 0.90)
        j0 = np.searchsorted(ts, ts + T_EXIT0, side="left"); j1 = np.searchsorted(ts, ts + T_EXIT1, side="right")
        with np.errstate(invalid="ignore", divide="ignore"):
            exit_vwap = (cum_pu[j1] - cum_pu[j0]) / (cum_usd[j1] - cum_usd[j0])
        has_exit = (cum_n[j1] - cum_n[j0]) >= 3
        dtc = (close_ts[mid] - ts) / 86400.0
        trunc = bool(r.get("truncated"))
        for X in XS:
            for sgn in (+1, -1):
                if sgn > 0:
                    hit = ok & (d < 0) & (yes <= ref - X)                 # seller of Yes reached our Yes bid at ref - X
                    b = ref - X
                else:
                    hit = ok & (d > 0) & (yes >= ref + X)                 # buyer of Yes swept to ref + X: we sold Yes there = bought No at 1-(ref+X)
                    b = ref + X
                idx = np.nonzero(hit & (dtc > 1.0))[0]
                if len(idx) == 0:
                    continue
                last_day = -1e18
                for i in idx:
                    if ts[i] - last_day < 86400:
                        continue
                    if trunc and usd[i] < 100:
                        continue
                    last_day = ts[i]
                    rows_out.append((mid, X, sgn, ts[i], float(ref[i]), float(b[i]), float(min(usd[i], 20.0)), float(exit_vwap[i]) if has_exit[i] else None, Y, float(dtc[i]), trunc))
print(f"markets scanned {n_mk}, fills {len(rows_out)}", flush=True)
json.dump(rows_out, open("data/slow/patient_bids.json", "w"))

# ---- scoring
def score(sel, label):
    if not sel:
        return
    # P&L per $ staked: Yes buy at b -> value Y; No buy at (1-b) -> value (1-Y). Exit at 24h VWAP (minus 1c) when available.
    st = pnl_res = pnl_exit = 0.0; n_exit = 0; st_exit = 0.0
    for mid, X, sgn, t, ref, b, usd_, ev, Y, dtc, tr in sel:
        if sgn > 0:
            cost, val, ex = b, Y, (ev - 0.01) if ev is not None else None
        else:
            cost, val, ex = 1 - b, 1 - Y, (1 - ev - 0.01) if ev is not None else None
        if cost <= 0.01:
            continue
        sh = usd_ / cost
        st += usd_; pnl_res += sh * (val - cost)
        if ex is not None:
            st_exit += usd_; pnl_exit += sh * (ex - cost); n_exit += 1
    print(f"  {label:34} fills {len(sel):6}  hold-to-resolution {pnl_res / st:+.3f}/$   sell 24h later {pnl_exit / st_exit if st_exit else 0:+.3f}/$ (n={n_exit})")

print("\nPATIENT BIDS, by depth X below/above the trailing-day average (both directions)")
for X in XS:
    score([r for r in rows_out if r[1] == X], f"X = {X:.2f}")
print("\nby direction (X = 0.10)")
score([r for r in rows_out if r[1] == 0.10 and r[2] > 0], "buy Yes after a dump")
score([r for r in rows_out if r[1] == 0.10 and r[2] < 0], "buy No after a spike")
print("\nby days to close (X = 0.10)")
for lo, hi in ((1, 3), (3, 7), (7, 30), (30, 10000)):
    score([r for r in rows_out if r[1] == 0.10 and lo <= r[9] < hi], f"{lo}-{hi} days to close")
print("\nby reference level (X = 0.10)")
for lo, hi in ((0.10, 0.30), (0.30, 0.50), (0.50, 0.70), (0.70, 0.90)):
    score([r for r in rows_out if r[1] == 0.10 and lo <= r[4] < hi], f"ref {lo:.2f}-{hi:.2f}")
print("\ncomplete tapes only (X = 0.10)")
score([r for r in rows_out if r[1] == 0.10 and not r[10]], "not truncated")
