"""Maker-vs-taker census from the public trade tape (read-only, 11-14).

Every test so far bought at the ask (taker) and lost the spread + fee to a mid that is about right. The other side of every one
of those trades is a maker. This census asks, per category, who actually wins: for every closed market whose SCHEDULED end fell in
a fixed past window, pull every public trade (data-api /v2/trades: the taker's side, price, size, time) and settle it against the
final outcome. For a taker BUY of outcome i at p the maker is short i at p: maker P&L = size x (p - y_i), capital = size x (1 - p);
for a taker SELL: size x (y_i - p), capital = size x p. Taker P&L = -maker P&L - fee (fee = rate x p(1-p) x size where enabled;
makers get rebateRate of it back). These are prices that really traded - no mid / last-trade / ask guesswork (LESSONS 3).

Cells per market: (hours before the scheduled end | hours before the market's last trade | taker side + outcome | price band).
Sampling is by event-id hash (never by volume, LESSONS 16); the window is by scheduled end date and all markets in it are
closed, so early-settling path markets and late ones are both in (LESSONS 11).
Output: data/research/tape_census.json.gz (per-market cells) + data/research/tape_raw_<cat>.jsonl.gz (raw rows, small categories).
Env: WEEKS (6), T_MAX seconds (2900)."""
import json, time, gzip, os, hashlib, collections, threading, datetime as dt
from concurrent.futures import ThreadPoolExecutor
import requests

G = "https://gamma-api.polymarket.com"; DA = "https://data-api.polymarket.com"
T0 = time.time(); T_MAX = float(os.environ.get("T_MAX", "2900")); WEEKS = int(os.environ.get("WEEKS", "6"))
MAXPAGES = 40
# (tag, category, keep events with hash % den == 0, keep raw rows)
PLAN = [("mention-markets", "mention", 1, True), ("earnings-calls", "mention", 1, True),
        ("mrbeast", "youtube", 1, True), ("youtube", "youtube", 1, True), ("movies", "movies", 1, True),
        ("music", "music", 1, True), ("awards", "awards", 1, True),
        ("elon-tweets", "tweets", 1, True), ("tweets", "tweets", 1, True), ("truth-social", "tweets", 1, True),
        ("pop-culture", "pop-culture", 1, False),
        ("economy", "economy", 2, False), ("ai", "ai/tech", 2, False), ("tech", "ai/tech", 2, False),
        ("geopolitics", "geopolitics", 2, False), ("politics", "politics", 8, False),
        ("esports", "esports", 25, False), ("weather", "weather", 6, False)]
tl = threading.local(); lock = threading.Lock(); nxt = [0.0]; n429 = [0]


def sess():
    if not hasattr(tl, "s"):
        tl.s = requests.Session(); tl.s.headers["User-Agent"] = "polymarket-lab-research/0.1"
    return tl.s


def get(url, params, tries=5, pace=0.07):
    for k in range(tries):
        with lock:                                   # global pacing (~14 requests a second)
            w = nxt[0] - time.time(); nxt[0] = max(nxt[0], time.time()) + pace
        if w > 0:
            time.sleep(w)
        try:
            r = sess().get(url, params=params, timeout=40)
            if r.status_code == 429:
                n429[0] += 1; time.sleep(2.0 * (k + 1)); continue
            if r.status_code != 200:
                return None
            return r.json()
        except Exception:  # noqa: BLE001
            time.sleep(1 + k)
    return None


def trades(cid, extra=None):
    out = []; cur = None
    for _ in range(MAXPAGES):
        p = dict({"condition_id": cid, "limit": 500}, **(extra or {}))
        if cur:
            p["cursor"] = cur
        d = get(f"{DA}/v2/trades", p)
        rows = (d or {}).get("data") if isinstance(d, dict) else None
        if not rows:
            return out, False
        out += rows
        pg = d.get("pagination") or {}
        if not pg.get("has_more") or not pg.get("next_cursor"):
            return out, False
        cur = pg["next_cursor"]
    return out, True


def ts(s):
    try:
        return dt.datetime.fromisoformat(str(s).replace(" ", "T").replace("Z", "+00:00").replace("+00+00:00", "+00:00")).timestamp()
    except Exception:  # noqa: BLE001
        try:
            return dt.datetime.fromisoformat(str(s)[:19]).replace(tzinfo=dt.timezone.utc).timestamp()
        except Exception:  # noqa: BLE001
            return None


def eb(h):      # hours before the scheduled end
    return "E>72" if h > 72 else "E24-72" if h > 24 else "E6-24" if h > 6 else "E1-6" if h > 1 else "E0-1" if h > 0 else "E-1-0" if h > -1 else "E<-1"


def lb(h):      # hours before the market's last trade
    return "L>72" if h > 72 else "L24-72" if h > 24 else "L6-24" if h > 6 else "L1-6" if h > 1 else "L<1"


def pb(p):
    return "<.05" if p < 0.05 else ".05-.15" if p < 0.15 else ".15-.35" if p < 0.35 else ".35-.65" if p < 0.65 else ".65-.85" if p < 0.85 else ".85-.95" if p < 0.95 else ">=.95"


def process(m):
    rows, trunc = trades(m["cid"])
    if not rows:
        return m, None, None
    tt = [float(r["timestamp"]) for r in rows]; last = max(tt); first = min(tt)
    cells = {}; wal = collections.Counter(); raw = []
    for r in rows:
        try:
            p = float(r["price"]); s = float(r["size"]); oi = int(r["outcome_index"]); t = float(r["timestamp"]); buy = r["side"] == "BUY"
        except Exception:  # noqa: BLE001
            continue
        y = m["y0"] if oi == 0 else 1 - m["y0"]
        mp = s * (p - y) if buy else s * (y - p)
        cap = s * (1 - p) if buy else s * p
        fee = m["fee"] * p * (1 - p) * s
        key = f"{eb((m['end'] - t) / 3600)}|{lb((last - t) / 3600)}|{'B' if buy else 'S'}{oi}|{pb(p)}"
        c = cells.setdefault(key, [0, 0.0, 0.0, 0.0, 0.0, 0.0])
        c[0] += 1; c[1] += s; c[2] += s * p; c[3] += mp; c[4] += cap; c[5] += fee
        wal[r.get("proxy_wallet")] += s * p
        if m["raw"]:
            raw.append([int(t), 1 if buy else 0, oi, round(p, 4), round(s, 2), (r.get("proxy_wallet") or "")[2:12]])
    tot = sum(wal.values()) or 1.0
    rec = {"e": m["e"], "cat": m["cat"], "q": m["q"], "end": m["end"], "closed": m["closed"], "y0": m["y0"], "vol": m["vol"], "fee": m["fee"],
           "reb": m["reb"], "n": len(rows), "trunc": trunc, "first": first, "last": last, "w": len(wal),
           "top5": round(sum(v for _, v in wal.most_common(5)) / tot, 3),
           "cells": {k: [v[0]] + [round(x, 3) for x in v[1:]] for k, v in cells.items()}}
    return m, rec, raw


# 1. events per tag and week (scheduled end in the window; all closed)
now = dt.datetime.now(dt.timezone.utc)
seen_ev = set(); todo = []; tagfreq = collections.Counter(); ev_n = collections.Counter()
for tag, cat, den, keep_raw in PLAN:
    for w in range(1, WEEKS + 1):
        a = now - dt.timedelta(days=7 * w + 3); b = now - dt.timedelta(days=7 * (w - 1) + 3)
        for off in range(0, 2000, 100):
            page = get(f"{G}/events", {"tag_slug": tag, "closed": "true", "limit": 100, "offset": off,
                                       "end_date_min": a.strftime("%Y-%m-%dT%H:%M:%SZ"), "end_date_max": b.strftime("%Y-%m-%dT%H:%M:%SZ")}, pace=0.25)
            if not page:
                break
            for e in page:
                if e.get("id") in seen_ev:
                    continue
                seen_ev.add(e.get("id"))
                for t in e.get("tags") or []:
                    tagfreq[t.get("slug")] += 1
                if int(hashlib.md5(str(e.get("id")).encode()).hexdigest(), 16) % den:
                    continue
                ev_n[cat] += 1
                for m in e.get("markets") or []:
                    try:
                        pr = [float(x) for x in json.loads(m.get("outcomePrices") or "[]")]
                        tk = json.loads(m.get("clobTokenIds") or "[]")
                    except Exception:  # noqa: BLE001
                        continue
                    if not m.get("closed") or len(pr) != 2 or len(tk) != 2 or not m.get("conditionId"):
                        continue
                    if not ((pr[0] >= 0.99 and pr[1] <= 0.01) or (pr[1] >= 0.99 and pr[0] <= 0.01)):
                        continue
                    end = ts(m.get("endDate") or e.get("endDate"))
                    if not end:
                        continue
                    fs = m.get("feeSchedule") or {}
                    if isinstance(fs, str):
                        try:
                            fs = json.loads(fs)
                        except Exception:  # noqa: BLE001
                            fs = {}
                    on = str(m.get("feesEnabled")).lower() == "true"
                    todo.append({"cid": m["conditionId"], "e": e.get("slug"), "cat": cat, "q": (m.get("question") or "")[:110], "end": end,
                                 "closed": ts(m.get("closedTime")), "y0": 1.0 if pr[0] >= 0.99 else 0.0, "vol": float(m.get("volumeNum") or 0),
                                 "fee": float(fs.get("rate") or 0) if on else 0.0, "reb": float(fs.get("rebateRate") or 0) if on else 0.0,
                                 "raw": keep_raw, "den": den, "start": ts(e.get("startTime") or m.get("gameStartTime") or "")})
            if len(page) < 100:
                break
    print(f"{tag:16} -> {cat:12} events kept {ev_n[cat]:5} markets queued {sum(1 for x in todo if x['cat'] == cat):6}  ({time.time() - T0:.0f}s)", flush=True)
print("top tags among fetched events:", tagfreq.most_common(120), flush=True)

# 1b. does the tape expose maker rows?
if todo:
    c0 = max((x for x in todo if x["cat"] == "mention"), key=lambda x: x["vol"], default=todo[0])["cid"]
    a, _ = trades(c0); b, _ = trades(c0, {"taker_only": "false"}); c, _ = trades(c0, {"takerOnly": "false"})
    print("rows default / taker_only=false / takerOnly=false:", len(a), len(b), len(c), flush=True)
    if len(b) != len(a) or len(c) != len(a):
        x = b if len(b) != len(a) else c
        h = collections.Counter(r.get("transaction_hash") for r in x)
        print("  rows per tx (top):", h.most_common(3), "sample:", [(r.get("side"), r.get("outcome_index"), r.get("price"), r.get("size"), (r.get("proxy_wallet") or "")[:8])
                                                                 for r in x if r.get("transaction_hash") == h.most_common(1)[0][0]][:6], flush=True)

# 2. tapes (5 threads, global pacing)
out = {}; raws = collections.defaultdict(list); done = 0; skipped = 0
with ThreadPoolExecutor(5) as ex:
    it = iter(todo); futs = []
    while True:
        while len(futs) < 40 and time.time() - T0 < T_MAX:
            m = next(it, None)
            if m is None:
                break
            futs.append(ex.submit(process, m))
        if not futs:
            break
        f = futs.pop(0)
        m, rec, raw = f.result()
        done += 1
        if rec:
            out[m["cid"]] = rec
            if raw:
                raws[m["cat"]].append({"cid": m["cid"], "e": m["e"], "q": m["q"], "end": m["end"], "y0": m["y0"], "fee": m["fee"], "rows": raw})
        if done % 1000 == 0:
            print(f"  {done} markets, {sum(r['n'] for r in out.values())} trades, 429s {n429[0]}, {time.time() - T0:.0f}s", flush=True)
    skipped = sum(1 for _ in it)
print(f"markets done {done} (with trades {len(out)}), not reached {skipped}, 429s {n429[0]}", flush=True)
os.makedirs("data/research", exist_ok=True)
json.dump({"at": now.strftime("%Y-%m-%d %H:%M"), "weeks": WEEKS, "plan": PLAN, "events_kept": dict(ev_n), "markets": out},
          gzip.open("data/research/tape_census.json.gz", "wt"), separators=(",", ":"))
for cat, L in raws.items():
    with gzip.open(f"data/research/tape_raw_{cat.replace('/', '_')}.jsonl.gz", "wt") as fh:
        for x in L:
            fh.write(json.dumps(x, separators=(",", ":")) + "\n")

# 3. summary: who wins, by category and time before the scheduled end
EB = ["E>72", "E24-72", "E6-24", "E1-6", "E0-1", "E-1-0", "E<-1"]
agg = collections.defaultdict(lambda: [0, 0.0, 0.0, 0.0, 0.0])      # (cat, eb) -> trades, taker $, maker pnl, maker capital, fee
ev = collections.defaultdict(set)
for cid, r in out.items():
    ev[r["cat"]].add(r["e"])
    for k, v in r["cells"].items():
        e_ = k.split("|")[0]
        for key in ((r["cat"], e_), (r["cat"], "ALL")):
            a = agg[key]; a[0] += v[0]; a[1] += v[2]; a[2] += v[3]; a[3] += v[4]; a[4] += v[5]
print("\nmaker P&L by category (all trades settled at the final outcome); pnl% = maker P&L / taker $ volume; cap% = / maker capital")
for cat in sorted({k[0] for k in agg}):
    a = agg[(cat, "ALL")]
    print(f"{cat:12} events {len(ev[cat]):5} markets {sum(1 for r in out.values() if r['cat'] == cat):6} trades {a[0]:8} taker ${a[1]:12,.0f} "
          f"maker pnl ${a[2]:11,.0f} ({a[2] / a[1] if a[1] else 0:+.2%} of volume, {a[2] / a[3] if a[3] else 0:+.2%} of capital) taker fees ${a[4]:9,.0f}")
    for e_ in EB:
        a = agg.get((cat, e_))
        if a and a[1] > 0:
            print(f"      {e_:7} trades {a[0]:8} taker ${a[1]:12,.0f} maker pnl ${a[2]:11,.0f} ({a[2] / a[1]:+.2%} vol, {a[2] / a[3] if a[3] else 0:+.2%} cap)")
