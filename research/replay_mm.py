"""Offline replay of the paper market maker (paper_mm2.py, any variant) over the recorded
hourly books, with fills taken from the real trade record (data/replay_mm/trades/).

Same code path as the live paper trader: paper_mm2.tick() is called once per hourly snapshot
with books_for / trades_since / rewards / jump table / event map served from recorded data.
Granularity is hourly (the live paper trader requotes every 10 min), so replay fills are
somewhat pessimistic (quotes rest longer) - fine for comparing rules against each other.

Usage: MM_VARIANT=1c python research/replay_mm.py [--start 2026-10-31T20:00] [--end ...]
Output: data/replay_mm/results/<variant>.json (same report shape) + per-hour series.
"""
import argparse, glob, gzip, json, os, sys
_real_glob = glob.glob
from datetime import datetime, timezone
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import collect  # noqa: E402
import paper_mm2 as P  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--start", default="2026-10-31T20:00"); ap.add_argument("--end", default="2099-01-01T00:00")
ap.add_argument("--tag", default="")
a = ap.parse_args()
t_start = datetime.fromisoformat(a.start).replace(tzinfo=timezone.utc).timestamp()
t_end = datetime.fromisoformat(a.end).replace(tzinfo=timezone.utc).timestamp()
RD = f"data/replay_mm/results"; os.makedirs(RD, exist_ok=True)
P.D = f"data/replay_mm/state_{P.VARIANT}{a.tag}"
if os.path.exists(P.D):
    import shutil; shutil.rmtree(P.D)

meta = {}
for f in sorted(glob.glob("data/live/meta/*.jsonl.gz")):
    for m in collect.read_jsonl_gz(f):
        meta[m["id"]] = m
tok2cid = {}
for m in meta.values():
    for t in collect.as_list(m.get("clobTokenIds")):
        tok2cid[str(t)] = m.get("conditionId")
rewards_files = sorted(glob.glob("data/live/rewards/*.jsonl.gz"))
TR = {}
for f in glob.glob("data/replay_mm/trades/*.json.gz"):
    TR[os.path.basename(f)[:-8]] = json.load(gzip.open(f, "rt"))
print(f"{len(TR)} markets with trade records", flush=True)
snaps = sorted(glob.glob("data/live/20*/*.json.gz"))
mids_hist = {}  # cid -> [[ts, mid]] rolling 48h, built as we go (what the live job would have had)


def make_books(d):
    out = {}
    for mid, r in d["markets"].items():
        m = meta.get(mid)
        if not m:
            continue
        for j, t in enumerate(collect.as_list(m.get("clobTokenIds"))):
            b = d["books"].get(f"{mid}:{j}")
            if b:
                out[str(t)] = {"bids": [{"price": p, "size": s} for p, s in b[2]], "asks": [{"price": p, "size": s} for p, s in b[3]]}
    return out


hours = []
for f in snaps:
    d = json.load(gzip.open(f))
    if "market_columns" not in d or not (t_start <= d["ts"] < t_end):
        continue
    now = d["ts"]
    B = make_books(d)
    # rolling mids (as record_live.py maintains)
    for mid, r in d["markets"].items():
        m = meta.get(mid); b = d["books"].get(f"{mid}:0")
        if m and m.get("conditionId") and b and b[2] and b[3] and b[3][0][0] - b[2][0][0] <= 0.10:
            mids_hist.setdefault(m["conditionId"], []).append([now, (b[2][0][0] + b[3][0][0]) / 2])
    cutoff = now - 48 * 3600
    for c in list(mids_hist):
        mids_hist[c] = [x for x in mids_hist[c] if x[0] >= cutoff]
    # serve recorded data to the paper trader
    P.books_for = lambda toks, B=B: {t: B[t] for t in toks if t in B}
    P.trades_since = lambda cid, t0, now=now: [{"price": p, "size": s, "side": "BUY" if sd else "SELL", "outcomeIndex": oc, "timestamp": ts_}
                                              for ts_, sd, oc, p, s in TR.get(cid, []) if t0 < ts_ <= now]
    P.jump_table = lambda: {c: (max(abs(b[1] - a_[1]) for a_, b in zip(v, v[1:])), (sum((b[1] - a_[1]) ** 2 for a_, b in zip(v, v[1:])) / max(len(v) - 1, 1)) ** 0.5)
                            for c, v in mids_hist.items() if len(v) >= 6}
    rf = [x for x in rewards_files if os.path.basename(x)[:10] <= datetime.fromtimestamp(now, timezone.utc).strftime("%Y-%m-%d")] or rewards_files[:1]
    P.glob.glob = (lambda pat, rf=rf: rf if "rewards" in pat else _real_glob(pat))
    collect.get = lambda *args, **kw: {}  # no network: no resolution settlement in replay (positions stay marked to mid)
    rep = P.tick(now)
    if rep:
        hours.append({"ts": now, **{k: rep[k] for k in ("rewards_earned", "maker_rebates", "trading_cash", "inventory_value_at_mid", "fills", "quoting", "capital_in_use")}})
if hours:
    h = (hours[-1]["ts"] - hours[0]["ts"]) / 3600 or 1
    last = hours[-1]; tr = last["trading_cash"] + last["inventory_value_at_mid"]
    summary = {"variant": P.VARIANT, "tag": a.tag, "hours": round(h, 1), "rewards_per_hour": round(last["rewards_earned"] / h, 2),
               "rebates_per_hour": round(last["maker_rebates"] / h, 2), "trading_per_hour": round(tr / h, 2), "fills": last["fills"],
               "net_per_hour": round((last["rewards_earned"] + last["maker_rebates"] + tr) / h, 2), "capital": last["capital_in_use"]}
    json.dump({"summary": summary, "hours": hours}, open(f"{RD}/{P.VARIANT}{a.tag}.json", "w"), indent=1)
    print(json.dumps(summary))
