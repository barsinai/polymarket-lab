"""Big sparse ridge: thousands of weak features -> how wrong is the price?

Target: won - price (first side), one row per (market, moment) from derived/rows.npz.
Features (all known at the moment of the bet):
  * the ~40 numeric price/time/type features of model.py (standardised)
  * price band (12) x horizon (7) one-hots, price band x category, price band x deadline
  * question words (top-K by training frequency) and words x price band (sparse)
  * market age band, day of week, hour of day, event-size band, neg-risk x band
  * sibling features: sum of sibling prices in the same event at the same horizon, #siblings
Fit on rows before 2026-05-01; alpha chosen on Jun-Aug; Sep-Oct reported once (lockbox).
Judged on FAIR rows (>= $5k traded before the bet; see fair.py) as well as all rows.
Also fits a model on fair training rows only. Reports correlation, 'won minus price' for
rows the model flags, and profit at typical costs - plus the number that matters for the
market maker: how much the model's lean would have been worth per share.
Usage: python research/bigridge.py [--words 3000]
"""
import argparse, glob, gzip, json, os, re, sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
import numpy as np
import scipy.sparse as sp
from sklearn.linear_model import Ridge
sys.path.insert(0, "research")
from fair import fair_mask  # noqa: E402

ap = argparse.ArgumentParser(); ap.add_argument("--words", type=int, default=3000); ap.add_argument("--alphas", default="300,1000,3000,10000,30000")
a = ap.parse_args()
D = np.load("derived/rows.npz")
X, y, info, F = D["X"], D["y"], D["info"], list(D["feats"])
MID, EV, T, DAYS, VOL = info.T
P = X[:, F.index("p")]; OUT = y + P
n = len(y)
day = lambda s: datetime.fromisoformat(s).replace(tzinfo=timezone.utc).timestamp()  # noqa: E731
TR = T < day("2026-05-01"); seen = np.isin(EV, np.unique(EV[TR]))
VA = (T >= day("2026-06-01")) & (T < day("2026-09-01")) & ~seen
LB = (T >= day("2026-09-01")) & ~seen & ~np.isin(EV, np.unique(EV[VA]))
FAIR, KNOWN, USD = fair_mask(MID, DAYS, 5000)
ACTIVE = (X[:, F.index("n_moves_7d")] >= 10) & (X[:, F.index("at_half")] == 0)
print(f"rows {n}: train {TR.sum()} val {VA.sum()} lockbox {LB.sum()}; fair {FAIR.sum()} (train {(TR&FAIR).sum()}, val {(VA&FAIR).sum()}, lb {(LB&FAIR).sum()})", flush=True)

# ---- questions and start dates
need = set(MID.astype(int)); Q, START = {}, {}
for f in glob.glob("data/listing/*.gz"):
    for l in gzip.open(f, "rt"):
        i = l.find('"id":"'); mid = int(l[i + 6:l.index('"', i + 6)])
        if mid in need:
            m = json.loads(l); Q[mid] = (m.get("question") or "").lower()
            try:
                START[mid] = datetime.fromisoformat(m["startDate"].replace("Z", "+00:00")).timestamp()
            except (KeyError, ValueError, AttributeError, TypeError):
                pass
qs = [Q.get(int(m), "") for m in MID]
print("questions loaded", flush=True)

# ---- building blocks
def onehot(codes, k):
    codes = np.asarray(codes); ok = (codes >= 0) & (codes < k)
    return sp.csr_matrix((np.ones(ok.sum(), np.float32), (np.where(ok)[0], codes[ok])), shape=(n, k))


def cross(A, B):
    """row-wise outer product of two one-hot/sparse matrices"""
    A = A.tocsr(); B = B.tocsr(); kb = B.shape[1]
    rows, cols, vals = [], [], []
    for i in range(n):
        ai = A.indices[A.indptr[i]:A.indptr[i + 1]]; bi = B.indices[B.indptr[i]:B.indptr[i + 1]]
        if len(ai) and len(bi):
            for aa in ai:
                rows.append(np.full(len(bi), i)); cols.append(aa * kb + bi); vals.append(B.data[B.indptr[i]:B.indptr[i + 1]])
    if not rows:
        return sp.csr_matrix((n, A.shape[1] * kb), dtype=np.float32)
    return sp.csr_matrix((np.concatenate(vals).astype(np.float32), (np.concatenate(rows), np.concatenate(cols))), shape=(n, A.shape[1] * kb))


band_edges = [0, .05, .1, .2, .3, .4, .5, .6, .7, .8, .9, .95, 1.01]
band = np.digitize(P, band_edges) - 1; B_band = onehot(band, 12)
B_hz = onehot(np.searchsorted([1, 2, 3, 5, 7, 14, 30], DAYS), 7)
cats = [c for c in F if c.startswith("cat_")]
B_cat = onehot(np.argmax(X[:, [F.index(c) for c in cats]], axis=1), len(cats))
B_dead = onehot(X[:, F.index("deadline")].astype(int), 2)
B_neg = onehot(X[:, F.index("neg_risk")].astype(int), 2)
age = np.array([(T[i] - START.get(int(MID[i]), T[i])) / 86400 for i in range(n)])
B_age = onehot(np.searchsorted([1, 3, 7, 30, 90], age), 6)
dt = np.array([datetime.fromtimestamp(t, timezone.utc) for t in T])
B_dow = onehot([d.weekday() for d in dt], 7); B_hour = onehot([d.hour for d in dt], 24)
evsize = X[:, F.index("log_event_size")]; B_ev = onehot(np.searchsorted([0.1, 1.2, 2.0, 3.0], evsize), 5)
# sibling features: sum of sibling P at the same (event, horizon) slot
key = EV.astype(np.int64) * 100 + DAYS.astype(np.int64)
sums = defaultdict(float); cnt = defaultdict(int)
for k_, p_ in zip(key, P):
    sums[k_] += p_; cnt[k_] += 1
sib_sum = np.array([sums[k_] - p_ for k_, p_ in zip(key, P)], np.float32); sib_n = np.array([cnt[k_] - 1 for k_ in key], np.float32)
# words (vocabulary from training rows only)
tok = re.compile(r"[a-z][a-z'\-]{1,}")
wc = Counter()
for i in np.where(TR)[0]:
    wc.update(set(tok.findall(qs[i])))
vocab = {w: j for j, (w, c) in enumerate(wc.most_common(a.words)) if c >= 30}
rows_, cols_ = [], []
for i, q in enumerate(qs):
    ids = {vocab[w] for w in set(tok.findall(q)) if w in vocab}
    rows_.extend([i] * len(ids)); cols_.extend(ids)
B_words = sp.csr_matrix((np.ones(len(rows_), np.float32), (rows_, cols_)), shape=(n, len(vocab)))
print(f"vocab {len(vocab)} words; building crosses", flush=True)
num = np.column_stack([X, sib_sum, sib_n, age]).astype(np.float32)
mu, sd = num[TR].mean(0), num[TR].std(0) + 1e-9
NUM = sp.csr_matrix((num - mu) / sd)
blocks = {"numeric": NUM, "band": B_band, "band x horizon": cross(B_band, B_hz), "band x category": cross(B_band, B_cat),
          "band x deadline": cross(B_band, B_dead), "band x negrisk": cross(B_band, B_neg), "age": B_age, "dow": B_dow, "hour": B_hour,
          "event size": B_ev, "words": B_words, "words x band": cross(B_words, B_band)}
XX = sp.hstack(list(blocks.values()), format="csr", dtype=np.float32)
print(f"design matrix: {XX.shape[0]} x {XX.shape[1]}, nnz {XX.nnz}", flush=True)
RNG = np.random.default_rng(3)


def ci(v, ev):
    u, inv = np.unique(ev, return_inverse=True)
    s, c = np.bincount(inv, v, len(u)), np.bincount(inv, None, len(u))
    idx = RNG.integers(0, len(u), (300, len(u))); b = s[idx].sum(1) / c[idx].sum(1)
    return round(float(v.mean()), 4), round(float(np.percentile(b, 2.5)), 4), round(float(np.percentile(b, 97.5)), 4)


def evaluate(pred, mask, label):
    out = {}
    m = mask
    if m.sum() < 100:
        return None
    out["rows"] = int(m.sum()); out["corr"] = round(float(np.corrcoef(pred[m], y[m])[0, 1]), 4)
    for thr in (0.02, 0.04):
        sel = m & (np.abs(pred) > thr)
        if sel.sum() < 50:
            continue
        side = np.sign(pred[sel]); price = np.where(side > 0, P[sel], 1 - P[sel]); won = np.where(side > 0, OUT[sel], 1 - OUT[sel])
        out[f"lean>{int(thr*100)}c"] = {"bets": int(sel.sum()), "won_minus_price_c": [round(100 * v, 2) for v in ci(won - price, EV[sel])],
                                       "profit_per_$_at_2c_cost": ci(won / np.clip(price + 0.02, 0, .999) - 1, EV[sel])}
    print(f"  {label:34} rows={out['rows']:7} corr {out['corr']:+.4f} " + " ".join(f"| lean>{k[-2:]} n={v['bets']} wmp {v['won_minus_price_c'][0]:+.2f}c ({v['won_minus_price_c'][1]:+.2f},{v['won_minus_price_c'][2]:+.2f})" for k, v in out.items() if k.startswith("lean")), flush=True)
    return out


res = {"design": {k: int(v.shape[1]) for k, v in blocks.items()}, "n": int(n)}
for train_name, trm in (("trained on all training rows", TR), ("trained on FAIR training rows only", TR & FAIR)):
    if trm.sum() < 3000:
        print(f"{train_name}: too few rows ({trm.sum()})"); continue
    best = None
    for alpha in [float(x) for x in a.alphas.split(",")]:
        mdl = Ridge(alpha=alpha, solver="sparse_cg", max_iter=2000, tol=1e-4).fit(XX[trm], y[trm])
        pred = mdl.predict(XX)
        c = float(np.corrcoef(pred[VA & FAIR], y[VA & FAIR])[0, 1]) if (VA & FAIR).sum() > 100 else float(np.corrcoef(pred[VA], y[VA])[0, 1])
        print(f"{train_name} alpha={alpha:g}: val corr (fair) {c:+.4f}", flush=True)
        if best is None or c > best[0]:
            best = (c, alpha, pred, mdl)
    c, alpha, pred, mdl = best
    print(f"== {train_name}: alpha {alpha:g}")
    r = {"alpha": alpha}
    r["validation fair"] = evaluate(pred, VA & FAIR & ACTIVE, "validation (fair, active)")
    r["validation all"] = evaluate(pred, VA & ACTIVE, "validation (all rows)")
    r["lockbox fair"] = evaluate(pred, LB & FAIR & ACTIVE, "LOCKBOX (fair, active)")
    r["lockbox all"] = evaluate(pred, LB & ACTIVE, "LOCKBOX (all rows)")
    # biggest weights by block (for a sanity look)
    w = mdl.coef_; names = []
    for k, v in blocks.items():
        names += [f"{k}:{j}" for j in range(v.shape[1])]
    top = np.argsort(-np.abs(w))[:25]
    inv_vocab = {j: wd for wd, j in vocab.items()}
    def nm(j):
        k, idx = names[j].split(":"); idx = int(idx)
        if k == "words": return f"word '{inv_vocab.get(idx)}'"
        if k == "words x band": return f"word '{inv_vocab.get(idx // 12)}' x band {band_edges[idx % 12]:.2f}"
        if k == "numeric": return f"num {(F + ['sib_sum', 'sib_n', 'age'])[idx]}"
        return f"{k} {idx}"
    r["top_weights"] = [(nm(j), round(float(w[j]), 4)) for j in top]
    print("  top weights:", r["top_weights"][:12])
    res[train_name] = r
os.makedirs("results", exist_ok=True)
json.dump(res, open("results/bigridge.json", "w"), indent=1)
