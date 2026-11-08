"""Slow strategy: follow the strong traders (and/or fade the weak ones), done carefully. Random trade tape, 54k markets.

Train (markets closed before T0): per wallet, profit per $ in EACH market -> mean, and a t-statistic across markets
(a wallet that won once big is not skilled; one that wins a little in 40 markets is). Skilled: >= MIN_MK markets,
t >= T_SKILL and mean >= 3%. Weak: t <= -T_SKILL and mean <= -3%.
Test (trades after T0): for every trade of a skilled/weak wallet, the market's Yes-price drift 1 h, 6 h, 24 h later
(last print at or before t+h) and the resolution. "Copy" = buy the same side at the price 1 h later + 1c, sell at the
24 h mark - 1c, or hold to resolution. Also: per market-day, net $ flow of skilled minus weak wallets -> next-day drift.
"""
import glob, gzip, json
from datetime import datetime, timezone
import numpy as np

T0 = datetime(2026, 5, 1, tzinfo=timezone.utc).timestamp()
MIN_MK, T_SKILL = 15, 2.0
H = (3600, 6 * 3600, 86400)

winner, close = {}, {}
for f in sorted(glob.glob("data/listing/*.jsonl.gz")):
    for line in gzip.open(f, "rt"):
        m = json.loads(line)
        try:
            pr = json.loads(m.get("outcomePrices") or "[]")
            if len(pr) == 2 and max(float(x) for x in pr) >= 0.99:
                s = (m.get("closedTime") or m.get("endDate") or "").replace("Z", "+00:00")
                if s.endswith("+00"):
                    s += ":00"
                close[int(m["id"])] = datetime.fromisoformat(s).timestamp()
                winner[int(m["id"])] = 0 if float(pr[0]) > float(pr[1]) else 1
        except (ValueError, TypeError, KeyError):
            pass
files = sorted(glob.glob("data/trades/parts/*.jsonl.gz"))


def records():
    for f in files:
        for line in gzip.open(f, "rt"):
            r = json.loads(line); mid = int(r["market_id"])
            if mid not in winner:
                continue
            rows = r["trades"] + r.get("big", [])
            if len(rows) < 2:
                continue
            a = np.unique(np.array(rows, dtype=np.float64), axis=0); a = a[np.argsort(a[:, 0], kind="stable")]
            ts, side, oc, px, sz, wi = a.T
            yes = np.where(oc == 0, px, 1 - px); d = np.where((side == 1) == (oc == 0), 1.0, -1.0); usd = sz * px
            Y = 1.0 if winner[mid] == 0 else 0.0
            pnl = d * (Y - yes) * sz
            yield mid, ts, yes, d, usd, pnl, wi.astype(int), r["wallets"]


# ---- pass 1: per-wallet, per-market profit per $ (train)
wid = {}; per = {}   # wallet idx -> list of (pnl/usd per market, usd)
n_tr = 0
for mid, ts, yes, d, usd, pnl, wi, wl in records():
    if close[mid] >= T0:
        continue
    g = np.array([wid.setdefault(w, len(wid)) for w in wl]); gw = g[wi]
    u, inv = np.unique(gw, return_inverse=True)
    P = np.bincount(inv, pnl, len(u)); U = np.bincount(inv, usd, len(u))
    for w, p_, u_ in zip(u.tolist(), P.tolist(), U.tolist()):
        if u_ >= 5:
            per.setdefault(w, []).append((p_ / u_, u_))
    n_tr += 1
    if n_tr % 5000 == 0:
        print(f"train {n_tr} markets, {len(wid)} wallets", flush=True)
skilled, weak = set(), set(); stats = {}
for w, lst in per.items():
    if len(lst) < MIN_MK:
        continue
    r = np.array([x[0] for x in lst]); m = r.mean(); sd = r.std(ddof=1) if len(r) > 1 else 1.0
    t = m / (sd / np.sqrt(len(r))) if sd > 0 else 0.0
    stats[w] = (len(lst), m, t, sum(x[1] for x in lst))
    if t >= T_SKILL and m >= 0.03:
        skilled.add(w)
    elif t <= -T_SKILL and m <= -0.03:
        weak.add(w)
print(f"train: {n_tr} markets; wallets with >= {MIN_MK} markets: {len(stats)}; skilled {len(skilled)}, weak {len(weak)}", flush=True)
json.dump({"skilled": [[w, *stats[w]] for w in skilled], "weak": [[w, *stats[w]] for w in weak]}, open("data/slow/wallet_sets.json", "w"))

# ---- pass 2: test
agg = {}
def add(key, **kw):
    a = agg.setdefault(key, {})
    for k, v in kw.items():
        a[k] = a.get(k, 0.0) + v
flow_rows = []   # (mid, day, net_skilled_usd, net_weak_usd, total_usd, drift24, Y_minus_price)
n_te = 0
for mid, ts, yes, d, usd, pnl, wi, wl in records():
    if close[mid] < T0:
        continue
    keep = ts >= T0
    if not keep.any():
        continue
    g = np.array([wid.get(w, -1) for w in wl]); gw = g[wi]
    cls = np.zeros(len(ts), int)   # 0 other, 1 skilled, 2 weak
    sk = np.isin(gw, list(skilled)) if skilled else np.zeros(len(ts), bool)
    wk = np.isin(gw, list(weak)) if weak else np.zeros(len(ts), bool)
    cls[sk] = 1; cls[wk] = 2
    marks = {}
    for h in H:
        j = np.searchsorted(ts, ts + h, side="right") - 1
        has = j > np.arange(len(ts))
        marks[h] = (yes[j], has)
    Y = 1.0 if winner[mid] == 0 else 0.0
    for c, name in ((1, "skilled"), (2, "weak"), (0, "other")):
        sel = keep & (cls == c)
        if not sel.any():
            continue
        for sb, lo, hi in (("<50", 0, 50), ("50-500", 50, 500), (">500", 500, 1e12)):
            s2 = sel & (usd >= lo) & (usd < hi)
            if not s2.any():
                continue
            key = (name, sb)
            add(key, n=float(s2.sum()), usd=usd[s2].sum(), pnl=pnl[s2].sum())
            for h in H:
                mk, has = marks[h]; s3 = s2 & has
                add(key, **{f"drift{h}": (d[s3] * (mk[s3] - yes[s3]) * usd[s3]).sum(), f"usd{h}": usd[s3].sum()})
            # copy: enter at the 1 h mark + 1c in the wallet's direction; exit at the 24 h mark - 1c, or resolution
            mk1, has1 = marks[3600]; mk24, has24 = marks[86400]
            s4 = s2 & has1 & has24
            if s4.any():
                entry = np.where(d[s4] > 0, mk1[s4] + 0.01, 1 - mk1[s4] + 0.01)
                exit_ = np.where(d[s4] > 0, mk24[s4] - 0.01, 1 - mk24[s4] - 0.01)
                val = np.where(d[s4] > 0, Y, 1 - Y)
                okp = (entry > 0.02) & (entry < 0.98)
                stake = np.minimum(usd[s4], 20.0)[okp]; sh = stake / entry[okp]
                add(key, copy_stake=stake.sum(), copy_pnl24=(sh * (exit_[okp] - entry[okp])).sum(), copy_pnlres=(sh * (val[okp] - entry[okp])).sum(), copy_n=float(okp.sum()))
    # market-day flow
    if (sk | wk).any():
        day = (ts // 86400).astype(int)
        for dd in np.unique(day[keep]):
            s = keep & (day == dd)
            if not s.any():
                continue
            last_i = np.nonzero(s)[0][-1]
            j = np.searchsorted(ts, ts[last_i] + 86400, side="right") - 1
            if j <= last_i:
                continue
            net_sk = (d[s & sk] * usd[s & sk]).sum(); net_wk = (d[s & wk] * usd[s & wk]).sum()
            flow_rows.append((mid, int(dd), float(net_sk), float(net_wk), float(usd[s].sum()), float(yes[j] - yes[last_i]), float(Y - yes[last_i])))
    n_te += 1
    if n_te % 5000 == 0:
        print(f"test {n_te} markets", flush=True)

print(f"\ntest markets {n_te}\n{'group':8} {'size':7} {'trades':>8} {'$M':>6} {'own pnl/$':>10} {'drift1h':>8} {'drift6h':>8} {'drift24h':>9} | {'copy n':>7} {'copy 24h/$':>10} {'copy res/$':>10}")
for (name, sb), a in sorted(agg.items()):
    u = a.get("usd", 0) or 1
    dr = [a.get(f"drift{h}", 0) / (a.get(f"usd{h}", 0) or 1) for h in H]
    cs = a.get("copy_stake", 0) or 1
    print(f"{name:8} {sb:7} {int(a.get('n', 0)):8} {u / 1e6:6.1f} {a.get('pnl', 0) / u:+10.4f} {dr[0]:+8.4f} {dr[1]:+8.4f} {dr[2]:+9.4f} | {int(a.get('copy_n', 0)):7} {a.get('copy_pnl24', 0) / cs:+10.4f} {a.get('copy_pnlres', 0) / cs:+10.4f}")

# market-day net flow signal
F = np.array(flow_rows) if flow_rows else np.zeros((0, 7))
print(f"\nmarket-days with skilled/weak flow: {len(F)}")
if len(F):
    sig = (F[:, 2] - F[:, 3]) / np.maximum(F[:, 4], 1)      # (net skilled - net weak) as a share of the day's volume
    for lo, hi in ((-1.01, -0.5), (-0.5, -0.1), (-0.1, 0.1), (0.1, 0.5), (0.5, 1.01)):
        s = (sig >= lo) & (sig < hi)
        if s.sum() >= 50:
            print(f"  net skilled flow {lo:+.1f}..{hi:+.1f} of volume: market-days {s.sum():6}  next-24h drift of Yes {F[s, 5].mean():+.4f}  Yes resolution minus price {F[s, 6].mean():+.4f}")
json.dump({"agg": {f"{k[0]}|{k[1]}": v for k, v in agg.items()}, "n_test": n_te}, open("data/slow/copy_trade.json", "w"))
