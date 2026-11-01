"""First model: can features known at the time of a bet predict how wrong the price is?

Target: (did the first-listed side win: 1/0) - (its price), i.e. the price's error.
Rows: each resolved binary market, at several moments measured back from its *scheduled*
end (1, 2, 3, 5, 7, 14, 30 days), only while it was still trading. Features use only the
price history up to that moment plus facts known at creation (question type, category,
event size). Lifetime volume is NOT used (it's only known at the end).

Validation is out-of-time: fit on moments before --split, test on moments after
--split + 30 days, and test events never appear in training.

Step 1 (slow, streams all saved price files): python research/model.py build
Step 2 (fast):                                python research/model.py fit
"""

import gzip
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime, timezone

import numpy as np

DATA, DERIVED, OUT = "data", "derived", "results"
H, DAY = 3600, 86400
DAYS_BACK = [1, 2, 3, 5, 7, 14, 30]
CATS = ["Sports", "Crypto", "Politics", "Geopolitics", "Economy", "Culture", "Other"]
KW = [("Crypto", r"\b(bitcoin|btc|ethereum|eth|solana|sol|xrp|doge|crypto|token|fdv|airdrop)\b"),
      ("Sports", r"\b(vs\.?|win the|nba|nfl|mlb|nhl|ufc|fc|o/u|spread|grand prix|open|cup|league|match)\b"),
      ("Politics", r"\b(election|president|senate|governor|trump|biden|vote|party|prime minister|mayor|poll)\b"),
      ("Geopolitics", r"\b(war|israel|iran|russia|ukraine|china|ceasefire|strike|nato|invade|military)\b"),
      ("Economy", r"\b(fed|rate|inflation|cpi|gdp|stock|s&p|nasdaq|ipo|earnings|tariff|oil|recession)\b"),
      ("Culture", r"\b(tweet|elon|musk|movie|album|oscar|grammy|spotify|youtube|tiktok|mrbeast)\b")]
TAGS = {"Sports": {"Sports", "Games", "Soccer", "NBA", "NFL (All)", "Esports", "Tennis", "Basketball"},
        "Crypto": {"Crypto", "Crypto Prices", "Bitcoin", "Ethereum"},
        "Geopolitics": {"Geopolitics", "World", "Iran", "Middle East", "Israel", "Ukraine", "Foreign Policy"},
        "Politics": {"Politics", "Elections", "Global Elections", "US Election", "Trump", "U.S. Politics"},
        "Economy": {"Economy", "Finance", "Fed Rates", "Fed", "Business", "Tech", "Economic Policy", "AI"},
        "Culture": {"Culture", "Tweet Markets", "Elon Musk"}}


def jl(path):
    with gzip.open(path, "rt") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def as_list(v):
    if isinstance(v, list):
        return v
    try:
        return json.loads(v) if isinstance(v, str) else []
    except json.JSONDecodeError:
        return []


def ts(s):
    if not s:
        return None
    s = s.replace(" ", "T").replace("Z", "+00:00")
    if s.endswith("+00"):
        s += ":00"
    try:
        return datetime.fromisoformat(s).timestamp()
    except ValueError:
        return None


def category(tags, q):
    labels = {t.get("label") for t in tags or []}
    for c in CATS[:-1]:
        if labels & TAGS[c]:
            return c
    for c, rx in KW:
        if re.search(rx, q):
            return c
    return "Other"


# ------------------------------------------------------------------ build
FEATS = ["p", "logit_p", "dist50", "chg_1h", "chg_6h", "chg_1d", "chg_3d", "chg_7d", "vol_1d", "vol_7d",
         "range_7d", "max_7d_gap", "min_7d_gap", "log_days_left", "frac_elapsed", "log_age_days",
         "yes_no", "deadline", "neg_risk", "log_event_size", "fees", "hist_density_7d", "n_moves_7d", "at_half"] + \
        [f"cat_{c}" for c in CATS] + ["has_1d", "has_7d"]


def features(t_, p_, t, m):
    j = np.searchsorted(t_, t, side="right") - 1
    if j < 0 or t - t_[j] > 6 * H:
        return None
    p = p_[j]
    if not (0.02 < p < 0.98):
        return None

    def at(dt):
        k = np.searchsorted(t_, t - dt, side="right") - 1
        return p_[k] if k >= 0 and (t - dt) - t_[k] <= 6 * H else None

    w1 = (t_ > t - DAY) & (t_ <= t)
    w7 = (t_ > t - 7 * DAY) & (t_ <= t)
    d1, d7 = np.diff(p_[w1]), np.diff(p_[w7])
    chg = {}
    for name, dt in [("1h", H), ("6h", 6 * H), ("1d", DAY), ("3d", 3 * DAY), ("7d", 7 * DAY)]:
        q = at(dt)
        chg[name] = (p - q) if q is not None else 0.0
    life = max(m["end"] - m["start"], H) if m["start"] else None
    f = {"p": p, "logit_p": np.log(p / (1 - p)), "dist50": abs(p - 0.5),
         **{f"chg_{k}": v for k, v in chg.items()},
         "vol_1d": float(d1.std()) if len(d1) > 2 else 0.0, "vol_7d": float(d7.std()) if len(d7) > 2 else 0.0,
         "range_7d": float(p_[w7].max() - p_[w7].min()) if w7.any() else 0.0,
         "max_7d_gap": float(p_[w7].max() - p) if w7.any() else 0.0,
         "min_7d_gap": float(p - p_[w7].min()) if w7.any() else 0.0,
         "log_days_left": np.log1p(max(m["end"] - t, 0) / DAY),
         "frac_elapsed": min(max((t - m["start"]) / life, 0), 1) if life else 0.5,
         "log_age_days": np.log1p(max(t - (m["start"] or t), 0) / DAY),
         "yes_no": float(m["yes"]), "deadline": float(m["deadline"]), "neg_risk": float(m["neg_risk"]),
         "log_event_size": np.log(m["event_size"]), "fees": float(m["fees"]),
         "hist_density_7d": float(w7.sum()) / 168.0,
         "n_moves_7d": float((np.abs(d7) > 1e-9).sum()),  # how many hours the price actually changed
         "at_half": float(abs(p - 0.5) < 0.005),
         **{f"cat_{c}": float(m["cat"] == c) for c in CATS},
         "has_1d": float(at(DAY) is not None), "has_7d": float(at(7 * DAY) is not None)}
    return [f[k] for k in FEATS]


def build():
    events = {str(e["id"]): e.get("tags") for e in jl(f"{DATA}/events_closed.jsonl.gz")}
    raw, ev_size = {}, Counter()
    paths = sorted(os.path.join(f"{DATA}/listing", f) for f in os.listdir(f"{DATA}/listing") if f.endswith(".gz"))
    for path in paths + [f"{DATA}/markets_closed.jsonl.gz"]:
        for m in jl(path):
            mid = str(m.get("id"))
            if mid in raw:
                continue
            ev = (m.get("events") or [{}])[0]
            eid = str(ev.get("id") or mid)
            ev_size[eid] += 1
            prices, outs = as_list(m.get("outcomePrices")), as_list(m.get("outcomes"))
            if len(prices) != 2 or len(outs) != 2:
                raw[mid] = None
                continue
            try:
                pr = [float(x) for x in prices]
            except ValueError:
                raw[mid] = None
                continue
            close, end = ts(m.get("closedTime") or m.get("endDate")), ts(m.get("endDate"))
            if max(pr) < 0.99 or min(pr) > 0.01 or close is None or end is None:
                raw[mid] = None
                continue
            q = (m.get("question") or "").lower()
            raw[mid] = {"won": 1 if pr[0] > 0.5 else 0, "event": eid, "yes": outs[0] == "Yes",
                        "deadline": " by " in q or " before " in q, "neg_risk": bool(m.get("negRisk")),
                        "fees": bool(m.get("feesEnabled")), "close": close, "end": end,
                        "start": ts(m.get("startDate")), "cat": category(events.get(eid), q),
                        "vol": float(m.get("volumeNum") or 0)}
    meta = {k: v for k, v in raw.items() if v}
    for v in meta.values():
        v["event_size"] = ev_size[v["event"]]
    print(f"{len(meta)} resolved binary markets in listing", flush=True)

    X, y, info, fut, seen = [], [], [], [], set()

    def future(t_, p_, t, close):
        """price at time t (for short-term trading targets); nan if missing or after close."""
        if t >= close - H:
            return np.nan
        j = np.searchsorted(t_, t, side="right") - 1
        return p_[j] if j >= 0 and t - t_[j] <= 6 * H else np.nan
    for root, _, files in os.walk(f"{DATA}/prices"):
        for fn in sorted(files):
            if not fn.endswith(".jsonl.gz"):
                continue
            for r in jl(os.path.join(root, fn)):
                mid = r["market_id"]
                m = meta.get(mid)
                if not m or mid in seen or not r["tokens"] or not r["tokens"][0]["history"]:
                    continue
                seen.add(mid)
                a = np.array(r["tokens"][0]["history"], dtype=float)
                t_, p_ = a[:, 0], a[:, 1]
                for d in DAYS_BACK:
                    t = m["end"] - d * DAY
                    if t >= m["close"] - H:  # must still be trading at that moment
                        continue
                    f = features(t_, p_, t, m)
                    if f is None:
                        continue
                    X.append(f); y.append(m["won"] - f[0])
                    fut.append([future(t_, p_, t + h, m["close"]) for h in (6 * H, DAY, 3 * DAY)])
                    info.append((int(mid), int(m["event"]) if m["event"].isdigit() else -1, int(t), d, m["vol"]))
            print(f"  {fn}: {len(seen)} markets, {len(X)} rows", flush=True)
    os.makedirs(DERIVED, exist_ok=True)
    np.savez_compressed(f"{DERIVED}/rows.npz", X=np.array(X, dtype=np.float32), y=np.array(y, dtype=np.float32),
                        info=np.array(info, dtype=np.float64), feats=np.array(FEATS),
                        fut=np.array(fut, dtype=np.float32))  # price +6h, +1d, +3d
    print(f"saved {len(X)} rows from {len(seen)} markets")


# ------------------------------------------------------------------ fit
def fit(split="2026-05-01"):
    from sklearn.ensemble import HistGradientBoostingRegressor
    from sklearn.linear_model import Ridge
    from sklearn.preprocessing import StandardScaler

    d = np.load(f"{DERIVED}/rows.npz")
    X, y, info, feats = d["X"], d["y"], d["info"], list(d["feats"])
    mid, ev, t, days, vol = info.T
    s = datetime.fromisoformat(split).replace(tzinfo=timezone.utc).timestamp()
    tr = t < s
    te = (t >= s + 30 * DAY) & ~np.isin(ev, np.unique(ev[tr]))
    print(f"rows: {len(y)}  train {tr.sum()} (before {split})  test {te.sum()} (after +30d, unseen events)")

    # extra interaction features for the linear model (price level x recent move, etc.)
    def lin(X):
        p = X[:, feats.index("p")]
        extra = [p * X[:, feats.index(c)] for c in ["chg_1d", "chg_7d", "deadline", "log_days_left"]]
        extra += [p ** 2, (p < 0.2) * 1.0, (p > 0.8) * 1.0,
                  np.clip(X[:, feats.index("chg_1d")], -.5, .5) ** 2 * np.sign(X[:, feats.index("chg_1d")])]
        return np.column_stack([X] + extra)

    names = feats + ["p*chg_1d", "p*chg_7d", "p*deadline", "p*days_left", "p^2", "p<20c", "p>80c", "chg_1d^2 signed"]
    sc = StandardScaler().fit(lin(X[tr]))
    R = {"rows_train": int(tr.sum()), "rows_test": int(te.sum()), "split": split, "models": {}}
    preds = {}
    for alpha in [1, 100, 1000, 10000]:
        mdl = Ridge(alpha=alpha).fit(sc.transform(lin(X[tr])), y[tr])
        preds[f"ridge a={alpha}"] = mdl.predict(sc.transform(lin(X[te])))
        if alpha == 1000:
            R["ridge_weights"] = sorted(zip(names, map(float, mdl.coef_)), key=lambda x: -abs(x[1]))[:20]
    gb = HistGradientBoostingRegressor(max_iter=300, learning_rate=0.05, max_leaf_nodes=31,
                                       min_samples_leaf=500, l2_regularization=1.0, random_state=0)
    gb.fit(X[tr], y[tr])
    preds["boosted trees"] = gb.predict(X[te])

    yt, pt = y[te], X[te, feats.index("p")]
    evt = ev[te]
    rng = np.random.default_rng(0)
    uev, inv = np.unique(evt, return_inverse=True)

    def boot_mean(v, mask):
        """95% interval of the mean of v[mask], resampling whole events."""
        s_ = np.bincount(inv[mask], v[mask], len(uev)); n_ = np.bincount(inv[mask], None, len(uev))
        keep = n_ > 0; s_, n_ = s_[keep], n_[keep]
        idx = rng.integers(0, len(s_), (500, len(s_)))
        b = s_[idx].sum(1) / n_[idx].sum(1)
        return float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5))

    for name, pr in preds.items():
        out = {"corr_with_actual_error": float(np.corrcoef(pr, yt)[0, 1]),
               "r2_vs_price_alone": float(1 - np.mean((yt - pr) ** 2) / np.mean(yt ** 2))}
        # strategy: when |predicted error| > thr, buy the side the model says is too cheap.
        # profit per $1 staked, before costs and with an assumed 1c / 2c extra cost per share.
        for thr in [0.02, 0.05, 0.10]:
            sel = np.abs(pr) > thr
            if sel.sum() < 50:
                continue
            buy_yes = pr > 0
            price = np.where(buy_yes, pt, 1 - pt)
            won = np.where(buy_yes, yt + pt, 1 - (yt + pt))  # yt + pt = outcome (1/0)
            row = {"bets": int(sel.sum()), "events": int(len(np.unique(evt[sel])))}
            for cost in [0.0, 0.01, 0.02]:
                c = np.clip(price + cost, 0.001, 0.999)
                ret = won / c - 1
                lo, hi = boot_mean(ret, sel)
                row[f"profit_per_$_cost{int(cost*100)}c"] = [float(ret[sel].mean()), lo, hi]
            out[f"edge>{int(thr*100)}c"] = row
        R["models"][name] = out
        print(name, json.dumps(out), flush=True)

    # simple-rule baseline on the same test rows: bet against a >15c one-day jump
    c1 = X[te, feats.index("chg_1d")]
    rule = np.where(c1 > 0.15, -1, np.where(c1 < -0.15, 1, 0)).astype(float)
    sel = rule != 0
    if sel.sum() > 50:
        price = np.where(rule > 0, pt, 1 - pt); won = np.where(rule > 0, yt + pt, 1 - (yt + pt))
        row = {"bets": int(sel.sum())}
        for cost in [0.0, 0.01, 0.02]:
            ret = won / np.clip(price + cost, 0.001, 0.999) - 1
            row[f"profit_per_$_cost{int(cost*100)}c"] = [float(ret[sel].mean()), *boot_mean(ret, sel)]
        R["baseline_fade_big_move"] = row
        print("baseline", json.dumps(row))
    print("top ridge weights:", R["ridge_weights"][:10])
    os.makedirs(OUT, exist_ok=True)
    with open(f"{OUT}/model_v1.json", "w") as f:
        json.dump(R, f, indent=1)


if __name__ == "__main__":
    build() if sys.argv[1:] == ["build"] else fit(*sys.argv[2:])
