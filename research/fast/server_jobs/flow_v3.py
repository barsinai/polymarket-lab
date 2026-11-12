"""Server job (read-only): does taker flow in the last minute carry information beyond the price?
For every settled 5m window with recorded books: at T = end - 20 s take the Up mid (top of book of the Up token) and the
net taker flow over the previous 40 s in $ (buys of Up + sells of Down - sells of Up - buys of Down, from last-trade
prints). If informed traders show up in the flow, the outcome should follow the flow more than the mid says.
Prints realized Up frequency vs the mid, bucketed by flow, and the same split by mid band."""
import glob, gzip, json, os, math, datetime as dt
try:
    import orjson
    _loads = orjson.loads
except ImportError:
    _loads = json.loads
from collections import defaultdict

STORE = os.environ.get("STORE", "/home/runner/pilot-data"); BOOKWS = os.environ.get("BOOKWS_DIR", f"{STORE}/bookws")
META = json.load(open(os.environ.get("RESULTS_META", f"{STORE}/results_meta.json")))
SINCE = os.environ.get("SINCE", (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=16)).strftime("%Y-%m-%dT%H"))   # v1 (30 h) hit the 420-s limit
tok = {}
for s, md in META.items():
    if md.get("up") is None or md.get("window") != 300 or len(md.get("tokens") or []) != 2:
        continue
    tok[md["tokens"][0]] = (s, "Up"); tok[md["tokens"][1]] = (s, "Down")
ev = defaultdict(list); n_kept = [0]
files = [f for f in sorted(glob.glob(f"{BOOKWS}/*.jsonl*")) if os.path.basename(f)[:13] >= SINCE]
for f in files:
    op = gzip.open if f.endswith(".gz") else open
    try:
        with op(f, "rt") as fh:
            for line in fh:
                i = line.find('"a":"')
                if i < 0:
                    continue
                a = line[i + 5:line.find('"', i + 5)]
                if a not in tok:
                    continue
                k = line.rfind('"rx":')                 # rx is the last field: test the time window before parsing the line
                try:
                    rx = float(line[k + 5:line.find("}", k)])
                except ValueError:
                    continue
                s0 = tok[a][0]; e0 = META[s0]["start"] + 300
                if not (e0 - 120 <= rx <= e0 - 20):
                    continue
                try:
                    o = _loads(line)
                except ValueError:
                    continue
                s, side = tok[a]
                end_ = META[s]["start"] + 300
                if not (end_ - 120 <= o["rx"] <= end_ - 20):
                    continue
                n_kept[0] += 1                          # keep only the 100 s that matter (memory: the server holds tens of millions of events)
                ev[s].append((o["rx"], side, o["t"], o.get("top"), o.get("p"), o.get("s"), o.get("side")))
    except Exception as e:  # noqa: BLE001
        print("skip", f, e)
print(f"files {len(files)} since {SINCE}; windows with events {len(ev)}")
rows = []; fav = defaultdict(lambda: [0, 0, 0.0, 0.0])
for s, E in ev.items():
    md = META[s]; end = md["start"] + 300
    E.sort()
    for T in (end - 20, end - 40, end - 60):
        mid = None; flow = 0.0; ask = {"Up": None, "Down": None}
        for rx, side, t, top, p, sz, tside in E:
            if rx > T:
                break
            if t in ("top", "book") and top:
                ask[side] = (top[0], top[1])
                if side == "Up" and top[0] is not None and top[2] is not None:
                    mid = (top[0] + top[2]) / 2
            if t == "ltp" and rx >= T - 40 and p is not None:
                usd = float(p) * float(sz); sign = 1 if tside == "BUY" else -1
                flow += usd * sign * (1 if side == "Up" else -1)
        if T == end - 20 and mid is not None and 0.05 <= mid <= 0.95:
            rows.append((mid, flow, int(md["up"])))
        # late favourite: buy the side whose ask is in the band at T (market-only rule, no model, no K)
        for side in ("Up", "Down"):
            a = ask[side]
            if a and a[0] is not None:
                for lo, hi in ((0.60, 0.70), (0.70, 0.80), (0.80, 0.90), (0.90, 0.95)):
                    if lo <= a[0] < hi:
                        win = (md["up"] == (side == "Up")); f = fav[(int(end - T), f"{lo:.2f}-{hi:.2f}")]
                        sh = min(a[1] or 0, 20 / a[0])
                        if sh >= 5:
                            f[0] += 1; f[1] += win; f[2] += sh * a[0]; f[3] += sh * ((1 if win else 0) - a[0] - 0.07 * a[0] * (1 - a[0]))
print("windows with a mid at end-20 s in 5-95c:", len(rows))
if rows:
    for g, R in (("net flow toward Up", [r for r in rows if r[1] > 0]), ("net flow toward Down", [r for r in rows if r[1] < 0]), ("no trades in 40 s", [r for r in rows if r[1] == 0])):
        if R:
            print(f"  {g:22} n {len(R):4}  mean mid {sum(r[0] for r in R) / len(R):.3f}  realized Up {sum(r[2] for r in R) / len(R):.3f}  gap {sum(r[2] - r[0] for r in R) / len(R):+.3f}")
print("\nlate favourite (buy the side whose best ask is in the band, $20 cap, taker fee):")
for k in sorted(fav):
    n, w, st, pnl = fav[k]
    if n:
        print(f"  {k[0]:2} s before end, ask {k[1]}: n {n:4} win {w / n:6.1%} staked {st:6.0f} pnl {pnl:+7.1f} ({pnl / st:+.1%})")
