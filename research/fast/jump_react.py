"""How fast does the Up/Down book react to a Chainlink jump, by hour of day? (read-only, websocket recordings)
A 'jump' is a Chainlink print that moves the asset >= JUMP_BP vs the price 2 s earlier, inside the last R_HI seconds of
a 5-minute window. We then watch the Up token's best ASK (websocket top-of-book): how many seconds until it moves by
>= REACT c in the direction the jump implies (ask up after an upward jump, down after a downward one), and what a
'jump chaser' would have earned buying the implied side at the first ask seen >= LAG s after the jump (cap on the price).
Env: SINCE/UNTIL archive hours (as lifetimes.py), JUMP_BP (4), R_HI (120), LAG (0.5), CAP (0.90).
"""
import glob, gzip, json, math, os, datetime as dt
from collections import defaultdict
import numpy as np
D = "data/fast"; BOOKWS = os.environ.get("BOOKWS_DIR") or f"{D}/bookws"; RTDS = os.environ.get("RTDS_DIR") or f"{D}/rtds"
META = os.environ.get("RESULTS_META", f"{D}/results_meta.json"); SINCE, UNTIL = os.environ.get("SINCE", ""), os.environ.get("UNTIL", "9")
JUMP_BP = float(os.environ.get("JUMP_BP", "4")); R_HI = float(os.environ.get("R_HI", "120")); LAG = float(os.environ.get("LAG", "0.5")); CAP = float(os.environ.get("CAP", "0.90"))


def lines(pattern):
    for f in sorted(glob.glob(pattern)):
        if not (SINCE <= os.path.basename(f)[:13] < UNTIL):
            continue
        op = gzip.open if f.endswith(".gz") else open; seen = set()
        try:
            with op(f, "rt") as fh:
                while True:
                    try:
                        line = fh.readline()
                    except Exception:  # noqa: BLE001
                        break
                    if not line:
                        break
                    if hash(line) in seen:
                        continue
                    seen.add(hash(line))
                    try:
                        yield json.loads(line)
                    except ValueError:
                        pass
        except Exception:  # noqa: BLE001
            pass


M = json.load(open(META))
tok2 = {}
for s, md in M.items():
    for i, t in enumerate(md.get("tokens") or []):
        tok2[t] = (s, "Up" if i == 0 else "Down")
feed = defaultdict(list)
for o in lines(f"{RTDS}/*.jsonl*"):
    m = o.get("m") or {}; p = m.get("payload") or {}
    if m.get("topic") == "crypto_prices_chainlink" and p.get("symbol"):
        feed[p["symbol"].split("/")[0].lower()].append((p["timestamp"] / 1000.0, float(p["value"])))
feed = {a: sorted(set(v)) for a, v in feed.items()}
top = defaultdict(list)
for o in lines(f"{BOOKWS}/*.jsonl*"):
    if o.get("t") in ("top", "book") and o.get("top") and o["top"][0] is not None and o["a"] in tok2:
        top[o["a"]].append((o["rx"], o["top"][0], o["top"][1] or 0.0))
up_tok = {s: t for t, (s, side) in tok2.items() if side == "Up"}
print("feed assets", {a: len(v) for a, v in feed.items()}, "| Up tokens with books", sum(1 for s in up_tok if up_tok[s] in top))

lag_by_hour = defaultdict(list); chase = defaultdict(lambda: [0, 0, 0.0, 0.0]); n_jumps = 0
for slug, md in M.items():
    if md.get("up") is None or slug.split("-")[2] != "5m" or slug not in up_tok or up_tok[slug] not in top:
        continue
    a = slug.split("-")[0]; start = md["start"]; end = start + 300
    F = feed.get(a)
    if not F:
        continue
    T = np.array([x[0] for x in F]); Pz = np.array([x[1] for x in F])
    B = sorted(top[up_tok[slug]]); BT = np.array([b[0] for b in B])
    i0 = np.searchsorted(T, end - R_HI); i1 = np.searchsorted(T, end - 3)
    last_jump = -1e9
    for i in range(max(i0, 1), i1):
        t, p = T[i], Pz[i]
        j = np.searchsorted(T, t - 2.0, side="right") - 1
        if j < 0 or t - T[j] > 4:
            continue
        mv = math.log(p / Pz[j]) * 1e4
        if abs(mv) < JUMP_BP or t - last_jump < 10:
            continue
        last_jump = t; n_jumps += 1
        side_up = mv > 0
        k = np.searchsorted(BT, t) - 1
        if k < 0:
            continue
        ask0 = B[k][1]
        # reaction: first book record after t where the ask moved >= 5c in the implied direction
        react = None
        for b in B[k + 1:]:
            if b[0] - t > 30:
                break
            if (side_up and b[1] >= ask0 + 0.05) or ((not side_up) and b[1] <= ask0 - 0.05):
                react = b[0] - t; break
        hr = dt.datetime.fromtimestamp(t, dt.timezone.utc).hour
        lag_by_hour[hr // 4 * 4].append(react if react is not None else 30.0)
        # chaser: buy the implied side at the first ask >= LAG s after the jump (Up ask, or 1 - Up bid ~ Down ask unknown: use Up only)
        if side_up:
            kk = np.searchsorted(BT, t + LAG)
            if kk < len(B) and B[kk][0] - t < 5 and 0.05 <= B[kk][1] <= CAP and B[kk][2] >= 5:
                ask = B[kk][1]; sh = min(B[kk][2], 20 / ask); win = md["up"]; fee = 0.07 * ask * (1 - ask)
                c = chase[hr // 4 * 4]; c[0] += 1; c[1] += win; c[2] += sh * ask; c[3] += sh * ((1 if win else 0) - ask - fee)
print(f"jumps >= {JUMP_BP} bp in the last {R_HI:.0f} s of 5m windows: {n_jumps}")
print("\nbook reaction lag (s until the Up ask moved >= 5c the implied way; 30 = no reaction within 30 s), by 4-hour block UTC:")
for h in sorted(lag_by_hour):
    L = sorted(lag_by_hour[h]); n = len(L)
    print(f"  {h:02d}-{h + 4:02d} UTC: n {n:4}  median {L[n // 2]:5.1f} s  p25 {L[n // 4]:5.1f}  p75 {L[3 * n // 4]:5.1f}  no-reaction {sum(1 for x in L if x >= 30) / n:5.0%}")
print(f"\njump chaser (upward jumps only, buy Up at the first ask {LAG} s after, cap {CAP}, $20):")
for h in sorted(chase):
    n, w, st, pnl = chase[h]
    if n: print(f"  {h:02d}-{h + 4:02d} UTC: n {n:4} win {w / n:6.1%} staked {st:6.0f} pnl {pnl:+7.1f} ({pnl / st:+.1%})")
t = [sum(v[i] for v in chase.values()) for i in range(4)]
if t[0]: print(f"  total: n {t[0]} win {t[1] / t[0]:.1%} pnl {t[3]:+.1f} ({t[3] / t[2]:+.1%})")
