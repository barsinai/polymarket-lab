"""Paper trading: pretend bets on live markets at the price we'd really pay. No money.

Called by record_live.py each hour with the open markets and their full order books.
For every open binary market, three strategies decide whether to bet (one side, $10):
  model     - live_v1 model: bet when its estimated win chance minus the real average
              price for $10 (walking the sell orders) is more than 2c
  fade_jump - the simple rule: price moved >15c in a day -> buy the side that fell
  longshot  - the cheap side (5-20c) about a week (5-9 days) before the scheduled end
Every signal is logged with the real fill price; scoring (score()) later looks up how
each market resolved. Analysis counts each market once per strategy (its first signal).

Output: data/paper/YYYY-MM-DD/HHMM.jsonl.gz, data/paper/resolutions.jsonl.gz
"""

import glob
import gzip
import json
import math
import os
import pickle
import re
import sys
from datetime import datetime, timezone

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import collect  # noqa: E402

STAKE = 10.0
MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", "live_v1.pkl")
KW = [("Crypto", r"\b(bitcoin|btc|ethereum|eth|solana|sol|xrp|doge|crypto|token|fdv|airdrop)\b"),
      ("Sports", r"\b(vs\.?|win the|nba|nfl|mlb|nhl|ufc|fc|o/u|spread|grand prix|open|cup|league|match)\b"),
      ("Politics", r"\b(election|president|senate|governor|trump|biden|vote|party|prime minister|mayor|poll)\b"),
      ("Geopolitics", r"\b(war|israel|iran|russia|ukraine|china|ceasefire|strike|nato|invade|military)\b"),
      ("Economy", r"\b(fed|rate|inflation|cpi|gdp|stock|s&p|nasdaq|ipo|earnings|tariff|oil|recession)\b"),
      ("Culture", r"\b(tweet|elon|musk|movie|album|oscar|grammy|spotify|youtube|tiktok|mrbeast)\b")]


def ts(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def category(q):
    for c, rx in KW:
        if re.search(rx, q):
            return c
    return "Other"


def fnum(x, default=0.0):
    try:
        return float(x) if x is not None else default
    except (TypeError, ValueError):
        return default


def fill(book, dollars=STAKE):
    """Walk the sell orders: average price and dollars actually spent for a `dollars` buy."""
    asks = sorted((float(a["price"]), float(a["size"])) for a in (book or {}).get("asks") or [])
    spent = shares = 0.0
    for price, size in asks:
        take = min(size, (dollars - spent) / price)
        spent += take * price; shares += take
        if spent >= dollars - 1e-6:
            break
    return (spent / shares if shares else None), spent, (asks[0][0] if asks else None)


def features(m, p, now, names):
    q = (m.get("question") or "").lower()
    start, end = ts(m.get("startDate")), ts(m.get("endDate"))
    life = max(end - start, 3600) if start and end else None
    cat = category(q)
    f = {"p": p, "logit_p": math.log(p / (1 - p)), "dist50": abs(p - 0.5),
         "chg_1h": fnum(m.get("oneHourPriceChange")), "chg_1d": fnum(m.get("oneDayPriceChange")),
         "chg_7d": fnum(m.get("oneWeekPriceChange")),
         "log_days_left": math.log1p(max(end - now, 0) / 86400) if end else 0.0,
         "frac_elapsed": min(max((now - start) / life, 0), 1) if life else 0.5,
         "log_age_days": math.log1p(max(now - start, 0) / 86400) if start else 0.0,
         "yes_no": float(collect.as_list(m.get("outcomes"))[:1] == ["Yes"]),
         "deadline": float(" by " in q or " before " in q), "neg_risk": float(bool(m.get("negRisk"))),
         "fees": float(bool(m.get("feesEnabled"))), **{f"cat_{c}": float(cat == c) for c in
                                                       ["Sports", "Crypto", "Politics", "Geopolitics", "Economy", "Culture", "Other"]}}
    return [f[k] for k in names], cat


def run(markets, raw_books, now, out_dir="data/paper"):
    with open(MODEL_PATH, "rb") as fh:
        M = pickle.load(fh)
    rows, X, meta = [], [], []
    for m in markets:
        toks = [str(t) for t in collect.as_list(m.get("clobTokenIds"))]
        if len(toks) != 2 or not m.get("acceptingOrders", True):
            continue
        bb, ba = fnum(m.get("bestBid"), None), fnum(m.get("bestAsk"), None)
        if bb and ba and 0 < bb < ba < 1 and ba - bb <= 0.10:
            p = (bb + ba) / 2
        else:
            p = fnum(m.get("lastTradePrice"), None)
        if p is None or not (0.02 < p < 0.98):
            continue
        f, cat = features(m, p, now, M["features"])
        X.append(f); meta.append((m, toks, p, cat))
    if not X:
        return 0
    pred = M["model"].predict(np.array(X, dtype=np.float32))
    for (m, toks, p, cat), err in zip(meta, pred):
        end = ts(m.get("endDate"))
        days_left = (end - now) / 86400 if end else None
        chg = fnum(m.get("oneDayPriceChange"))
        prob0 = min(max(p + float(err), 0.001), 0.999)
        sides = {}
        for side in (0, 1):
            avg, spent, best = fill(raw_books.get(toks[side]))
            sides[side] = (avg, spent, best, prob0 if side == 0 else 1 - prob0)
        signals = []
        for side, (avg, spent, best, prob) in sides.items():
            if avg and spent >= STAKE - 0.01 and prob - avg > 0.02:
                signals.append(("model", side))
        if abs(chg) > 0.15 and 0.03 < p < 0.97:
            signals.append(("fade_jump", 1 if chg > 0 else 0))
        if days_left is not None and 5 <= days_left <= 9:
            for side, sp in ((0, p), (1, 1 - p)):
                if 0.05 <= sp < 0.20:
                    signals.append(("longshot", side))
        for strat, side in signals:
            avg, spent, best, prob = sides[side]
            rows.append({"ts": int(now), "market_id": str(m["id"]), "strategy": strat, "side": side,
                         "outcome": (collect.as_list(m.get("outcomes")) or ["?", "?"])[side], "p_side": round(p if side == 0 else 1 - p, 4),
                         "model_prob": round(prob, 4), "best_ask": best, "avg_fill": avg and round(avg, 4),
                         "filled_usd": round(spent, 2), "days_left": days_left and round(days_left, 2),
                         "volume": fnum(m.get("volumeNum")), "liquidity": fnum(m.get("liquidityNum")),
                         "category": cat, "fees": bool(m.get("feesEnabled")), "question": m.get("question")})
    d = datetime.fromtimestamp(now, timezone.utc)
    os.makedirs(f"{out_dir}/{d:%Y-%m-%d}", exist_ok=True)
    collect.write_jsonl_gz(f"{out_dir}/{d:%Y-%m-%d}/{d:%H%M}.jsonl.gz", rows)
    return len(rows)


def score(out_dir="data/paper"):
    """Look up how signalled markets resolved; keep a cumulative resolutions file."""
    rp = f"{out_dir}/resolutions.jsonl.gz"
    res = {r["id"]: r for r in collect.read_jsonl_gz(rp)}
    ids = set()
    for f in glob.glob(f"{out_dir}/*/*.jsonl.gz"):
        for r in collect.read_jsonl_gz(f):
            ids.add(r["market_id"])
    todo = sorted(i for i in ids if not res.get(i, {}).get("resolved"))
    for k in range(0, len(todo), 40):
        chunk = todo[k:k + 40]
        got = collect.get(f"{collect.GAMMA}/markets", [("id", i) for i in chunk] + [("limit", 100)]) or []
        for m in got:
            pr = [fnum(x) for x in collect.as_list(m.get("outcomePrices"))]
            resolved = bool(m.get("closed")) and len(pr) == 2 and max(pr) >= 0.99
            res[str(m["id"])] = {"id": str(m["id"]), "closed": bool(m.get("closed")), "resolved": resolved,
                                 "winner": (0 if pr[0] > pr[1] else 1) if resolved else None,
                                 "closedTime": m.get("closedTime")}
    collect.write_jsonl_gz(rp, list(res.values()))
    return sum(1 for r in res.values() if r.get("resolved")), len(ids)


def report(out_dir="data/paper"):
    """Profit per strategy, counting each market once (first signal), at the real fill price."""
    res = {r["id"]: r for r in collect.read_jsonl_gz(f"{out_dir}/resolutions.jsonl.gz")}
    first = {}
    for f in sorted(glob.glob(f"{out_dir}/*/*.jsonl.gz")):
        for r in collect.read_jsonl_gz(f):
            first.setdefault((r["strategy"], r["market_id"]), r)
    out = {}
    for (strat, mid), r in first.items():
        o = out.setdefault(strat, {"signals": 0, "resolved": 0, "stake": 0.0, "pnl": 0.0, "wins": 0})
        o["signals"] += 1
        z = res.get(mid)
        if not z or not z.get("resolved") or not r.get("avg_fill"):
            continue
        won = z["winner"] == r["side"]
        o["resolved"] += 1; o["wins"] += won; o["stake"] += r["filled_usd"]
        o["pnl"] += r["filled_usd"] * ((1 / r["avg_fill"]) - 1 if won else -1)
    for o in out.values():
        o["profit_per_$"] = round(o["pnl"] / o["stake"], 4) if o["stake"] else None
    return out


if __name__ == "__main__":
    if sys.argv[1:] == ["score"]:
        print(score())
    print(json.dumps(report(), indent=1))
