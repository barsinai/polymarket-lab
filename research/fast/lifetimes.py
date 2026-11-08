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
SIGMA_FLOOR = {"btc": 1.5e-5, "eth": 2.4e-5, "bnb": 1.6e-5, "sol": 3.4e-5, "doge": 3.4e-5, "xrp": 4.3e-5, "hype": 4.2e-5, "zec": 8.6e-5}


def lines(pattern):
    for f in sorted(glob.glob(pattern)):
        op = gzip.open if f.endswith(".gz") else open
        try:
            with op(f, "rt") as fh:
                for line in fh:
                    try:
                        yield json.loads(line)
                    except ValueError:
                        pass
        except (OSError, EOFError):
            pass


M = json.load(open(f"{D}/results_meta.json"))
tok2 = {}
for o in lines(f"{D}/tokens.jsonl"):
    tok2[o["tokens"][0]] = (o["slug"], "Up"); tok2[o["tokens"][1]] = (o["slug"], "Down")
for s, md in M.items():
    for i, t in enumerate(md.get("tokens") or []):
        tok2[t] = (s, "Up" if i == 0 else "Down")
print("tokens known:", len(tok2))

# feed: chainlink prices per asset
feed = defaultdict(list)
for o in lines(f"{D}/rtds/*.jsonl*"):
    m = o.get("m") or {}; p = m.get("payload") or {}
    if m.get("topic") == "crypto_prices_chainlink" and p.get("symbol"):
        feed[p["symbol"].split("/")[0]].append((p["timestamp"] / 1000.0, float(p["value"])))
for a in feed:
    feed[a] = sorted(set(feed[a]))
print("feed assets:", {a: len(v) for a, v in feed.items()})

# websocket top-of-book per token
top = defaultdict(list)
for o in lines(f"{D}/bookws/*.jsonl*"):
    if o.get("t") in ("top", "book") and o.get("top"):
        top[o["a"]].append((o["rx"], o["top"][0], o["top"][1]))
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
    """(t, z_up) every 0.5 s in the last 60 s"""
    ser = [x for x in feed.get(asset, []) if end - 1500 <= x[0] <= end]
    if len(ser) < 200:
        return []
    out = []
    t = end - 60
    while t <= end - 1:
        hist = [x for x in ser if x[0] <= t]
        if len(hist) < 120:
            t += 0.5; continue
        sg = sigma30(hist[-900:])
        if not sg:
            t += 0.5; continue
        sg = max(sg, SIGMA_FLOOR.get(asset, 0))
        S = hist[-1][1]
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
    zs = z_series(asset, start, end, md["ptb"])
    if not zs:
        continue
    n_windows += 1
    sign = 1 if side == "Up" else -1
    won = (md["up"] == (side == "Up"))
    recs = sorted(recs)
    # state machine: opportunity open when z_side >= Z and ask in [ASK_MIN, ASK_MAX]
    zi = 0; open_t = None; open_ask = None; open_sz = None
    events = sorted([(t, "z", z) for t, z in zs] + [(rx, "b", (ask, sz)) for rx, ask, sz in recs])
    cur_z = None; cur_ask = None; cur_sz = None
    for t, kind, v in events:
        if kind == "z":
            cur_z = v * sign
        else:
            cur_ask, cur_sz = v
        locked = cur_z is not None and cur_z >= Z and cur_ask is not None and ASK_MIN <= cur_ask <= ASK_MAX
        if locked and open_t is None:
            open_t, open_ask, open_sz = t, cur_ask, cur_sz
        elif not locked and open_t is not None:
            life.append((t - open_t, open_ask, open_sz, won, slug, side)); open_t = None
    if open_t is not None:
        life.append((end - open_t, open_ask, open_sz, won, slug, side))

print(f"\nwindows with feed + book + result: {n_windows}; locked-and-cheap episodes: {len(life)} (won {sum(1 for x in life if x[3])}, lost {sum(1 for x in life if not x[3])})")
if life:
    for R in (0.05, 0.1, 0.2, 0.3, 0.5, 1.0, 2.0, 5.0):
        reach = [x for x in life if x[0] >= R]
        w = sum(1 for x in reach if x[3]); n = len(reach)
        usd = sum(min(x[1] * (x[2] or 0), 20) for x in reach)
        pnl = sum(min(x[1] * (x[2] or 0), 20) / x[1] * ((1 if x[3] else 0) - x[1] - 0.07 * x[1] * (1 - x[1])) for x in reach)
        print(f"  reaction {R:4.2f} s: reachable episodes {n:5} win {w / n if n else 0:.3f}  stake ${usd:,.0f}  pnl ${pnl:+,.1f} ({pnl / usd if usd else 0:+.1%})")
    ls = sorted(x[0] for x in life); print("  lifetime percentiles (s): 10%", round(ls[len(ls) // 10], 2), "median", round(ls[len(ls) // 2], 2), "90%", round(ls[9 * len(ls) // 10], 2))
    wl = sorted(x[0] for x in life if x[3]); ll = sorted(x[0] for x in life if not x[3])
    if wl: print("  winners' lifetime median", round(wl[len(wl) // 2], 2), "s;", "losers' median", round(ll[len(ll) // 2], 2) if ll else None, "s")
