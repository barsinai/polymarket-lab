"""Cross-asset consistency (read-only): 5-minute windows of all assets end on the same second; their outcomes are
correlated through the common crypto factor (BTC). Does the BTC market's probability add information about an
alt's outcome beyond the alt's own market price? If yes, the alt's book is slow and can be traded in BTC's direction.
Rows: ticks where both the alt's and BTC's Up/Down asks exist, rem <= REM_MAX. Day split: train 11-07/08, test 11-09/10."""
import glob, gzip, json, math, os, datetime as dt
from collections import defaultdict
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss
D = "data/fast"; REM_MAX = int(os.environ.get("REM_MAX", "140"))
M = json.load(open(f"{D}/results_meta.json")); res = {s: md["up"] for s, md in M.items() if md.get("up") is not None}
q = {}
for f in sorted(glob.glob(f"{D}/obs-*.jsonl.gz")) + [f"{D}/obs.jsonl"]:
    op = gzip.open if f.endswith(".gz") else open; seen = set()
    with op(f, "rt") as fh:
        for line in fh:
            if hash(line) in seen: continue
            seen.add(hash(line))
            try: o = json.loads(line)
            except ValueError: continue
            if o.get("v") != 4 or o["slug"].split("-")[2] != "5m" or o["rem"] > REM_MAX or o.get("ask") is None: continue
            q.setdefault((o["slug"], o["ts"]), {})[o["side"]] = o
mid = {}
for (slug, ts), d in q.items():
    if "Up" in d and "Down" in d:
        mid[(slug, ts)] = ((d["Up"]["ask"] + 1 - d["Down"]["ask"]) / 2, d["Up"], d["Down"])
rows = []
for (slug, ts), (m_alt, u, dn) in mid.items():
    a, end = slug.split("-")[0], int(slug.rsplit("-", 1)[1]) + 300
    if a == "btc" or slug not in res: continue
    bslug = f"btc-updown-5m-{end - 300}"
    if (bslug, ts) not in mid or bslug not in res: continue
    m_btc = mid[(bslug, ts)][0]
    rows.append({"slug": slug, "ts": ts, "day": dt.datetime.fromtimestamp(ts, dt.timezone.utc).strftime("%m-%d"), "asset": a, "rem": u["rem"],
                 "m_alt": m_alt, "m_btc": m_btc, "ask_u": u["ask"], "ask_d": dn["ask"], "sz_u": u["ask_sz"] or 0, "sz_d": dn["ask_sz"] or 0,
                 "z_alt": max(-6, min(6, u["z"] or 0)), "y": int(res[slug]), "y_btc": int(res[bslug])})
print("rows", len(rows), "windows", len({r["slug"] for r in rows}))
lg = lambda p: math.log(min(max(p, 0.02), 0.98) / (1 - min(max(p, 0.02), 0.98)))
days = sorted({r["day"] for r in rows}); tr = [r for r in rows if r["day"] <= "11-08"]; te = [r for r in rows if r["day"] > "11-08"]
print("outcome correlation alt vs btc (window level):", round(np.corrcoef([r["y"] for r in rows], [r["y_btc"] for r in rows])[0, 1], 3))
def X(rs, cols): return np.array([[c(r) for c in cols] for r in rs])
feats = {"alt mid only": [lambda r: lg(r["m_alt"])],
         "alt mid + btc mid": [lambda r: lg(r["m_alt"]), lambda r: lg(r["m_btc"])],
         "alt mid + btc mid + alt z + rem": [lambda r: lg(r["m_alt"]), lambda r: lg(r["m_btc"]), lambda r: r["z_alt"], lambda r: r["rem"] / 60, lambda r: lg(r["m_btc"]) * r["rem"] / 60]}
ytr, yte = [r["y"] for r in tr], [r["y"] for r in te]
print(f"\nbaseline alt market mid, test log loss: {log_loss(yte, np.clip([r['m_alt'] for r in te], 1e-3, 1 - 1e-3)):.4f}")
for name, cols in feats.items():
    lr = LogisticRegression(C=1.0, max_iter=1000).fit(X(tr, cols), ytr); p = lr.predict_proba(X(te, cols))[:, 1]
    print(f"{name:34} test log loss {log_loss(yte, p):.4f}  coef {np.round(lr.coef_[0], 2)}")
# simple rule: BTC market confident (mid >= 0.85 / <= 0.15), the alt's same-direction ask still <= CAP: buy the alt in BTC's direction
print("\nrule: btc mid >= 0.85 (or <= 0.15), alt same-direction ask <= cap, rem in range; one trade per window; $20 cap, shares >= 5")
for cap in (0.60, 0.70, 0.80, 0.90):
    for lo, hi in ((0, 60), (61, 140)):
        by = defaultdict(lambda: [0, 0, 0.0, 0.0]); done = set()
        for r in sorted(rows, key=lambda r: r["ts"]):
            if not (lo <= r["rem"] <= hi) or r["slug"] in done: continue
            if r["m_btc"] >= 0.85: side, ask, sz = "Up", r["ask_u"], r["sz_u"]
            elif r["m_btc"] <= 0.15: side, ask, sz = "Down", r["ask_d"], r["sz_d"]
            else: continue
            if ask > cap or ask < 0.05: continue
            sh = min(sz, 20 / ask)
            if sh < 5: continue
            done.add(r["slug"]); win = (r["y"] == 1) == (side == "Up"); fee = 0.07 * ask * (1 - ask)
            b = by[r["day"]]; b[0] += 1; b[1] += win; b[2] += sh * ask; b[3] += sh * ((1 if win else 0) - ask - fee)
        t = [sum(v[i] for v in by.values()) for i in range(4)]
        if t[0]:
            print(f"  cap {cap:.2f} rem {lo:3}-{hi:3}: n {t[0]:4} win {t[1] / t[0]:6.1%} staked {t[2]:6.0f} pnl {t[3]:+7.1f} ({t[3] / t[2]:+.1%}) | " + " ".join(f"{d}:{v[0]}/{v[1]}/{v[3]:+.0f}" for d, v in sorted(by.items())))
