"""Real buying costs, measured from the recorded live order books.

For every market-hour in data/live, and each side: how much above the "price" (the midpoint
between best buy and best sell offer, which is what price histories approximate) do you
actually pay to buy $10 and $100, walking the sell orders? Grouped by market type, size,
and price level, so backtests can charge a realistic cost instead of a flat guess.

Output: results/costs.json with median and mean extra cost (in cents per share) per group,
plus how often $10 / $100 could not be filled within 5c of the best offer.
"""
import glob
import gzip
import json
import os
import re
import sys
from collections import defaultdict

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import collect  # noqa: E402

KIND = [("soccer prop", r"o/u|exact score|score first|end in a draw|both teams|spread:"),
        ("game winner", r"\bvs\.?\b"), ("crypto", r"bitcoin|btc|ethereum|eth\b|solana|xrp|up or down"),
        ("politics", r"election|president|prime minister|senate|governor|mayor|nominee|party"),
        ]


def kind(q):
    for k, rx in KIND:
        if re.search(rx, q):
            return k
    return "other"


def tier(v):
    return "$5-20k" if v < 2e4 else "$20-100k" if v < 1e5 else "$100k-1M" if v < 1e6 else ">$1M"


def band(p):
    return "<10c" if p < .1 else "10-25c" if p < .25 else "25-50c" if p < .5 else "50-75c" if p < .75 else ">75c"


def walk(asks, dollars):
    spent = shares = 0.0
    for price, size in asks:
        take = min(size, (dollars - spent) / price)
        spent += take * price; shares += take
        if spent >= dollars - 1e-6:
            return spent / shares
    return None  # not fillable within the recorded band


def main():
    meta = {}
    for f in sorted(glob.glob("data/live/meta/*.jsonl.gz")):
        for m in collect.read_jsonl_gz(f):
            meta[m["id"]] = m

    acc = defaultdict(lambda: {"c10": [], "c100": [], "n": 0, "unfill10": 0, "unfill100": 0})
    for f in sorted(glob.glob("data/live/20*/*.json.gz")):
        d = json.load(gzip.open(f))
        if "market_columns" not in d:
            continue
        cols = d["market_columns"]
        iv = cols.index("volumeNum")
        for mid, r in d["markets"].items():
            m = meta.get(mid)
            if not m:
                continue
            b0, b1 = d["books"].get(f"{mid}:0"), d["books"].get(f"{mid}:1")
            if not b0 or not b1 or not b0[2] or not b0[3]:
                continue
            mid0 = (b0[2][0][0] + b0[3][0][0]) / 2  # midpoint of side 0
            k, t = kind((m.get("question") or "").lower()), tier(r[iv] or 0)
            for side, book, pmid in ((0, b0, mid0), (1, b1, 1 - mid0)):
                if not (0.02 < pmid < 0.98) or not book[3]:
                    continue
                g = acc[(k, t, band(pmid))]
                g["n"] += 1
                for usd, key in ((10, "10"), (100, "100")):
                    avg = walk(book[3], usd)
                    if avg is None:
                        g[f"unfill{key}"] += 1
                    else:
                        g[f"c{key}"].append(100 * (avg - pmid))

    out = []
    for (k, t, b), g in sorted(acc.items()):
        if g["n"] < 30:
            continue
        row = {"kind": k, "size": t, "price": b, "observations": g["n"]}
        for key in ("10", "100"):
            v = np.array(g[f"c{key}"])
            row[f"extra_cost_c_${key}_median"] = round(float(np.median(v)), 2) if len(v) else None
            row[f"extra_cost_c_${key}_mean"] = round(float(np.mean(v)), 2) if len(v) else None
            row[f"unfillable_${key}_share"] = round(g[f"unfill{key}"] / g["n"], 3)
        out.append(row)
    os.makedirs("results", exist_ok=True)
    json.dump({"snapshots": len(glob.glob("data/live/20*/*.json.gz")), "groups": out}, open("results/costs.json", "w"), indent=1)
    print(f"{'kind':12} {'size':9} {'price':7} {'n':>6}  $10: median/mean extra c   $100: median/mean  unfillable$100")
    for r in out:
        print(f"{r['kind']:12} {r['size']:9} {r['price']:7} {r['observations']:6}  "
              f"{r['extra_cost_c_$10_median']}/{r['extra_cost_c_$10_mean']}   {r['extra_cost_c_$100_median']}/{r['extra_cost_c_$100_mean']}  {r['unfillable_$100_share']}")


if __name__ == "__main__":
    main()
