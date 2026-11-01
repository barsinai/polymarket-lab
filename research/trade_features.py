"""Trade-based features for the rows of derived/rows.npz whose market is in the trades sample.

Everything is computed from trades strictly BEFORE the row's moment t:
  log_usd_so_far      money traded in the market so far (log $)
  log_trades_24h      number of trades in the last 24h (log)
  log_usd_24h         money traded in the last 24h (log $)
  flow_24h            net money pushing toward the first side in the last 24h, as a share
                      of all money traded then (-1..1): buys of side 0 + sells of side 1
                      minus buys of side 1 + sells of side 0
  big_flow_24h        same, only trades of $500+
  log_wallets_so_far  distinct wallets that traded so far (log)
  smart_flow_7d       last 7 days' net flow weighted by each wallet's track record: its
                      profit per $ on markets that had ALREADY ENDED before t (no peeking)
  smart_wallets_7d    how many wallets with a good record (>=5 ended markets, profit>0) traded
Output: derived/trade_feats.npz with row indices and the feature matrix.
"""
import glob
import gzip
import json

import numpy as np

TF = ["log_usd_so_far", "log_trades_24h", "log_usd_24h", "flow_24h", "big_flow_24h",
      "log_wallets_so_far", "smart_flow_7d", "smart_wallets_7d"]
DAY = 86400


def main():
    d = np.load("derived/rows.npz")
    info, X, y, feats = d["info"], d["X"], d["y"], list(d["feats"])
    MID, T = info[:, 0].astype(int), info[:, 2]
    OUT = y + X[:, feats.index("p")]

    # market outcome + close time (needed for wallet track records); from the listing
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
                from datetime import datetime
                s = ct.replace(" ", "T").replace("Z", "+00:00")
                if s.endswith("+00"):
                    s += ":00"
                try:
                    close[int(m["id"])] = datetime.fromisoformat(s).timestamp()
                    winner[int(m["id"])] = 0 if pr[0] > pr[1] else 1
                except ValueError:
                    pass

    # one pass over the trade files: keep trades only for markets that have rows, and turn
    # every resolved market into compact (wallet, close time, profit, money spent) records
    need = set(MID.tolist())
    trades, wid = {}, {}
    rw, rc, rp, rs = [], [], [], []
    for f in glob.glob("data/trades/parts/*.jsonl.gz"):
        for line in gzip.open(f, "rt"):
            r = json.loads(line)
            rows = r["trades"] + r.get("big", [])
            if not rows:
                continue
            mid = int(r["market_id"])
            gmap = np.array([wid.setdefault(w, len(wid)) for w in r["wallets"]], dtype=np.int64)
            a = np.unique(np.array(rows, dtype=np.float64), axis=0)  # "big" can repeat rows
            a[:, 5] = gmap[a[:, 5].astype(int)]
            a = a[np.argsort(a[:, 0])]
            if mid in winner:
                signed = np.where(a[:, 1] == 1, 1.0, -1.0)
                payout = (a[:, 2] == winner[mid]).astype(float)
                pnl = signed * a[:, 4] * (payout - a[:, 3])
                spent = np.where(a[:, 1] == 1, a[:, 4] * a[:, 3], 0.0)
                u, inv = np.unique(a[:, 5].astype(np.int64), return_inverse=True)
                rw.append(u); rc.append(np.full(len(u), close[mid]))
                rp.append(np.bincount(inv, pnl, len(u))); rs.append(np.bincount(inv, spent, len(u)))
            if mid in need:
                trades[mid] = a.astype(np.float64)
    print(f"{len(trades)} markets with rows+trades, {len(wid)} wallets", flush=True)
    del wid
    rw, rc, rp, rs = (np.concatenate(v) for v in (rw, rc, rp, rs))
    o = np.lexsort((rc, rw))
    rw, rc, rp, rs = rw[o], rc[o], rp[o], rs[o]
    starts = np.r_[0, np.flatnonzero(np.diff(rw)) + 1]
    wallets_u = rw[starts]
    # cumulative profit / spend within each wallet's run of records
    cp, cs = np.cumsum(rp), np.cumsum(rs)
    base_p = np.repeat(np.r_[0, cp[starts[1:] - 1]], np.diff(np.r_[starts, len(rw)]))
    base_s = np.repeat(np.r_[0, cs[starts[1:] - 1]], np.diff(np.r_[starts, len(rw)]))
    cp, cs = cp - base_p, cs - base_s
    pos = np.searchsorted(wallets_u, np.arange(0))  # placeholder to keep numpy happy

    def skill(wv, t):
        """wallet's profit per $ over markets that ended before t, and how many."""
        k = np.searchsorted(wallets_u, wv)
        if k >= len(wallets_u) or wallets_u[k] != wv:
            return 0.0, 0
        a0 = starts[k]
        a1 = starts[k + 1] if k + 1 < len(starts) else len(rw)
        j = a0 + np.searchsorted(rc[a0:a1], t) - 1
        if j < a0 or cs[j] <= 0:
            return 0.0, 0
        return float(np.clip(cp[j] / cs[j], -1, 3)), int(j - a0 + 1)

    idx = np.where(np.isin(MID, list(trades)))[0]
    F = np.zeros((len(idx), len(TF)), dtype=np.float32)
    for k, i in enumerate(idx):
        a, t = trades[MID[i]], T[i]
        before = a[a[:, 0] < t]
        usd = before[:, 3] * before[:, 4]
        to0 = np.where(((before[:, 1] == 1) & (before[:, 2] == 0)) | ((before[:, 1] == 0) & (before[:, 2] == 1)), 1, -1)
        d1 = before[:, 0] >= t - DAY
        d7 = before[:, 0] >= t - 7 * DAY
        big = d1 & (usd >= 500)
        tot1 = usd[d1].sum()
        smart, nsmart = 0.0, set()
        for row, u, s in zip(before[d7], usd[d7], to0[d7]):
            sk, n = skill(int(row[5]), t)
            if n >= 5:
                smart += sk * u * s
                if sk > 0:
                    nsmart.add(int(row[5]))
        tot7 = usd[d7].sum()
        F[k] = [np.log1p(usd.sum()), np.log1p(d1.sum()), np.log1p(tot1),
                (usd[d1] * to0[d1]).sum() / tot1 if tot1 > 0 else 0.0,
                (usd[big] * to0[big]).sum() / max(usd[big].sum(), 1e-9) if big.any() else 0.0,
                np.log1p(len(np.unique(before[:, 5]))), smart / tot7 if tot7 > 0 else 0.0, len(nsmart)]
        if k % 5000 == 0:
            print(f"  {k}/{len(idx)} rows", flush=True)
    np.savez_compressed("derived/trade_feats.npz", idx=idx, F=F, names=np.array(TF))
    print(f"saved trade features for {len(idx)} rows")


if __name__ == "__main__":
    main()
