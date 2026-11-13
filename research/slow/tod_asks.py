"""N15 (cycle 6): do near-certain favourites get cheaper at certain hours (UTC) / weekends, and do the dips revert?

Data: data/books/<date>/<HHMM>.json.gz (every 15 min since 10-31, full books trimmed to +-20c, receive-time = snapshot ts).
Set: tokens whose best ask is 0.92-0.985 for most of their life, market end >= 3 days after the snapshot (slow, non-sports by
construction: sports end within the 'closing' window), ask depth >= $10 at the best level.
Numbers:
  1. best ask minus that token's same-UTC-day median, by hour (cents) and weekday/weekend; placebo = shuffled hour labels.
  2. dips (ask >= 1c under the token's trailing 24-h median): best ask 6 h / 24 h later and best bid then
     -> does a patient buyer get a lasting discount (reversion) or was the dip news (no reversion)?
Independent events: tokens grouped by event slug stem (slug without the last '-' part for negRisk sets).
"""
import gzip, json, glob, os, sys, random, statistics as st, collections
from datetime import datetime, timezone

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
files = sorted(glob.glob(os.path.join(ROOT, "data/books/*/*.json.gz")))
obs = collections.defaultdict(list)  # token -> [(ts, ask, ask_sz_usd, bid)]
meta = {}
for i, f in enumerate(files):
    try:
        d = json.load(gzip.open(f))
    except Exception as e:
        print("skip", f, e, file=sys.stderr); continue
    ts = d["ts"]
    for m in d["markets"]:
        try:
            end = datetime.fromisoformat(m["endDate"].replace("Z", "+00:00")).timestamp()
        except Exception:
            continue
        if end - ts < 3 * 86400:
            continue
        toks = m.get("clobTokenIds")
        toks = json.loads(toks) if isinstance(toks, str) else (toks or [])
        for t in toks:
            b = d["books"].get(str(t))
            if not b or not b.get("asks"):
                continue
            lv = lambda L: [(float(x["price"]), float(x["size"])) if isinstance(x, dict) else (float(x[0]), float(x[1])) for x in L]
            asks = sorted(lv(b["asks"]))
            bids = sorted(lv(b.get("bids") or []))
            a, sz = asks[0]
            if not 0.90 <= a <= 0.99:
                continue
            obs[t].append((ts, a, a * sz, bids[-1][0] if bids else None))
            meta[t] = (m["slug"], m["question"][:70], m.get("negRisk"))
    del d

def stem(slug, neg):
    return slug.rsplit("-", 1)[0] if neg else slug

toks = [t for t, L in obs.items() if len(L) >= 48 and 0.92 <= st.median(x[1] for x in L) <= 0.985]
print(f"{len(files)} snapshots, {len(toks)} tokens, {len(set(stem(meta[t][0], meta[t][2]) for t in toks))} event groups")

# 1. hour-of-day deviation
dev = collections.defaultdict(list); wk = collections.defaultdict(list); rows = []
for t in toks:
    byday = collections.defaultdict(list)
    for ts, a, usd, bid in obs[t]:
        byday[ts // 86400].append(a)
    for ts, a, usd, bid in obs[t]:
        if usd < 10:
            continue
        x = 100 * (a - st.median(byday[ts // 86400]))
        h = (ts % 86400) // 3600
        dev[h].append(x); rows.append((h, x))
        wk["weekend" if datetime.fromtimestamp(ts, timezone.utc).weekday() >= 5 else "weekday"].append(x)
print("hour UTC: mean dev of best ask from the token's same-day median (cents), n")
hm = {h: st.mean(v) for h, v in sorted(dev.items())}
for h, v in sorted(dev.items()):
    print(f"  {h:02d}  {st.mean(v):+.3f}c  n={len(v)}")
spread = max(hm.values()) - min(hm.values())
print("weekday/weekend:", {k: f"{st.mean(v):+.3f}c n={len(v)}" for k, v in wk.items()})
random.seed(1); pl = []
for _ in range(200):
    hs = [h for h, _ in rows]; random.shuffle(hs)
    g = collections.defaultdict(list)
    for h, (_, x) in zip(hs, rows):
        g[h].append(x)
    m = [st.mean(v) for v in g.values()]; pl.append(max(m) - min(m))
pl.sort()
print(f"max-min hour spread {spread:.3f}c vs placebo median {pl[100]:.3f}c, p95 {pl[190]:.3f}c")

# 2. dips and reversion (receive-time: only past data define the dip)
res = []
for t in toks:
    L = obs[t]
    for i, (ts, a, usd, bid) in enumerate(L):
        past = [x[1] for x in L if ts - 86400 <= x[0] < ts]
        if len(past) < 40 or usd < 10:
            continue
        med = st.median(past)
        if a > med - 0.01:
            continue
        if res and res[-1][0] == t and ts - res[-1][1] < 6 * 3600:
            continue  # one dip per token per 6 h
        fut = {}
        for lag in (6, 24):
            nxt = [x for x in L if x[0] >= ts + lag * 3600]
            fut[lag] = nxt[0] if nxt and nxt[0][0] - ts < (lag + 2) * 3600 else None
        res.append((t, ts, a, med, fut))
print(f"dips >= 1c under trailing 24-h median: {len(res)} on {len(set(r[0] for r in res))} tokens / "
      f"{len(set(stem(meta[r[0]][0], meta[r[0]][2]) for r in res))} event groups")
for lag in (6, 24):
    R = [(r[2], r[3], r[4][lag]) for r in res if r[4][lag]]
    if not R:
        continue
    ask_ch = [100 * (f[1] - a) for a, med, f in R]
    bid_ch = [100 * (f[3] - a) for a, med, f in R if f[3] is not None]
    back = sum(1 for a, med, f in R if f[1] >= med - 0.002)
    print(f"  +{lag}h: n={len(R)}  later ask - dip ask {st.mean(ask_ch):+.2f}c (median {st.median(ask_ch):+.2f}),"
          f" later bid - dip ask {st.mean(bid_ch):+.2f}c, ask back at the old median {back}/{len(R)}")
out = {"snapshots": len(files), "tokens": len(toks), "hour_dev_c": hm, "hour_spread_c": spread,
       "placebo_p50": pl[100], "placebo_p95": pl[190], "dips": len(res)}
json.dump(out, open(os.path.join(ROOT, "data/research/tod_asks_report.json"), "w"), indent=1)
