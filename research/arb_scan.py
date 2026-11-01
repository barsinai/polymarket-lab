"""Scan recorded live order books for risk-free combinations (no prediction involved).

1. Both sides of one market: if (Yes ask + No ask) < $1, buying one of each pays $1 for sure.
2. Multi-option events (negRisk: exactly one option wins): buying "No" on a set S of options
   costs sum(No asks) and pays at least |S|-1 (all but at most one No win), whether or not
   every option is in S. Guaranteed profit per set = sum(1 - No ask) - 1, when positive.
Uses best ask prices and the size available there (the recording keeps levels within 5c of
best). Reports how often, how big (in $ that could actually be bought), and how long they last.
Fees are not included; markets with fees are counted separately.

Usage: python research/arb_scan.py   -> results/arb_scan.json
"""
import glob
import gzip
import json
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import collect  # noqa: E402

meta = {}
for f in sorted(glob.glob("data/live/meta/*.jsonl.gz")):
    for m in collect.read_jsonl_gz(f):
        meta[m["id"]] = m

pair, basket = [], []
for f in sorted(glob.glob("data/live/20*/*.json.gz")):
    d = json.load(gzip.open(f))
    if "market_columns" not in d:
        continue
    books, ts = d["books"], d["ts"]
    ev = defaultdict(list)
    for mid in d["markets"]:
        b0, b1 = books.get(f"{mid}:0"), books.get(f"{mid}:1")
        if not b0 or not b1 or not b0[3] or not b1[3]:
            continue
        (a0, s0), (a1, s1) = b0[3][0], b1[3][0]
        if a0 + a1 < 0.999:
            sets = min(s0, s1)
            pair.append({"ts": ts, "market": mid, "cost": a0 + a1, "profit_per_set": 1 - a0 - a1,
                         "sets": sets, "profit_usd": sets * (1 - a0 - a1),
                         "fees": bool(meta.get(mid, {}).get("feesEnabled"))})
        m = meta.get(mid)
        if m and m.get("negRisk") and m.get("event_id"):
            ev[m["event_id"]].append((mid, a1, s1, bool(m.get("feesEnabled"))))
    for eid, legs in ev.items():
        legs = [l for l in legs if l[1] < 1]
        if len(legs) < 2:
            continue
        edge = sum(1 - a for _, a, _, _ in legs) - 1
        if edge > 0.001:
            sets = min(s for _, _, s, _ in legs)
            basket.append({"ts": ts, "event": eid, "legs": len(legs), "profit_per_set": edge,
                           "cost_per_set": sum(a for _, a, _, _ in legs), "sets": sets,
                           "profit_usd": sets * edge, "fees": any(l[3] for l in legs)})


def summ(rows, key):
    if not rows:
        return {"count": 0}
    hours = sorted({r["ts"] for r in rows})
    ids = defaultdict(list)
    for r in rows:
        ids[r[key]].append(r["ts"])
    persist = [len(v) for v in ids.values()]
    usd = sorted(r["profit_usd"] for r in rows)
    return {"observations": len(rows), "distinct": len(ids), "hours_with_any": len(hours),
            "median_profit_per_set_c": round(100 * sorted(r["profit_per_set"] for r in rows)[len(rows) // 2], 2),
            "median_profit_usd": round(usd[len(usd) // 2], 2), "max_profit_usd": round(usd[-1], 2),
            "total_profit_usd_if_each_taken_once": round(sum(max(r["profit_usd"] for r in rows if r[key] == k)
                                                             for k in ids), 2),
            "share_with_fees": round(sum(r["fees"] for r in rows) / len(rows), 3),
            "median_hours_seen": sorted(persist)[len(persist) // 2],
            "top": sorted(rows, key=lambda r: -r["profit_usd"])[:8]}


n_snap = len([f for f in glob.glob("data/live/20*/*.json.gz")])
out = {"snapshots": n_snap, "same_market_pairs": summ(pair, "market"), "multi_option_no_baskets": summ(basket, "event")}
os.makedirs("results", exist_ok=True)
json.dump(out, open("results/arb_scan.json", "w"), indent=1)
print(json.dumps({k: ({kk: vv for kk, vv in v.items() if kk != "top"} if isinstance(v, dict) else v)
                  for k, v in out.items()}, indent=1))
for r in out["multi_option_no_baskets"].get("top", [])[:5]:
    print(r, meta.get(next((m for m, mm in meta.items() if mm.get("event_id") == r["event"]), ""), {}).get("event_title"))
