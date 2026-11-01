"""Fair (selection-bias-free) row filter.

Our market list keeps markets by FINAL volume, which over-represents dramatic outcomes.
A row (market, moment t) is fair if the market had already traded >= MIN_USD before t: every
such market is in our list however it ended. Volume before t comes from data/volume (all
markets, filling up over ~2 days) or, failing that, from the trades sample's features.

usage:  from fair import fair_mask;  F = fair_mask(MID, DAYS, min_usd=5000)
        -> boolean array (True = fair row), plus coverage printed.
"""
import glob
import gzip
import json
import os

import numpy as np


def usd_before_table():
    """market_id -> {days_before: usd or None}"""
    out = {}
    for f in glob.glob("data/volume/parts/*.jsonl.gz"):
        for line in gzip.open(f, "rt"):
            r = json.loads(line)
            out[int(r["market_id"])] = {int(k): v for k, v in (r.get("usd_before") or {}).items()}
    return out


def fair_mask(MID, DAYS, min_usd=5000, verbose=True):
    vt = usd_before_table()
    known = np.zeros(len(MID), bool)
    usd = np.full(len(MID), np.nan)
    for i, (m, d) in enumerate(zip(MID.astype(int), DAYS.astype(int))):
        v = vt.get(m, {}).get(d)
        if v is not None:
            usd[i] = v; known[i] = True
    # fall back on the trades sample for rows not yet covered
    if os.path.exists("derived/trade_feats.npz"):
        tf = np.load("derived/trade_feats.npz")
        names = list(tf["names"])
        idx = tf["idx"]
        vals = np.expm1(tf["F"][:, names.index("log_usd_so_far")])
        miss = ~known[idx]
        usd[idx[miss]] = vals[miss]; known[idx[miss]] = True
    F = known & (usd >= min_usd)
    if verbose:
        print(f"fair filter: volume-before-bet known for {known.mean():.1%} of rows; "
              f"{F.sum()} rows fair at >= ${min_usd:,.0f}", flush=True)
    return F, known, usd
