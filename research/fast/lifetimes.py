"""How long does a cheap ask on a LOCKED outcome survive? (Read-only; needs data/fast/bookws, rtds, tokens.jsonl,
results_meta.json with priceToBeat.)

For every window with a result: rebuild the lock state in the last 60 s from the Chainlink feed (same model as
the bot: K = official price to beat, A = mean of feed prices since end-60, sigma from 30 s returns with the
per-asset floor), then walk the websocket top-of-book records of the winning side and measure, for every
moment the best ask is <= ASK_MAX while z >= Z, how long that state lasts before the ask moves above ASK_MAX.
Prints the lifetime distribution (what a bot with reaction time R could have reached) and the $ available.
"""
import glob, gzip, json, math, os, sys
from collections import defaultdict
D = "data/fast"
Z, ASK_MAX, ASK_MIN = float(os.environ.get("Z", "2.5")), float(os.environ.get("ASK_MAX", "0.97")), float(os.environ.get("ASK_MIN", "0.50"))
R_LO, R_HI = float(os.environ.get("R_LO", "0")), float(os.environ.get("R_HI", "60"))   # seconds-before-end range to study
SINCE, UNTIL = os.environ.get("SINCE", ""), os.environ.get("UNTIL", "9")   # archive hours to use, e.g. SINCE=2026-11-09T21 (out-of-sample days)
BOOKWS = os.environ.get("BOOKWS_DIR") or f"{D}/bookws"; RTDS = os.environ.get("RTDS_DIR") or f"{D}/rtds"
META = os.environ.get("RESULTS_META", f"{D}/results_meta.json")
HOUR = os.environ.get("HOUR")          # summarize one UTC hour (YYYY-MM-DDTHH): archives of that hour and the one before, windows ending in it
OUT = os.environ.get("OUT")            # append a one-line JSON summary here (the server's hourly summary, the only thing that goes to git)
if HOUR:
    import datetime as _dt
    _h0 = _dt.datetime.strptime(HOUR, "%Y-%m-%dT%H").replace(tzinfo=_dt.timezone.utc)
    SINCE = (_h0 - _dt.timedelta(hours=1)).strftime("%Y-%m-%dT%H"); UNTIL = (_h0 + _dt.timedelta(hours=1)).strftime("%Y-%m-%dT%H")
    WIN_LO, WIN_HI = _h0.timestamp(), _h0.timestamp() + 3600
else:
    WIN_LO, WIN_HI = 0, 1e12
SIGMA_FLOOR = {"btc": 1.5e-5, "eth": 2.4e-5, "bnb": 1.6e-5, "sol": 3.4e-5, "doge": 3.4e-5, "xrp": 4.3e-5, "hype": 4.2e-5, "zec": 8.6e-5}


def lines(pattern):
    """records of every file matching pattern; duplicate lines within a file are dropped (archives that were
    appended more than once hold the same hour several times)"""
    for f in sorted(glob.glob(pattern)):
        if not (SINCE <= os.path.basename(f)[:13] < UNTIL):
            continue
        op = gzip.open if f.endswith(".gz") else open
        seen = set()
        try:
            with op(f, "rt") as fh:
                while True:
                    try:
                        line = fh.readline()
                    except Exception:  # noqa: BLE001  (a corrupt gzip member ends the file)
                        break
                    if not line:
                        break
                    h = hash(line)
                    if h in seen:
                        continue
                    seen.add(h)
                    try:
                        yield json.loads(line)
                    except ValueError:
                        pass
        except Exception:  # noqa: BLE001
            pass


M = json.load(open(META))
tok2 = {}
for o in lines(f"{D}/tokens.jsonl"):
    tok2[o["tokens"][0]] = (o["slug"], "Up"); tok2[o["tokens"][1]] = (o["slug"], "Down")
for s, md in M.items():
    for i, t in enumerate(md.get("tokens") or []):
        tok2[t] = (s, "Up" if i == 0 else "Down")
print("tokens known:", len(tok2))

# feed: chainlink prices per asset
feed = defaultdict(list); twap60 = defaultdict(list)
for o in lines(f"{RTDS}/*.jsonl*"):
    m = o.get("m") or {}; p = m.get("payload") or {}
    if m.get("topic") == "crypto_prices_chainlink" and p.get("symbol"):
        feed[p["symbol"].split("/")[0]].append((p["timestamp"] / 1000.0, float(p["value"])))
    elif m.get("topic") == "crypto_prices_twap_sixty" and p.get("symbol") and isinstance(p.get("value"), (int, float)):
        twap60[p["symbol"].split("/")[0].lower()].append((p["timestamp"] / 1000.0, float(p["value"])))
for a in feed:
    feed[a] = sorted(set(feed[a]))
for a in twap60:
    twap60[a] = sorted(set(twap60[a]))
# K: the official price to beat is published only after the window is under way (5m: usually not before the last minute),
# so K_EST=bot (default since 11-11) uses what the bot can know at the start: the 60-s TWAP topic at the start, else the
# mean of the Chainlink prints in the minute before. K_EST=ptb reproduces the old (hindsight) study.
K_EST = os.environ.get("K_EST", "bot")


def k_bot(asset, start):
    tw = [v for t, v in twap60.get(asset.lower(), []) if start - 3 <= t <= start + 3]
    if tw:
        return tw[len(tw) // 2], "twap"
    pre = [v for t, v in feed.get(asset, []) if start - 60 <= t < start]
    return (sum(pre) / len(pre), "chainlink") if len(pre) >= 20 else (None, None)
print("feed assets:", {a: len(v) for a, v in feed.items()})

# websocket top-of-book per token
top = defaultdict(list)
for o in lines(f"{BOOKWS}/*.jsonl*"):
    if o.get("t") in ("top", "book") and o.get("top") and o["top"][0] is not None:
        top[o["a"]].append((o["rx"], o["top"][0], o["top"][1] or 0.0))
print("tokens with book records:", len(top), "records:", sum(len(v) for v in top.values()))


def phi(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def sigma30(ser):
    r = []
    j = 0
    for i in range(len(ser)):
        t, p = ser[i]
        while j < len(ser) and ser[j][0] < t - 30:
            j += 1
        if j < i and ser[j][1] > 0 and t - ser[j][0] >= 24:
            r.append(math.log(p / ser[j][1]) / math.sqrt(t - ser[j][0]))
    if len(r) < 60:
        return None
    m = sum(r) / len(r)
    return math.sqrt(sum((x - m) ** 2 for x in r) / (len(r) - 1))


def z_series(asset, start, end, K):
    """(t, z_up) every 0.5 s for end-R_HI <= t <= end-R_LO (the bot's model: Brownian mean over what is left)"""
    ser = [x for x in feed.get(asset, []) if end - 1500 <= x[0] <= end]
    if len(ser) < 200:
        return []
    out = []
    t = end - R_HI
    while t <= end - max(R_LO, 1):
        hist = [x for x in ser if x[0] <= t]
        if len(hist) < 120:
            t += 0.5; continue
        sg = sigma30(hist[-900:])
        if not sg:
            t += 0.5; continue
        sg = max(sg, SIGMA_FLOOR.get(asset, 0))
        S = hist[-1][1]
        if t < end - 60:
            sd = max(S * sg * math.sqrt((end - 60 - t) + 20.0), 1e-9)
            out.append((t, (S - K) / sd))
        else:
            last = [p for tt, p in hist if tt >= end - 60]
            g = (t - (end - 60)) / 60.0; A = sum(last) / len(last) if last else S
            r = max(end - t, 1.0)
            sd = max((1 - g) * S * sg * math.sqrt(r / 3), 1e-9)
            out.append((t, (g * A + (1 - g) * S - K) / sd))
        t += 0.5
    return out


life = []   # (lifetime_s, ask, size, won, slug, side)
n_windows = 0
for tok, recs in top.items():
    if tok not in tok2:
        continue
    slug, side = tok2[tok]; md = M.get(slug)
    if not md or md.get("up") is None or not md.get("ptb"):
        continue
    asset = slug.split("-")[0]; start = md["start"]; end = start + md["window"]
    if not (WIN_LO <= end < WIN_HI):
        continue
    K = md["ptb"]
    if K_EST == "bot":
        K, ksrc = k_bot(asset, start)
        if K is None:
            continue
    zs = z_series(asset, start, end, K)
    if not zs:
        continue
    n_windows += 1
    sign = 1 if side == "Up" else -1
    won = (md["up"] == (side == "Up"))
    recs = sorted(recs, key=lambda x: x[0])
    # state machine: opportunity open when z_side >= Z and ask in [ASK_MIN, ASK_MAX]; remember the ask path
    events = sorted([(t, "z", z) for t, z in zs] + [(rx, "b", (ask, sz)) for rx, ask, sz in recs])
    cur_z = None; cur_ask = None; cur_sz = None; open_t = None; path = []
    for t, kind, v in events:
        if kind == "z":
            cur_z = v * sign
        else:
            cur_ask, cur_sz = v
        locked = cur_z is not None and cur_z >= Z and cur_ask is not None and ASK_MIN <= cur_ask <= ASK_MAX
        if locked and open_t is None:
            open_t = t; path = [(t, cur_ask, cur_sz)]
        elif locked and open_t is not None and kind == "b":
            path.append((t, cur_ask, cur_sz))
        elif not locked and open_t is not None:
            life.append((t - open_t, path[0][1], path[0][2], won, slug, side, path)); open_t = None
    if open_t is not None:
        life.append((end - open_t, path[0][1], path[0][2], won, slug, side, path))


def ask_at(path, dt):
    """ask and size prevailing dt seconds after the episode opened"""
    t0 = path[0][0]; a, sz = path[0][1], path[0][2]
    for t, ask, size in path:
        if t - t0 <= dt:
            a, sz = ask, size
        else:
            break
    return a, sz


print(f"\nwindows with feed + book + result: {n_windows}; locked-and-cheap episodes: {len(life)} (won {sum(1 for x in life if x[3])}, lost {sum(1 for x in life if not x[3])})")
if life:
    print(f"(study range: {R_LO:.0f}-{R_HI:.0f} s before the end, z >= {Z}, ask {ASK_MIN}-{ASK_MAX})")
    for R in (0.05, 0.1, 0.2, 0.3, 0.5, 1.0, 2.0, 3.0, 5.0, 10.0):
        reach = [x for x in life if x[0] >= R]
        w = sum(1 for x in reach if x[3]); n = len(reach)
        usd = pnl = 0.0; prices = []
        for x in reach:
            a, sz = ask_at(x[6], R); stake = min(a * (sz or 0), 20.0)
            usd += stake; pnl += stake / a * ((1 if x[3] else 0) - a - 0.07 * a * (1 - a)); prices.append(a)
        prices.sort()
        print(f"  act after {R:5.2f} s of persistence: episodes {n:4} win {w / n if n else 0:.3f}  stake ${usd:,.0f}  pnl ${pnl:+,.1f} ({pnl / usd if usd else 0:+.1%})  ask paid median {prices[len(prices) // 2] if prices else 0:.2f}")
    # window level: one trade per (window, side), the first episode that lasts R seconds (what the bot does)
    print("  window level (one trade per window-side, first episode that persisted R s):")
    summary = {"hour": HOUR, "k_est": K_EST, "since": SINCE, "until": UNTIL, "z": Z, "ask_max": ASK_MAX, "windows": n_windows, "episodes": len(life),
               "episodes_won": sum(1 for x in life if x[3]), "window_level": {}}
    for R in (0.05, 0.5, 1.0, 2.0, 3.0, 5.0):
        first = {}
        for x in sorted(life, key=lambda x: x[6][0][0]):
            if x[0] >= R and (x[4], x[5]) not in first:
                first[(x[4], x[5])] = x
        n = len(first); w = sum(1 for x in first.values() if x[3]); usd = pnl = 0.0
        for x in first.values():
            a, sz = ask_at(x[6], R); stake = min(a * (sz or 0), 20.0)
            usd += stake; pnl += stake / a * ((1 if x[3] else 0) - a - 0.07 * a * (1 - a))
        print(f"    R {R:4.2f} s: windows {n:4} win {w / n if n else 0:.3f}  stake ${usd:,.0f}  pnl ${pnl:+,.1f} ({pnl / usd if usd else 0:+.1%})")
        summary["window_level"][str(R)] = {"n": n, "won": w, "stake": round(usd, 2), "pnl": round(pnl, 2),
                                           "trades": [{"slug": x[4], "side": x[5], "ask": ask_at(x[6], R)[0], "won": bool(x[3])} for x in first.values()]}
    if OUT:
        with open(OUT, "a") as fh:
            fh.write(json.dumps(summary) + "\n")
    ls = sorted(x[0] for x in life); print("  lifetime percentiles (s): 10%", round(ls[len(ls) // 10], 2), "median", round(ls[len(ls) // 2], 2), "90%", round(ls[9 * len(ls) // 10], 2))
    wl = sorted(x[0] for x in life if x[3]); ll = sorted(x[0] for x in life if not x[3])
    if wl: print("  winners' lifetime median", round(wl[len(wl) // 2], 2), "s;", "losers' median", round(ll[len(ll) // 2], 2) if ll else None, "s")

if not OUT:
  json.dump([{"life": round(x[0], 3), "ask0": x[1], "sz0": x[2], "won": bool(x[3]), "slug": x[4], "side": x[5],
            "ask2": ask_at(x[6], 2.0)[0], "sz2": ask_at(x[6], 2.0)[1]} for x in life], open(f"{D}/episodes.json", "w"))
