"""Wallet track records for the market maker: profit per $ on the final outcome over all
resolved markets in the trades sample that closed before CUTOFF (default 2026-10-31, the start
of the live recording, so a replay over the recording has no lookahead).
Output: data/replay_mm/wallet_scores.json.gz  {"cutoff", "edges": decile edges, "wallets": {addr: [score, n, usd]}}
Only wallets with >= 10 trades and >= $500 traded are kept (~90k).
"""
import glob, gzip, json, os, sys
from datetime import datetime
import numpy as np

CUTOFF = datetime.fromisoformat(os.environ.get("CUTOFF", "2026-10-31")).timestamp()
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
wid = {}
P = np.zeros(0); U = np.zeros(0); N = np.zeros(0)
n_m = 0
for f in sorted(glob.glob("data/trades/parts/*.jsonl.gz")):
    for line in gzip.open(f, "rt"):
        r = json.loads(line)
        mid = int(r["market_id"])
        if mid not in winner or close[mid] >= CUTOFF:
            continue
        rows = r["trades"] + r.get("big", [])
        if len(rows) < 2:
            continue
        a = np.unique(np.array(rows, dtype=np.float64), axis=0)
        ts, side, oc, px, sz, wi = a.T
        yes_px = np.where(oc == 0, px, 1 - px)
        d = np.where((side == 1) == (oc == 0), 1.0, -1.0)
        Y = 1.0 if winner[mid] == 0 else 0.0
        pnl = d * (Y - yes_px) * sz; usd = sz * px
        g = np.array([wid.setdefault(w, len(wid)) for w in r["wallets"]])
        gw = g[wi.astype(int)]
        need = len(wid) - len(P)
        if need > 0:
            P = np.concatenate([P, np.zeros(need + 200000)]); U = np.concatenate([U, np.zeros(need + 200000)]); N = np.concatenate([N, np.zeros(need + 200000)])
        u, inv = np.unique(gw, return_inverse=True)
        P[u] += np.bincount(inv, pnl, len(u)); U[u] += np.bincount(inv, usd, len(u)); N[u] += np.bincount(inv, None, len(u))
        n_m += 1
        if n_m % 5000 == 0:
            print(n_m, "markets", len(wid), "wallets", flush=True)
P, U, N = P[:len(wid)], U[:len(wid)], N[:len(wid)]
ok = (N >= 10) & (U >= 500)
score = P[ok] / U[ok]
edges = np.percentile(score, np.arange(10, 100, 10)).round(4).tolist()
addrs = np.array(list(wid.keys()))[ok]
out = {"cutoff": datetime.fromtimestamp(CUTOFF).date().isoformat(), "markets": n_m, "edges": edges,
       "wallets": {str(a): [round(float(s), 4), int(n), round(float(u))] for a, s, n, u in zip(addrs, score, N[ok], U[ok])}}
os.makedirs("data/replay_mm", exist_ok=True)
with gzip.open("data/replay_mm/wallet_scores.json.gz", "wt") as fh:
    json.dump(out, fh, separators=(",", ":"))
print(f"{n_m} markets, {ok.sum()} scored wallets, decile edges {edges}")
