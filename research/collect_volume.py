"""For every closed market in data/listing/: how much money had traded BEFORE each bet moment.

Why: the market list keeps markets by FINAL volume (>= $5k), which over-represents dramatic
outcomes (they attract extra trading). A fair historical test must instead select markets by
volume traded before the bet. This saves, per market, cumulative traded $ at the moments the
analysis uses (1, 2, 3, 5, 7, 14, 30 days before the scheduled end) plus the total.

From the public trades API (same as collect_trades.py). Markets with more trades than the API
will page through are marked truncated; for those the early cumulative values are unknown
(None) unless they can be bounded from big trades.
Output: data/volume/parts/<run>-<k>.jsonl.gz, data/volume/DONE.txt, data/volume/REMAINING
"""
import argparse, gzip, json, os, random, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import collect  # noqa: E402
from collect_trades import pages  # noqa: E402

OUT = "data/volume"
DAYS = [1, 2, 3, 5, 7, 14, 30]


def log(msg):
    print(f"[{datetime.now(timezone.utc):%H:%M:%S}] {msg}", flush=True)


def ts(s):
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
    except (AttributeError, ValueError):
        return None


def fetch(m):
    trades, trunc = pages(m["conditionId"], {})
    rows = sorted((float(t["timestamp"]), float(t["price"]) * float(t["size"])) for t in trades
                  if t.get("timestamp") and t.get("price") and t.get("size"))
    end = ts(m.get("endDate"))
    total = sum(u for _, u in rows)
    at = {}
    if end:
        for d in DAYS:
            t = end - d * 86400
            if trunc and rows and rows[0][0] > t:
                at[d] = None  # trades before t not visible -> unknown
            else:
                at[d] = round(sum(u for tt, u in rows if tt < t), 2)
    return {"market_id": m["id"], "n": len(rows), "truncated": trunc, "total_usd": round(total, 2), "usd_before": at}


def checkpoint(msg):
    for c in ["mkdir -p logs && cp /tmp/volume-log.txt logs/volume-log.txt",
              "git add --sparse data/volume logs/volume-log.txt", f'git commit -qm "{msg} [skip ci]"',
              "git pull -q --rebase origin main", "git push -q"]:
        r = subprocess.run(c, shell=True, capture_output=True, text=True)
        if r.returncode and "commit" not in c:
            log(f"checkpoint step failed: {c}: {r.stderr[-300:]}")
            return
    log(f"checkpoint pushed: {msg}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--time-budget-min", type=float, default=300)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--git-checkpoint", action="store_true")
    a = ap.parse_args()
    t0, run = time.time(), datetime.now(timezone.utc).strftime("%Y%m%dT%H%M")
    os.makedirs(f"{OUT}/parts", exist_ok=True)
    done = set(open(f"{OUT}/DONE.txt").read().split()) if os.path.exists(f"{OUT}/DONE.txt") else set()
    todo = []
    for fn in sorted(os.listdir("data/listing")):
        if fn.endswith(".jsonl.gz"):
            for m in collect.read_jsonl_gz(os.path.join("data/listing", fn)):
                mid = str(m.get("id"))
                if m.get("conditionId") and mid not in done:
                    todo.append({"id": mid, "conditionId": m["conditionId"], "endDate": m.get("endDate")})
    random.Random(11).shuffle(todo)
    log(f"{len(done)} done, {len(todo)} to go")
    k, last = 0, time.time()
    with ThreadPoolExecutor(a.workers) as ex:
        for i in range(0, len(todo), 400):
            if time.time() - t0 > a.time_budget_min * 60:
                break
            recs = list(ex.map(fetch, todo[i:i + 400]))
            collect.write_jsonl_gz(f"{OUT}/parts/{run}-{k:04d}.jsonl.gz", recs)
            k += 1
            done |= {r["market_id"] for r in recs}
            with open(f"{OUT}/DONE.txt", "w") as f:
                f.write("\n".join(sorted(done)) + "\n")
            log(f"batch {k}: total done {len(done)}, truncated {sum(r['truncated'] for r in recs)}/400")
            if a.git_checkpoint and time.time() - last > 30 * 60:
                checkpoint(f"Volume checkpoint {run} ({len(done)} markets)"); last = time.time()
    remaining = len([t for t in todo if t["id"] not in done])
    with open(f"{OUT}/REMAINING", "w") as f:
        f.write(str(remaining))
    log(f"finished: {remaining} remaining")
    if a.git_checkpoint:
        checkpoint(f"Volume {run} done ({len(done)} markets)")


if __name__ == "__main__":
    main()
