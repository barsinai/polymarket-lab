"""Server job (read-only, on the raw recordings): how much could a live lock_m have bought, and how fast does the cheap
ask go? For every paper lock / lock_m / lock_c / lock_x trade since the K fix (data/fast/trades.jsonl in the checkout),
on that token's websocket book (top-of-book changes, 5-level snapshots, last-trade prints) from the signal to the end:
  - survival: seconds until the best ask first rises above the price the paper trade took (latency budget)
  - others' fills: size traded on that token at <= the paper price, <= 0.95 and <= 0.97 after the signal (ltp prints;
    a print is a taker hitting a resting ask) = what was there to take
  - 5-level depth at the nearest snapshot before the signal: $ offered at <= 0.95 / <= 0.97
Prints one line per trade and a summary."""
import glob, gzip, json, os, datetime as dt
from collections import defaultdict

STORE = os.environ.get("STORE", "/home/runner/pilot-data"); BOOKWS = os.environ.get("BOOKWS_DIR", f"{STORE}/bookws")
META = json.load(open(os.environ.get("RESULTS_META", f"{STORE}/results_meta.json")))
T0 = dt.datetime(2026, 11, 11, 13, 0, tzinfo=dt.timezone.utc).timestamp()
STRATS = {"lock", "lock_m", "lock_c", "lock_x", "lock_x50", "lock_p", "lock_early"}
trades = []
for l in open("data/fast/trades.jsonl"):
    try:
        t = json.loads(l)
    except ValueError:
        continue
    if t.get("ts", 0) >= T0 and t.get("strat") in STRATS:
        trades.append(t)
tok = {}
for t in trades:
    md = META.get(t["slug"]) or {}
    tk = md.get("tokens") or []
    if len(tk) == 2:
        tok[t["slug"], t["side"]] = tk[0] if t["side"] == "Up" else tk[1]
want = set(tok.values())
hours = sorted({dt.datetime.fromtimestamp(t["ts"], dt.timezone.utc).strftime("%Y-%m-%dT%H") for t in trades})
ev = defaultdict(list)
for h in hours:
    for f in glob.glob(f"{BOOKWS}/{h}.jsonl*"):
        op = gzip.open if f.endswith(".gz") else open
        try:
            with op(f, "rt") as fh:
                for line in fh:
                    i = line.find('"a":"')
                    if i < 0:
                        continue
                    j = line.find('"', i + 5)
                    if line[i + 5:j] not in want:
                        continue                      # cheap token filter before parsing (tens of millions of lines)
                    try:
                        o = json.loads(line)
                    except ValueError:
                        continue
                    ev[o["a"]].append(o)
        except Exception as e:  # noqa: BLE001
            print("skip", f, e)
print(f"trades {len(trades)}, tokens {len(want)}, tokens with recorded events {len(ev)}")
seen = set(); rows = []
for t in sorted(trades, key=lambda t: t["ts"]):
    key = (t["slug"], t["side"])
    if key in seen or key not in tok:
        continue
    seen.add(key)
    E = sorted(ev.get(tok[key], []), key=lambda o: o["rx"])
    end = int(t["slug"].rsplit("-", 1)[1]) + {"5m": 300, "15m": 900, "4h": 14400}[t["slug"].split("-")[2]]
    px = t["price"]; ts = t["ts"]
    surv = None; vol = {"px": 0.0, "95": 0.0, "97": 0.0}; depth = None
    for o in E:
        if o["rx"] < ts:
            if o["t"] == "book" and o.get("asks5"):
                depth = o["asks5"]
            continue
        if o["rx"] > end + 2:
            break
        if o["t"] in ("top", "book") and surv is None and o["top"][0] is not None and o["top"][0] > px + 1e-9:
            surv = o["rx"] - ts
        if o["t"] == "ltp" and o.get("side") == "BUY":
            p = float(o["p"]); s = float(o["s"])
            if p <= px + 1e-9: vol["px"] += s * p
            if p <= 0.95: vol["95"] += s * p
            if p <= 0.97: vol["97"] += s * p
    d95 = sum(p * s for p, s in (depth or []) if p <= 0.95); d97 = sum(p * s for p, s in (depth or []) if p <= 0.97)
    won = (META.get(t["slug"]) or {}).get("up")
    won = None if won is None else (won == (t["side"] == "Up"))
    rows.append((t, surv, vol, d95, d97, won, len(E)))
    print(f"{dt.datetime.fromtimestamp(ts, dt.timezone.utc):%m-%d %H:%M:%S} {t['strat']:8} {t['slug']:26} {t['side']:4} px {px:.2f} rem {t.get('rem', t.get('rem_s'))} "
          f"survive {('%.2f s' % surv) if surv is not None else '>end'}  bought by others <=px ${vol['px']:7.0f} <=.95 ${vol['95']:7.0f} <=.97 ${vol['97']:7.0f}  "
          f"snapshot depth <=.95 ${d95:6.0f} <=.97 ${d97:6.0f}  {'W' if won else 'L' if won is not None else '?'}  events {len(E)}")
S = [r for r in rows if r[6] > 0]
if S:
    sv = sorted((r[1] if r[1] is not None else 99) for r in S); n = len(sv)
    print(f"\nwith recordings: {n} signals; ask survival p25 {sv[n // 4]:.2f} s, median {sv[n // 2]:.2f} s, p75 {sv[3 * n // 4]:.2f} s; "
          f"share surviving > 0.25 s {sum(1 for x in sv if x > 0.25) / n:.0%}, > 1 s {sum(1 for x in sv if x > 1) / n:.0%}")
    for k in ("px", "95", "97"):
        v = sorted(r[2][k] for r in S)
        print(f"others' buys after the signal at <= {k}: median ${v[n // 2]:.0f}, mean ${sum(v) / n:.0f}, total ${sum(v):.0f}")
