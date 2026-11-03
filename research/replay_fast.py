"""How much of the market maker's trading loss is requote speed?

The hourly replay (replay_mm.py) re-centres quotes once an hour, so a quote can sit stale for
up to an hour while the price moves. A live bot re-centres in seconds. This replay keeps the
hourly replay's market selection, sizes and offsets (it runs paper_mm2.tick for that) but
simulates the hour in between from the trade tape:
  - a running mid estimate: average of the last taker-buy price (~ask) and last taker-sell
    price (~bid) in Yes terms, reset to the book mid at each hourly snapshot;
  - quotes re-centred on that estimate every K seconds (K = 3600 reproduces the hourly replay);
  - fills when a taker trade prints at or through our quote, up to our remaining size;
  - inventory skew and the 2x-size cap as in paper_mm2.
Trade-based mids lag the real book, so this still overstates losses for a fast bot.
Rewards are taken from the hourly replay (identical selection). Output: results/replay_fast.json
Usage: MM_VARIANT=2c MM_SIZE_BY_VOL=1 python research/replay_fast.py --tag _fast
"""
import argparse, glob, gzip, json, os, shutil, sys
from datetime import datetime, timezone
_real_glob = glob.glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import collect  # noqa: E402
import paper_mm2 as P  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--start", default="2026-10-31T20:00"); ap.add_argument("--end", default="2099-01-01T00:00")
ap.add_argument("--tag", default="_fast"); ap.add_argument("--ks", default="3600,600,60,5")
a = ap.parse_args()
KS = [int(x) for x in a.ks.split(",")]
t_start = datetime.fromisoformat(a.start).replace(tzinfo=timezone.utc).timestamp()
t_end = datetime.fromisoformat(a.end).replace(tzinfo=timezone.utc).timestamp()
P.D = f"data/replay_mm/state_{P.VARIANT}{a.tag}"
if os.path.exists(P.D):
    shutil.rmtree(P.D)
meta = {}
for f in sorted(glob.glob("data/live/meta/*.jsonl.gz")):
    for m in collect.read_jsonl_gz(f):
        meta[m["id"]] = m
rewards_files = sorted(glob.glob("data/live/rewards/*.jsonl.gz"))
TR = {}
for f in glob.glob("data/replay_mm/trades/*.json.gz"):
    TR[os.path.basename(f)[:-8]] = json.load(gzip.open(f, "rt"))
snaps = sorted(glob.glob("data/live/20*/*.json.gz"))
mids_hist = {}


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


# one simulator state per K
sims = {k: {"cash": 0.0, "inv": {}, "fills": 0, "mids": {}} for k in KS}
prev_quotes, prev_now = None, None
hours = []
for f in snaps:
    d = json.load(gzip.open(f))
    if "market_columns" not in d or not (t_start <= d["ts"] < t_end):
        continue
    now = d["ts"]
    B = make_books(d)
    cid_mid = {}
    for mid, r in d["markets"].items():
        m = meta.get(mid); b = d["books"].get(f"{mid}:0")
        if m and m.get("conditionId") and b and b[2] and b[3] and b[3][0][0] - b[2][0][0] <= 0.10:
            cid_mid[m["conditionId"]] = (b[2][0][0] + b[3][0][0]) / 2
            mids_hist.setdefault(m["conditionId"], []).append([now, cid_mid[m["conditionId"]]])
    cutoff = now - 48 * 3600
    for c in list(mids_hist):
        mids_hist[c] = [x for x in mids_hist[c] if x[0] >= cutoff]
    # --- simulate the hour that just passed, for each K, from the previous hour's quotes
    if prev_quotes:
        for k, S in sims.items():
            for cid, q in prev_quotes.items():
                if not q.get("rpd"):
                    continue  # exit-only quotes: ignore
                off, size = q["off"], q["size"]
                tick = 0.001 if abs(round(q["bid"], 3) - round(q["bid"], 2)) > 1e-9 or abs(round(q["ask"], 3) - round(q["ask"], 2)) > 1e-9 else 0.01
                est = q["mid"]; last_b = last_a = None
                inv = S["inv"].get(cid, 0.0)
                next_q = prev_now
                bid = ask = None; lb = la = 0.0
                for r_ in TR.get(cid, []):
                    ts_ = r_[0]
                    if not (prev_now < ts_ <= now):
                        continue
                    if ts_ >= next_q:  # (re)quote
                        centre = est - P.SKEW * (inv / size)
                        bid = round(round((centre - off) / tick) * tick, 3); ask = round(round((centre + off) / tick) * tick, 3)
                        lb = size if inv < 2 * size else 0.0; la = size if inv > -2 * size else 0.0
                        next_q = ts_ + k if k < 3600 else now + 1
                    sd, oc, px, sz = r_[1], r_[2], r_[3], r_[4]
                    yp = px if oc == 0 else 1 - px
                    sells_yes = (sd == 0 and oc == 0) or (sd == 1 and oc == 1)
                    if sells_yes and lb > 0 and bid and yp <= bid + 1e-9:
                        fll = min(lb, sz); lb -= fll; inv += fll; S["cash"] -= fll * bid; S["fills"] += 1
                    elif (not sells_yes) and la > 0 and ask and yp >= ask - 1e-9:
                        fll = min(la, sz); la -= fll; inv -= fll; S["cash"] += fll * ask; S["fills"] += 1
                    if sells_yes:
                        last_b = yp
                    else:
                        last_a = yp
                    est = (last_a + last_b) / 2 if (last_a is not None and last_b is not None and last_a > last_b) else yp
                S["inv"][cid] = inv
        # mark to market
        for k, S in sims.items():
            mtm = sum(v * cid_mid.get(c, S["mids"].get(c, 0.5)) for c, v in S["inv"].items())
            for c in S["inv"]:
                if c in cid_mid:
                    S["mids"][c] = cid_mid[c]
            hours.append({"ts": now, "k": k, "cash": round(S["cash"], 2), "mtm": round(mtm, 2), "fills": S["fills"]})
    # --- run the hourly paper trader for the next hour's selection
    P.books_for = lambda toks, B=B: {t: B[t] for t in toks if t in B}
    P.trades_since = lambda cid, t0, now=now: [{"price": r_[3], "size": r_[4], "side": "BUY" if r_[1] else "SELL", "outcomeIndex": r_[2], "timestamp": r_[0],
                                               "proxyWallet": r_[5] if len(r_) > 5 else None}
                                              for r_ in TR.get(cid, []) if t0 < r_[0] <= now]
    P.jump_table = lambda: {c: (max(abs(b[1] - a_[1]) for a_, b in zip(v, v[1:])), (sum((b[1] - a_[1]) ** 2 for a_, b in zip(v, v[1:])) / max(len(v) - 1, 1)) ** 0.5)
                            for c, v in mids_hist.items() if len(v) >= 6}
    rf = [x for x in rewards_files if os.path.basename(x)[:10] <= datetime.fromtimestamp(now, timezone.utc).strftime("%Y-%m-%d")] or rewards_files[:1]
    P.glob.glob = (lambda pat, rf=rf: rf if "rewards" in pat else _real_glob(pat))
    collect.get = lambda *args, **kw: {}
    rep = P.tick(now)
    st = json.load(open(f"{P.D}/state.json"))
    prev_quotes = {}
    for cid, q in st["quotes"].items():
        if q.get("bid") and q.get("ask") and cid in cid_mid:
            prev_quotes[cid] = {**q, "mid": cid_mid[cid]}
    prev_now = now
rep = json.load(open(f"{P.D}/report.json"))
h = (hours[-1]["ts"] - hours[0]["ts"]) / 3600 if hours else 1
out = {"variant": P.VARIANT, "tag": a.tag, "hours": round(h, 1), "rewards_per_hour_hourly_replay": round(rep["rewards_earned"] / h, 2),
       "hourly_replay_trading_per_hour": round((rep["trading_cash"] + rep["inventory_value_at_mid"]) / h, 2), "by_requote_seconds": {}}
for k in KS:
    last = [x for x in hours if x["k"] == k][-1]
    out["by_requote_seconds"][k] = {"trading_per_hour": round((last["cash"] + last["mtm"]) / h, 2), "fills": last["fills"]}
json.dump({"summary": out, "hours": hours}, open(f"results/replay_fast{a.tag}.json", "w"), indent=1)
print(json.dumps(out, indent=1))
