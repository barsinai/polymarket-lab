"""Download individual trades for a fixed random sample of closed markets.

Why: price histories don't say how much money had traded by a given moment, how big
individual bets were, or who made them. Trades give all three, plus each wallet's track
record (computed later, offline).

Sample: markets from data/listing/ whose id hashes into 1-in---every (default 12, about
50k markets), so the sample is random, fixed, and reproducible.

Output: data/trades/parts/<run>-<k>.jsonl.gz, one line per market:
  {"market_id", "conditionId", "n", "truncated", "wallets": [...],
   "trades": [[ts, side(1=buy,0=sell), outcomeIndex, price, size, wallet_index], ...],
   "big": same shape - trades >= $100 over the whole life (only when "truncated")}
data/trades/DONE.txt lists finished market ids (so reruns skip them).
"""

import argparse
import gzip
import hashlib
import json
import os
import random
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import collect  # noqa: E402

DATA_API = "https://data-api.polymarket.com"
OUT = "data/trades"
PAGE = 500
MAX_OFFSET = 3000  # the API refuses deeper offsets; beyond that we fall back to big trades only


def log(msg):
    print(f"[{datetime.now(timezone.utc):%H:%M:%S}] {msg}", flush=True)


def in_sample(mid, every):
    return int(hashlib.sha1(str(mid).encode()).hexdigest(), 16) % every == 0


def pages(cid, extra):
    out, offset = [], 0
    while offset <= MAX_OFFSET:
        b = collect.get(f"{DATA_API}/trades", {"market": cid, "limit": PAGE, "offset": offset,
                                               "takerOnly": "false", **extra}, tries=4)
        if b is None:
            return out, True  # error (often: offset too large) -> treat as truncated
        out += b
        if len(b) < PAGE:
            return out, False
        offset += PAGE
    return out, True


def encode(trades, wallets, widx):
    rows = []
    for t in trades:
        w = t.get("proxyWallet") or ""
        if w not in widx:
            widx[w] = len(wallets); wallets.append(w)
        try:
            rows.append([int(t["timestamp"]), 1 if t.get("side") == "BUY" else 0, int(t.get("outcomeIndex") or 0),
                         float(t["price"]), round(float(t["size"]), 4), widx[w]])
        except (KeyError, TypeError, ValueError):
            continue
    rows.sort()
    return rows


def fetch(m):
    cid = m["conditionId"]
    trades, trunc = pages(cid, {})
    wallets, widx = [], {}
    rec = {"market_id": m["id"], "conditionId": cid, "truncated": trunc,
           "trades": encode(trades, wallets, widx)}
    if trunc:
        big, _ = pages(cid, {"filterType": "CASH", "filterAmount": 100})
        rec["big"] = encode(big, wallets, widx)
    rec["n"] = len(rec["trades"])
    rec["wallets"] = wallets
    return rec


def checkpoint(msg):
    for c in ["git add --sparse data/trades logs/trades-log.txt", f'git commit -qm "{msg} [skip ci]"',
              "git pull -q --rebase origin main", "git push -q"]:
        r = subprocess.run(c, shell=True, capture_output=True, text=True)
        if r.returncode and "commit" not in c:
            log(f"checkpoint step failed: {c}: {r.stderr[-300:]}")
            return
    log(f"checkpoint pushed: {msg}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--every", type=int, default=12)
    ap.add_argument("--time-budget-min", type=float, default=290)
    ap.add_argument("--git-checkpoint", action="store_true")
    a = ap.parse_args()
    t_start, run = time.time(), datetime.now(timezone.utc).strftime("%Y%m%dT%H%M")
    os.makedirs(f"{OUT}/parts", exist_ok=True)
    done = set(open(f"{OUT}/DONE.txt").read().split()) if os.path.exists(f"{OUT}/DONE.txt") else set()

    todo = []
    for fn in sorted(os.listdir("data/listing")):
        if fn.endswith(".jsonl.gz"):
            for m in collect.read_jsonl_gz(os.path.join("data/listing", fn)):
                mid = str(m.get("id"))
                if m.get("conditionId") and mid not in done and in_sample(mid, a.every):
                    todo.append({"id": mid, "conditionId": m["conditionId"]})
    random.Random(7).shuffle(todo)
    log(f"{len(done)} done, {len(todo)} to go")

    k, last_ck, batch = 0, time.time(), []
    with ThreadPoolExecutor(4) as ex:
        for i in range(0, len(todo), 200):
            if time.time() - t_start > a.time_budget_min * 60:
                break
            recs = list(ex.map(fetch, todo[i:i + 200]))
            collect.write_jsonl_gz(f"{OUT}/parts/{run}-{k:04d}.jsonl.gz", recs)
            k += 1
            done |= {r["market_id"] for r in recs}
            with open(f"{OUT}/DONE.txt", "w") as f:
                f.write("\n".join(sorted(done)) + "\n")
            n = sum(r["n"] for r in recs); tr = sum(r["truncated"] for r in recs)
            log(f"batch {k}: {len(recs)} markets, {n} trades, {tr} truncated, total done {len(done)}")
            if a.git_checkpoint and time.time() - last_ck > 30 * 60:
                checkpoint(f"Trades checkpoint {run} ({len(done)} markets)"); last_ck = time.time()
    remaining = len([t for t in todo if t["id"] not in done])
    with open(f"{OUT}/REMAINING", "w") as f:
        f.write(str(remaining))
    log(f"finished: {remaining} markets remaining")
    if a.git_checkpoint:
        checkpoint(f"Trades {run} done ({len(done)} markets)")


if __name__ == "__main__":
    main()
