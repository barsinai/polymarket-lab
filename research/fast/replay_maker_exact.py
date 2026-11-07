"""Replay a two-sided maker that prices off the EXACT feed (model track) against the real trade tape. Read-only.

Per window: mint N sets; at every model update (model.jsonl every 5 s, obs.jsonl every 2 s in the last
LAST_S seconds) set ask_Up = tick_up(p_up + SPREAD), ask_Down = tick_up(1 - p_up + SPREAD); stop quoting
with STOP_S seconds left. A resting ask is lifted by a later BUY print of that side at a price strictly above
it (partial by the print's size). Unsold inventory resolves; leftover complete sets merge back.
Needs: data/fast/model.jsonl + obs.jsonl (v4), tape.jsonl.gz, results_meta.json (run wallets.py first).
"""
import gzip, json, math, os
from collections import defaultdict

D = "data/fast"
SPREAD = float(os.environ.get("SPREAD", "0.04"))
N_SETS = float(os.environ.get("N_SETS", "20"))
STOP_S = int(os.environ.get("STOP_S", "45"))
M = json.load(open(f"{D}/results_meta.json"))
track = defaultdict(list)   # slug -> [(ts, p_up)]
for line in open(f"{D}/model.jsonl"):
    o = json.loads(line); track[o["slug"]].append((o["ts"], o["p_up"]))
for line in open(f"{D}/obs.jsonl"):
    o = json.loads(line)
    if o.get("v") == 4 and o["side"] == "Up":
        track[o["slug"]].append((o["ts"], o["p_model"]))
tape = defaultdict(list)
with gzip.open(f"{D}/tape.jsonl.gz", "rt") as fh:
    for line in fh:
        t = json.loads(line)
        if t["slug"] in track:
            tape[t["slug"]].append(t)


def tick_up(x):
    return min(0.99, math.ceil(x * 100 - 1e-9) / 100)


def run(slug, spread=SPREAD, n_sets=N_SETS, stop_s=STOP_S):
    md = M[slug]; end = md["start"] + md["window"]
    tr = sorted(track[slug]); prints = sorted(tape[slug], key=lambda t: t["ts"])
    inv = {"Up": n_sets, "Down": n_sets}; cash = -n_sets; fills = []
    i = 0
    for t in prints:
        while i < len(tr) and tr[i][0] <= t["ts"]:
            i += 1
        if i == 0:
            continue  # no quote yet
        ts_q, p_up = tr[i - 1]
        if t["ts"] - ts_q > 8:
            continue  # our quote is stale: treat as cancelled (no fill)
        rem = end - t["ts"]
        if rem <= stop_s or t["side"] != "BUY":
            continue
        s = t["o"]; p_side = p_up if s == "Up" else 1 - p_up
        ask = tick_up(p_side + spread)
        if inv[s] > 0 and t["p"] > ask + 1e-9:
            q = min(t["s"], inv[s]); inv[s] -= q; cash += q * ask; fills.append((rem, s, ask, q, t["p"]))
    win = "Up" if md["up"] else "Down"
    merged = min(inv["Up"], inv["Down"])
    cash += merged + (inv[win] - merged)
    return cash, fills


if __name__ == "__main__":
    slugs = [s for s in track if s in M and M[s].get("up") is not None and tape.get(s)]
    print("windows with model track, tape and result:", len(slugs))
    for spread in (0.02, 0.03, 0.05, 0.08):
        for stop_s in (20, 45, 90):
            tot = 0.0; pos = 0; nf = 0; sold = 0.0; edge = 0.0
            for s in slugs:
                pnl, fills = run(s, spread=spread, stop_s=stop_s)
                tot += pnl; pos += pnl > 0; nf += len(fills)
                win = "Up" if M[s]["up"] else "Down"
                for rem, side, a, q, p in fills:
                    sold += q * a; edge += q * (a - (1.0 if side == win else 0.0))
            if slugs:
                print(f"spread {spread:.2f} stop {stop_s:2}s: P&L {tot / (len(slugs) * N_SETS):+.3%} of capital/window, positive {pos / len(slugs):.0%}, "
                      f"fills {nf}, sold ${sold:,.0f}, sale edge {edge / sold if sold else 0:+.3f}/$")
