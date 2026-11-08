"""Slow strategy #3: two-sided market-making in long-dated markets, filtered by who is trading there.
Replay on the random trade tape (54k markets). Pass 1 (markets closed before T0) classifies wallets as skilled /
weak (t-statistic across >= 15 markets, as in copy_trade.py) and SAVES THEIR ADDRESSES. Pass 2 (trades after T0):

  quotes: bid = last Yes print - S, ask = last Yes print + S, $SIZE a side, re-centred on every print
  fills : a Yes-sell print strictly below our bid fills the bid at our price; a Yes-buy print strictly above our
          ask fills the ask (we sell Yes = buy No). Inventory capped at +-CAP shares; the side that would exceed
          it is not quoted. No quoting in the last 24 h before the market closes.
  P&L   : cash from fills + inventory valued at resolution. Makers pay no fee.
  flow  : for every fill, the counterparty's class (skilled / weak / other), and the market's trailing-7-day
          "weak share" of volume (share of $ from weak wallets minus share from skilled) at that moment,
          which is what a live bot could compute to choose markets.
Output: tables of maker P&L per $ of fills by counterparty class and by the market's flow score.
"""
import glob, gzip, json, os
from collections import defaultdict
from datetime import datetime, timezone
import numpy as np

T0 = datetime(2026, 5, 1, tzinfo=timezone.utc).timestamp()
MIN_MK, T_SKILL = 15, 2.0
S = float(os.environ.get("S", "0.02")); SIZE = float(os.environ.get("SIZE", "20")); CAP = float(os.environ.get("CAP", "100"))
os.makedirs("data/slow", exist_ok=True)

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
            yield mid, ts, yes, d, usd, sz, wi.astype(int), r["wallets"], bool(r.get("truncated"))


# ---- pass 1: wallet classes (cached by address)
cache = "data/slow/wallet_sets.json"
try:
    ws = json.load(open(cache)); skilled, weak = set(ws["skilled_addr"]), set(ws["weak_addr"])
    print(f"wallet classes from cache: skilled {len(skilled)} weak {len(weak)}", flush=True)
except (OSError, KeyError, ValueError):
    per = defaultdict(list); n_tr = 0
    for mid, ts, yes, d, usd, sz, wi, wl, tr in records():
        if close[mid] >= T0:
            continue
        Y = 1.0 if winner[mid] == 0 else 0.0
        pnl = d * (Y - yes) * sz
        u, inv = np.unique(wi, return_inverse=True)
        P = np.bincount(inv, pnl, len(u)); U = np.bincount(inv, usd, len(u))
        for k, p_, u_ in zip(u.tolist(), P.tolist(), U.tolist()):
            if u_ >= 5:
                per[wl[k]].append(p_ / u_)
        n_tr += 1
        if n_tr % 5000 == 0:
            print(f"train {n_tr}", flush=True)
    skilled, weak = set(), set()
    for w, r in per.items():
        if len(r) < MIN_MK:
            continue
        r = np.array(r); m = r.mean(); sd = r.std(ddof=1)
        t = m / (sd / np.sqrt(len(r))) if sd > 0 else 0.0
        if t >= T_SKILL and m >= 0.03:
            skilled.add(w)
        elif t <= -T_SKILL and m <= -0.03:
            weak.add(w)
    json.dump({"skilled_addr": sorted(skilled), "weak_addr": sorted(weak)}, open(cache, "w"))
    print(f"train {n_tr} markets: skilled {len(skilled)} weak {len(weak)}", flush=True)

# ---- pass 2: maker replay
fills = []   # (class, flow_score, edge_per_share, shares, usd, mid, dtc)
n_te = 0; mk_pnl = []
for mid, ts, yes, d, usd, sz, wi, wl, tr in records():
    if close[mid] < T0 or tr:
        continue
    if not (ts >= T0).any():
        continue
    Y = 1.0 if winner[mid] == 0 else 0.0
    cls = np.array([1 if wl[k] in skilled else 2 if wl[k] in weak else 0 for k in wi])
    # trailing-7-day flow score at each print: (weak $ - skilled $) / total $ over the previous 7 days (excluding this print)
    cum_w = np.concatenate([[0.0], np.cumsum(np.where(cls == 2, usd, 0.0))]); cum_s = np.concatenate([[0.0], np.cumsum(np.where(cls == 1, usd, 0.0))]); cum_t = np.concatenate([[0.0], np.cumsum(usd)])
    i0 = np.searchsorted(ts, ts - 7 * 86400, side="left"); i1 = np.arange(len(ts))
    tot7 = cum_t[i1] - cum_t[i0]
    with np.errstate(invalid="ignore", divide="ignore"):
        score = np.where(tot7 >= 500, ((cum_w[i1] - cum_w[i0]) - (cum_s[i1] - cum_s[i0])) / tot7, np.nan)
    inv = 0.0; cash = 0.0; this = []
    prev = np.concatenate([[np.nan], yes[:-1]])
    bid_ = prev - S; ask_ = prev + S
    dtc_s = close[mid] - ts
    cand = np.nonzero((ts >= T0) & (dtc_s >= 86400) & (((d < 0) & (yes < bid_ - 1e-9) & (bid_ >= 0.02) & (bid_ <= 0.98)) |
                                                     ((d > 0) & (yes > ask_ + 1e-9) & (ask_ >= 0.02) & (ask_ <= 0.98))))[0]
    for i in cand:
        t, p, dd, u, q = ts[i], yes[i], d[i], usd[i], sz[i]
        bid, ask = bid_[i], ask_[i]
        if dd < 0 and inv < CAP:            # seller hit our bid: we buy Yes at bid
            sh = min(q, SIZE / bid); inv += sh; cash -= sh * bid
            this.append((cls[i], score[i], Y - bid, sh, sh * bid, dtc_s[i] / 86400))
        elif dd > 0 and inv > -CAP:         # buyer lifted our ask: we sell Yes at ask
            sh = min(q, SIZE / (1 - ask)); inv -= sh; cash += sh * ask
            this.append((cls[i], score[i], ask - Y, sh, sh * (1 - ask), dtc_s[i] / 86400))
    if this:
        pnl = cash + inv * Y
        mk_pnl.append((mid, pnl, sum(x[4] for x in this), np.nanmean([x[1] for x in this]) if any(not np.isnan(x[1]) for x in this) else np.nan))
        fills += [(mid, *x) for x in this]
    n_te += 1
    if n_te % 5000 == 0:
        print(f"test {n_te} markets, fills {len(fills)}", flush=True)
json.dump({"fills": [[int(a), int(b), None if np.isnan(c) else round(float(c), 4), round(float(e), 4), round(float(sh), 3), round(float(u), 2), round(float(dt), 2)] for a, b, c, e, sh, u, dt in fills],
           "markets": [[int(a), round(float(b), 2), round(float(c), 2), None if np.isnan(dd) else round(float(dd), 3)] for a, b, c, dd in mk_pnl]}, open("data/slow/mm_flow.json", "w"))

print(f"\nMAKER REPLAY: spread {S:.2f} each side, ${SIZE:.0f} a side, test markets {n_te}, markets with fills {len(mk_pnl)}, fills {len(fills)}")
tot = sum(p for _, p, _, _ in mk_pnl); vol = sum(v for _, _, v, _ in mk_pnl)
print(f"  total P&L ${tot:,.0f} on ${vol:,.0f} of fills = {tot / vol:+.3%} per $ filled; markets positive {sum(p > 0 for _, p, _, _ in mk_pnl) / len(mk_pnl):.0%}")
def edge(sel, label):
    if not sel:
        return
    u = sum(x[5] for x in sel); e = sum(x[3] * x[4] for x in sel)
    print(f"  {label:42} fills {len(sel):7}  ${u:10,.0f}  edge vs resolution {e / u:+.4f} per $")
print("\nby counterparty (who hit our quote):")
for c, lab in ((1, "skilled wallet"), (2, "weak wallet"), (0, "other")):
    edge([x for x in fills if x[1] == c], lab)
print("\nby the market's trailing-7-day flow score (weak share minus skilled share of $ volume):")
for lo, hi in ((-1.01, -0.3), (-0.3, -0.1), (-0.1, 0.1), (0.1, 0.3), (0.3, 1.01)):
    edge([x for x in fills if x[2] is not None and not np.isnan(x[2]) and lo <= x[2] < hi], f"score {lo:+.1f}..{hi:+.1f}")
edge([x for x in fills if x[2] is None or np.isnan(x[2])], "no score (thin market)")
print("\nby days to close:")
for lo, hi in ((1, 3), (3, 7), (7, 30), (30, 1e9)):
    edge([x for x in fills if lo <= x[6] < hi], f"{lo}-{hi} days")
print("\nby price level of the fill (Yes terms):")
for lo, hi in ((0.02, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 0.98)):
    edge([x for x in fills if lo <= (x[5] / x[4] if x[3] <= 1 else 0) < hi], f"cost {lo:.1f}-{hi:.1f}")
