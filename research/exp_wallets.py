"""Do individual wallets have persistent skill? (random sample of ~54k markets, all their trades)

Two uses if yes:  (a) market-maker protection - lean/pull quotes when a wallet with a good
record trades against us;  (b) copy-trading - follow good wallets as a taker if their edge
beats the taker fee.

Pass 1 (train): markets that CLOSED before T0. Per wallet: profit per $ on the final outcome.
Pass 2 (test):  trades AFTER T0 in markets closing after T0. Group each trade by its wallet's
train decile (unknown = no record) and measure, out of sample:
  - profit per $ on the final outcome              (does skill persist?)
  - drift of the Yes price 1h and 24h after the trade, in the trade's direction
    (what a market maker eats when filled by this wallet)
Also: persistence correlation of per-wallet profit/$ between train and test.
Direction d=+1 means the wallet bought Yes (BUY outcome 0 or SELL outcome 1).
Output: results/exp_wallets.json
"""
import glob, gzip, json, sys
from datetime import datetime
import numpy as np

T0 = datetime(2026, 5, 1).timestamp()
MIN_N, MIN_USD = 10, 500.0
H = [3600, 86400]

close, winner = {}, {}
for f in glob.glob("data/listing/*.gz"):
    for line in gzip.open(f, "rt"):
        m = json.loads(line)
        try:
            pr = [float(x) for x in json.loads(m.get("outcomePrices") or "[]")]
        except (ValueError, TypeError):
            continue
        ct = m.get("closedTime") or m.get("endDate")
        if len(pr) == 2 and max(pr) >= 0.99 and ct:
            s = ct.replace(" ", "T").replace("Z", "+00:00")
            if s.endswith("+00"):
                s += ":00"
            try:
                close[int(m["id"])] = datetime.fromisoformat(s).timestamp()
                winner[int(m["id"])] = 0 if pr[0] > pr[1] else 1
            except ValueError:
                pass
print(f"{len(winner)} resolved markets in listing", flush=True)
files = sorted(glob.glob("data/trades/parts/*.jsonl.gz"))


def records():
    for f in files:
        for line in gzip.open(f, "rt"):
            r = json.loads(line)
            mid = int(r["market_id"])
            if mid not in winner:
                continue
            rows = r["trades"] + r.get("big", [])
            if len(rows) < 2:
                continue
            a = np.unique(np.array(rows, dtype=np.float64), axis=0)
            a = a[np.argsort(a[:, 0], kind="stable")]
            ts, side, oc, px, sz, wi = a.T
            yes_px = np.where(oc == 0, px, 1 - px)
            d = np.where((side == 1) == (oc == 0), 1.0, -1.0)
            usd = sz * px
            Y = 1.0 if winner[mid] == 0 else 0.0
            pnl = d * (Y - yes_px) * sz          # $ profit per trade on the final outcome
            yield mid, ts, yes_px, d, usd, pnl, wi, r["wallets"]


# ---- pass 1: train record per wallet
wid = {}
tr_p, tr_u, tr_n = np.zeros(0), np.zeros(0), np.zeros(0)
n_tr = 0
for mid, ts, yes_px, d, usd, pnl, wi, wl in records():
    if close[mid] >= T0:
        continue
    g = np.array([wid.setdefault(w, len(wid)) for w in wl])
    gw = g[wi.astype(int)]
    need = len(wid) - len(tr_p)
    if need > 0:
        tr_p = np.concatenate([tr_p, np.zeros(need + 100000)]); tr_u = np.concatenate([tr_u, np.zeros(need + 100000)]); tr_n = np.concatenate([tr_n, np.zeros(need + 100000)])
    u, inv = np.unique(gw, return_inverse=True)
    for arr, v in ((tr_p, pnl), (tr_u, usd), (tr_n, np.ones(len(gw)))):
        arr[u] += np.bincount(inv, v, len(u))
    n_tr += 1
    if n_tr % 5000 == 0:
        print(f"train {n_tr} markets, {len(wid)} wallets", flush=True)
tr_p, tr_u, tr_n = tr_p[:len(wid)], tr_u[:len(wid)], tr_n[:len(wid)]
ok = (tr_n >= MIN_N) & (tr_u >= MIN_USD)
score = np.full(len(tr_p), np.nan); score[ok] = tr_p[ok] / tr_u[ok]
edges = np.nanpercentile(score, np.arange(10, 100, 10))
dec = np.full(len(tr_p), -1, int); dec[ok] = np.searchsorted(edges, score[ok])
print(f"train: {n_tr} markets, {len(wid)} wallets, {ok.sum()} with record; decile edges {np.round(edges, 3).tolist()}", flush=True)

# ---- pass 2: test
K = len(H)
agg = {k: np.zeros(11) for k in ("n", "usd", "pnl", *[f"drift{h}" for h in H], *[f"usd_d{h}" for h in H])}
te_p, te_u = {}, {}
n_te = 0
for mid, ts, yes_px, d, usd, pnl, wi, wl in records():
    if close[mid] < T0:
        continue
    keep = ts >= T0
    if not keep.any():
        continue
    g = np.array([wid.get(w, -1) for w in wl])
    gw = g[wi.astype(int)]
    dw = np.where(gw >= 0, dec[np.maximum(gw, 0)], -1)
    # marks h later: last trade's Yes price at or before t+h (if no later trade, mark = own price)
    drifts = []
    for h in H:
        j = np.searchsorted(ts, ts + h, side="right") - 1
        mark = yes_px[j]
        drifts.append(d * (mark - yes_px))
    idx = dw + 1  # -1 -> bucket 0 (unknown), deciles -> 1..10
    for name, v in (("n", np.ones(len(ts))), ("usd", usd), ("pnl", pnl)):
        agg[name] += np.bincount(idx[keep], v[keep], 11)
    for h, dr in zip(H, drifts):
        # drift measured only where a later trade exists within the market
        has = (np.searchsorted(ts, ts + h, side="right") - 1) > np.arange(len(ts))
        kk = keep & has
        agg[f"drift{h}"] += np.bincount(idx[kk], (dr * usd)[kk], 11)
        agg[f"usd_d{h}"] += np.bincount(idx[kk], usd[kk], 11)
    kk = keep & (gw >= 0)
    if kk.any():
        u, inv = np.unique(gw[kk], return_inverse=True)
        for w, p_, u_ in zip(u.tolist(), np.bincount(inv, pnl[kk], len(u)).tolist(), np.bincount(inv, usd[kk], len(u)).tolist()):
            te_p[w] = te_p.get(w, 0.0) + p_; te_u[w] = te_u.get(w, 0.0) + u_
    n_te += 1
    if n_te % 5000 == 0:
        print(f"test {n_te} markets", flush=True)

labels = ["no record"] + [f"decile {i}" for i in range(1, 11)]
out = {"T0": "2026-05-01", "train_markets": n_tr, "test_markets": n_te, "wallets_with_record": int(ok.sum()),
       "decile_edges_profit_per_usd": np.round(edges, 4).tolist(), "by_decile": {}}
print(f"\n{'bucket':10} {'trades':>9} {'usd($M)':>8} {'pnl/$':>8} {'drift1h/$':>10} {'drift24h/$':>11}")
for i, lab in enumerate(labels):
    n, u, p = agg["n"][i], agg["usd"][i], agg["pnl"][i]
    r = {"trades": int(n), "usd": round(u), "profit_per_usd": round(p / u, 4) if u else None}
    for h in H:
        ud = agg[f"usd_d{h}"][i]
        r[f"drift_{h}s_per_usd"] = round(agg[f"drift{h}"][i] / ud, 4) if ud else None
    out["by_decile"][lab] = r
    print(f"{lab:10} {int(n):9d} {u/1e6:8.2f} {r['profit_per_usd'] if r['profit_per_usd'] is not None else float('nan'):+8.4f} "
          f"{r['drift_3600s_per_usd'] if r['drift_3600s_per_usd'] is not None else float('nan'):+10.4f} "
          f"{r['drift_86400s_per_usd'] if r['drift_86400s_per_usd'] is not None else float('nan'):+11.4f}")
# persistence: wallets with record in train and >= $500 in test
ws = [w for w in te_p if ok[w] and te_u[w] >= MIN_USD]
if len(ws) > 50:
    a_ = np.array([score[w] for w in ws]); b_ = np.array([te_p[w] / te_u[w] for w in ws])
    a_ = np.clip(a_, -1, 1); b_ = np.clip(b_, -1, 1)
    out["persistence"] = {"wallets": len(ws), "pearson": round(float(np.corrcoef(a_, b_)[0, 1]), 4),
                          "spearman": round(float(np.corrcoef(a_.argsort().argsort(), b_.argsort().argsort())[0, 1]), 4)}
    print("persistence", out["persistence"])
json.dump(out, open("results/exp_wallets.json", "w"), indent=1)
