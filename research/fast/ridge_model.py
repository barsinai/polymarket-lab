"""Ridge / logistic-ridge model of the Up/Down outcome from many features (read-only research).

Rows: every 2-second look of the paper bot at an Up token with <= REM_MAX s left (obs tape, v4 lines), joined with the
Down token's quote at the same tick and settled against the official result. Features are only things known at that
tick: our TWAP model (z, margin, sigma), the two order books, the asset's recent price path (reconstructed from the
bot's own spot series), BTC's path at the same moment, market-wide co-movement, time of day, asset/window/K-source.

Two targets:  y = 1[Up won]  (logistic regression with an L2 penalty = ridge-logistic)
              e = (official final - our projection) / K in bp  (plain ridge: what the model's forecast misses)
Evaluation is by DAY, never by random rows (rows of one window are near-duplicates): train on the earlier days, test on
the later ones; metrics against two baselines (the market mid, our model's own probability); then the trading rule
"buy the side whose model probability beats its ask by EDGE after fees", one trade per window-side, $20 cap, by day.
"""
import glob, gzip, json, math, os, sys, datetime as dt
from collections import defaultdict
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import log_loss, brier_score_loss

D = "data/fast"; REM_MAX = int(os.environ.get("REM_MAX", "140")); EDGE = float(os.environ.get("EDGE", "0.05"))
M = json.load(open(f"{D}/results_meta.json"))
res = {s: md for s, md in M.items() if md.get("up") is not None and md.get("ptb") and md.get("final")}
ASSETS = ["btc", "eth", "sol", "xrp", "doge", "bnb", "hype", "zec"]


def obs_lines():
    for f in sorted(glob.glob(f"{D}/obs-*.jsonl.gz")) + [f"{D}/obs.jsonl"]:
        op = gzip.open if f.endswith(".gz") else open
        seen = set()
        try:
            with op(f, "rt") as fh:
                for line in fh:
                    h = hash(line)
                    if h in seen:
                        continue
                    seen.add(h)
                    try:
                        o = json.loads(line)
                    except ValueError:
                        continue
                    if o.get("v") == 4 and o.get("src") == "chainlink" and o.get("rem") is not None and o["rem"] <= REM_MAX:
                        yield o
        except Exception:  # noqa: BLE001
            pass


# ---- pass 1: collect ticks; spot series per asset; both sides' quotes per (slug, ts)
spot_ser = defaultdict(dict)        # asset -> {ts: spot}
quotes = {}                         # (slug, ts) -> {"Up": o, "Down": o}
for o in obs_lines():
    a = o["slug"].split("-")[0]
    spot_ser[a][o["ts"]] = o["spot"]
    quotes.setdefault((o["slug"], o["ts"]), {})[o["side"]] = o
print("ticks with quotes:", len(quotes), "assets:", {a: len(v) for a, v in spot_ser.items()}, flush=True)
spot_arr = {a: (np.array(sorted(v)), np.array([v[t] for t in sorted(v)])) for a, v in spot_ser.items()}


def ret_bp(a, ts, k):
    """asset's log return over the last k seconds, bp (nearest tick at or before ts-k; 0 if the series has a gap > 8 s)"""
    T, P = spot_arr[a]
    i = np.searchsorted(T, ts, side="right") - 1
    j = np.searchsorted(T, ts - k, side="right") - 1
    if i < 0 or j < 0 or T[i] - T[j] < k - 2.5 or (ts - T[i]) > 4:
        return 0.0
    return math.log(P[i] / P[j]) * 1e4


def range_bp(a, ts, k):
    T, P = spot_arr[a]
    j = np.searchsorted(T, ts - k, side="left"); i = np.searchsorted(T, ts, side="right")
    seg = P[j:i]
    return (seg.max() - seg.min()) / seg[-1] * 1e4 if len(seg) >= 3 else 0.0


# market-wide co-movement per tick: how many assets have |z| > 1.5 on the Up side with each sign
tick_z = defaultdict(list)
for (slug, ts), q in quotes.items():
    if "Up" in q and q["Up"]["z"] is not None and slug.split("-")[2] == "5m":
        tick_z[ts].append(q["Up"]["z"])


def phi(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


rows = []
for (slug, ts), q in quotes.items():
    if slug not in res or "Up" not in q:
        continue
    u = q["Up"]; d = q.get("Down"); md = res[slug]
    a, w = slug.split("-")[0], slug.split("-")[2]
    K = u["K"]; S = u["spot"]; A = u["A"] if u.get("A") is not None else S; g = u["g"]; rem = u["rem"]; sg = u["sigma"] or 0.0
    proj = g * A + (1 - g) * S if rem <= 60 else S
    z = max(-8.0, min(8.0, u["z"])) if u["z"] is not None else 0.0
    ask_u = u["ask"]; ask_d = d["ask"] if d and d.get("ask") is not None else None
    if ask_u is None or ask_d is None:
        continue
    mid = (ask_u + (1 - ask_d)) / 2        # the market's Up probability from the two asks
    zs = tick_z.get(ts, [])
    hour = dt.datetime.fromtimestamp(ts, dt.timezone.utc)
    rows.append({
        "slug": slug, "ts": ts, "day": hour.strftime("%m-%d"), "asset": a, "w": w, "rem": rem,
        "y": int(md["up"]), "err_bp": (float(md["final"]) - proj) / K * 1e4,
        # our model
        "z": z, "p_model": phi(z), "margin_bp": (proj - K) / K * 1e4, "sigma_bp": sg * 1e4, "g": g,
        "spot_k_bp": (S - K) / K * 1e4, "a_k_bp": (A - K) / K * 1e4, "spot_a_bp": (S - A) / K * 1e4,
        "sd_bp": ((1 - g) * sg * math.sqrt(max(rem, 1) / 3) if rem <= 60 else sg * math.sqrt(rem - 60 + 20)) * 1e4,
        "k_ptb": int(u["k_src"] == "ptb"), "k_twap": int(u["k_src"] == "twap"), "k_cl": int(u["k_src"] == "chainlink"),
        # market
        "ask_u": ask_u, "ask_d": ask_d, "mid": mid, "spread": ask_u + ask_d - 1, "ask_sz_u": math.log1p(u["ask_sz"] or 0), "ask_sz_d": math.log1p(d["ask_sz"] or 0),
        "mkt_minus_model": mid - phi(z),
        # price path
        "r2": ret_bp(a, ts, 2), "r6": ret_bp(a, ts, 6), "r10": ret_bp(a, ts, 10), "r20": ret_bp(a, ts, 20), "r30": ret_bp(a, ts, 30), "r60": ret_bp(a, ts, 60),
        "range60": range_bp(a, ts, 60), "btc_r10": ret_bp("btc", ts, 10) if "btc" in spot_arr else 0.0, "btc_r30": ret_bp("btc", ts, 30) if "btc" in spot_arr else 0.0,
        "n_up": sum(1 for v in zs if v > 1.5), "n_dn": sum(1 for v in zs if v < -1.5),
        "hsin": math.sin(2 * math.pi * (hour.hour + hour.minute / 60) / 24), "hcos": math.cos(2 * math.pi * (hour.hour + hour.minute / 60) / 24),
        "w5": int(w == "5m"), "w15": int(w == "15m"), "w4h": int(w == "4h"),
        **{f"a_{x}": int(a == x) for x in ASSETS},
    })
df = pd.DataFrame(rows)
print("rows", len(df), "windows", df.slug.nunique(), "days", df.groupby("day").size().to_dict(), flush=True)
FEATS = [c for c in df.columns if c not in ("slug", "ts", "day", "asset", "w", "y", "err_bp")]
# interactions that a linear model cannot form on its own
df["z_x_rem"] = df.z * df.rem / 60; df["mid_x_rem"] = (df.mid - 0.5) * df.rem / 60; df["margin_over_sd"] = df.margin_bp / (df.sd_bp + 0.05)
df["mkt_logit"] = np.log(df.mid.clip(0.02, 0.98) / (1 - df.mid.clip(0.02, 0.98)))
FEATS += ["z_x_rem", "mid_x_rem", "margin_over_sd", "mkt_logit"]

days = sorted(df.day.unique())
train_days = [d for d in days if d <= os.environ.get("TRAIN_UNTIL", "11-08")]; test_days = [d for d in days if d not in train_days]
tr, te = df[df.day.isin(train_days)], df[df.day.isin(test_days)]
print(f"\ntrain days {train_days} rows {len(tr)} | test days {test_days} rows {len(te)}")
sc = StandardScaler().fit(tr[FEATS]); Xtr, Xte = sc.transform(tr[FEATS]), sc.transform(te[FEATS])


def report(name, p, y):
    p = np.clip(p, 1e-4, 1 - 1e-4)
    return f"{name:28} logloss {log_loss(y, p):.4f}  brier {brier_score_loss(y, p):.4f}"


print("\n--- out-of-sample probability quality (test days) ---")
print(report("baseline: market mid", te.mid.values, te.y.values))
print(report("baseline: our model phi(z)", te.p_model.values, te.y.values))
best = None
for C in (0.003, 0.01, 0.03, 0.1, 0.3, 1.0):
    lr = LogisticRegression(C=C, max_iter=2000).fit(Xtr, tr.y)
    p = lr.predict_proba(Xte)[:, 1]; ll = log_loss(te.y, np.clip(p, 1e-4, 1 - 1e-4))
    print(report(f"ridge-logistic C={C}", p, te.y.values))
    if best is None or ll < best[0]:
        best = (ll, C, lr, p)
ll, C, lr, p_te = best
print(f"best C {C}; coefficients (standardized):")
coef = sorted(zip(FEATS, lr.coef_[0]), key=lambda x: -abs(x[1]))
print("  " + ", ".join(f"{f} {c:+.2f}" for f, c in coef[:16]))

# calibration of the best model vs the market, by predicted-probability bucket (test days)
te = te.assign(p_hat=p_te)
print("\ncalibration on test days (bucket by model probability): model p / market mid / realized")
for lo in np.arange(0, 1, 0.1):
    b = te[(te.p_hat >= lo) & (te.p_hat < lo + 0.1)]
    if len(b) > 50:
        print(f"  {lo:.1f}-{lo + 0.1:.1f}: n {len(b):6}  model {b.p_hat.mean():.3f}  market {b.mid.mean():.3f}  realized {b.y.mean():.3f}")

# ridge on the forecast error (bp): does anything predict what our TWAP projection misses?
print("\n--- ridge on the forecast error (final - projection, bp), rem <= 60 ---")
tr60, te60 = tr[tr.rem <= 60], te[te.rem <= 60]
sc60 = StandardScaler().fit(tr60[FEATS])
for alpha in (1, 10, 100, 1000):
    rg = Ridge(alpha=alpha).fit(sc60.transform(tr60[FEATS]), tr60.err_bp)
    pred = rg.predict(sc60.transform(te60[FEATS]))
    r2 = 1 - ((te60.err_bp - pred) ** 2).sum() / ((te60.err_bp - te60.err_bp.mean()) ** 2).sum()
    print(f"  alpha {alpha:5}: out-of-sample R^2 {r2:+.4f}   (train R^2 {rg.score(sc60.transform(tr60[FEATS]), tr60.err_bp):+.4f})")
rg = Ridge(alpha=100).fit(sc60.transform(tr60[FEATS]), tr60.err_bp)
print("  largest standardized coefficients:", ", ".join(f"{f} {c:+.3f}" for f, c in sorted(zip(FEATS, rg.coef_), key=lambda x: -abs(x[1]))[:10]))


# ---- trading rule on the test days: buy a side when model probability beats its ask by EDGE after fees; 1 trade / window-side
def trade(dfx, p_up, label):
    by = defaultdict(lambda: [0, 0, 0.0, 0.0]); done = set()
    for (_, r), p in sorted(zip(dfx.iterrows(), p_up), key=lambda x: x[0][1].ts):
        for side, ask, prob, sz_log in (("Up", r.ask_u, p, r.ask_sz_u), ("Down", r.ask_d, 1 - p, r.ask_sz_d)):
            if (r.slug, side) in done or not (0.05 <= ask <= 0.95):
                continue
            fee = 0.07 * ask * (1 - ask)
            if prob - ask - fee < EDGE:
                continue
            sz = math.expm1(sz_log); shares = min(sz, 20.0 / ask)
            if shares < 5:
                continue
            done.add((r.slug, side)); win = (r.y == 1) == (side == "Up")
            b = by[r.day]; b[0] += 1; b[1] += win; b[2] += shares * ask; b[3] += shares * ((1 if win else 0) - ask - fee)
    tot = [sum(v[i] for v in by.values()) for i in range(4)]
    print(f"{label:34} total n {tot[0]:4} win {tot[1] / tot[0] if tot[0] else 0:6.1%} staked {tot[2]:6.0f} pnl {tot[3]:+7.1f} ({tot[3] / tot[2] if tot[2] else 0:+.1%}) | "
          + " ".join(f"{d}: {v[0]}/{v[1]}/{v[3]:+.0f}" for d, v in sorted(by.items())))


print(f"\n--- trading rule, test days, EDGE {EDGE:.2f} over ask+fee, one trade per window-side, $20 cap ---")
trade(te, te.p_model.values, "our model phi(z) vs market")
trade(te, p_te, f"ridge-logistic (C={C}) vs market")
trade(te, 0.5 * (p_te + te.p_model.values), "average of the two")
json.dump({"features": FEATS, "coef": dict(zip(FEATS, map(float, lr.coef_[0]))), "C": C, "train_days": train_days, "test_days": test_days,
           "rows": int(len(df))}, open(f"{D}/ridge_model.json", "w"))
