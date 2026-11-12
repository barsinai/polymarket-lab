"""Maker on a lock (read-only): instead of paying the ask (0.95-0.97 + taker fee) when the model says an outcome is
locked, rest a BID at B on that side and let sellers come to us (makers pay no fee).

For every settled window with recorded books and Chainlink prints: rebuild z every 0.5 s in the last W seconds from
the prints already RECEIVED (rx; prints arrive ~1.45 s after their timestamp), with the exact price to beat (the bot
has it exactly since 11-11 13:00 UTC). While z_side >= Z (and margin >= MARGIN_MIN bp) our bid at B is "resting".
Fill model (conservative): a taker SELL print on that token at a price <= B while our bid rests -> we buy at B, up to
the print's size, at most CAP $ per window-side. Prints AT B count only with QUEUE_AT_B (default 0: we are assumed to be
behind everyone at our level). P&L = shares x (won - B); no fee for makers.
Also reports the same windows' taker alternative (best ask <= ASK_MAX at the first z >= Z moment, + taker fee).

Env: BOOKWS_DIR, RTDS_DIR, RESULTS_META, SINCE/UNTIL (archive hours), Z (2.5), W (60), MARGIN_MIN (1), CAP (20).
"""
import glob, gzip, json, math, os
from collections import defaultdict

D = "data/fast"
BOOKWS = os.environ.get("BOOKWS_DIR") or f"{D}/bookws"; RTDS = os.environ.get("RTDS_DIR") or f"{D}/rtds"
META = os.environ.get("RESULTS_META", f"{D}/results_meta.json")
SINCE, UNTIL = os.environ.get("SINCE", ""), os.environ.get("UNTIL", "9")
Z = float(os.environ.get("Z", "2.5")); W = float(os.environ.get("W", "60")); MARGIN_MIN = float(os.environ.get("MARGIN_MIN", "1"))
CAP = float(os.environ.get("CAP", "20")); QUEUE_AT_B = float(os.environ.get("QUEUE_AT_B", "0")); ASK_MAX = 0.97
BIDS = [float(x) for x in os.environ.get("BIDS", "0.90,0.93,0.95,0.97").split(",")]
SIGMA_FLOOR = {"btc": 1.5e-5, "eth": 2.4e-5, "bnb": 1.6e-5, "sol": 3.4e-5, "doge": 3.4e-5, "xrp": 4.3e-5, "hype": 4.2e-5, "zec": 8.6e-5}


def files(pattern):
    return [f for f in sorted(glob.glob(pattern)) if SINCE <= os.path.basename(f)[:13] < UNTIL]


def read(f):
    op = gzip.open if f.endswith(".gz") else open
    try:
        with op(f, "rt") as fh:
            while True:
                try:
                    line = fh.readline()
                except Exception:  # noqa: BLE001
                    return
                if not line:
                    return
                yield line
    except Exception:  # noqa: BLE001
        return


M = json.load(open(META))
tok = {}
for s, md in M.items():
    if md.get("up") is None or md.get("ptb") is None or md.get("window") not in (300, 900) or len(md.get("tokens") or []) != 2:
        continue
    tok[md["tokens"][0]] = (s, 0); tok[md["tokens"][1]] = (s, 1)

feed = defaultdict(list)            # coin -> (ts, value, rx)
for f in files(f"{RTDS}/*.jsonl*"):
    for line in read(f):
        if "crypto_prices_chainlink" not in line:
            continue
        try:
            o = json.loads(line)
        except ValueError:
            continue
        p = (o.get("m") or {}).get("payload") or {}
        if p.get("symbol"):
            feed[p["symbol"].split("/")[0]].append((p["timestamp"] / 1000.0, float(p["value"]), o["rx"]))
for c in feed:
    feed[c] = sorted(set(feed[c]))

ev = defaultdict(list)              # (slug, side) -> (rx, kind, a, b)   kind: 'ask' (ask, size) / 'sell' (price, size)
for f in files(f"{BOOKWS}/*.jsonl*"):
    for line in read(f):
        i = line.find('"a":"')
        if i < 0:
            continue
        t = tok.get(line[i + 5:line.find('"', i + 5)])
        if not t:
            continue
        try:
            o = json.loads(line)
        except ValueError:
            continue
        md = M[t[0]]; end = md["start"] + md["window"]
        if not (end - W - 30 <= o["rx"] <= end):
            continue
        if o.get("t") in ("top", "book") and o.get("top"):
            ev[t].append((o["rx"], "ask", o["top"][0], o["top"][1] or 0.0))
        elif o.get("t") == "ltp" and o.get("side") == "SELL":
            ev[t].append((o["rx"], "sell", float(o["p"]), float(o["s"])))
print(f"windows-sides with book events: {len(ev)}; coins with prints: {sorted(feed)}")


def sigma30(ser):
    r = []; j = 0
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


zcache = {}


def z_series(coin, end, K):
    key = (coin, end)
    if key in zcache:
        return zcache[key]
    ser = [x for x in feed.get(coin, []) if end - 1500 <= x[0] <= end + 5]
    out = []
    if len(ser) >= 200:
        t = end - W
        while t <= end - 1:
            hist = [(ts, v) for ts, v, rx in ser if rx <= t and ts <= end]
            if len(hist) >= 120:
                sg = sigma30(hist[-900:])
                if sg:
                    sg = max(sg, SIGMA_FLOOR.get(coin, 0)); S = hist[-1][1]
                    last = [p for tt, p in hist if tt >= end - 60]
                    g = min(max((t - (end - 60)) / 60.0, 0), 1); A = sum(last) / len(last) if last else S
                    sd = max((1 - g) * S * sg * math.sqrt(max(end - t, 1.0) / 3), 1e-9)
                    x = g * A + (1 - g) * S - K
                    out.append((t, x / sd, x / K * 1e4))
            t += 0.5
    zcache[key] = out
    return out


res = {B: [0, 0, 0.0, 0.0, 0] for B in BIDS}         # windows filled, won, $ spent, pnl, windows with a resting bid
taker = [0, 0, 0.0, 0.0]
fills_log = []
for (slug, side), E in ev.items():
    md = M[slug]; coin = slug.split("-")[0]; end = md["start"] + md["window"]
    zs = z_series(coin, end, md["ptb"])
    if not zs:
        continue
    sign = 1 if side == 0 else -1
    won = (md["up"] is True) if side == 0 else (md["up"] is False)
    E.sort(key=lambda e: e[0])
    timeline = sorted([(t, "z", z * sign, m * sign) for t, z, m in zs] + E, key=lambda e: e[0])
    for B in BIDS:
        on = False; spent = 0.0; shares = 0.0; rested = False
        for e in timeline:
            if e[1] == "z":
                on = e[2] >= Z and e[3] >= MARGIN_MIN
                rested = rested or on
            elif e[1] == "sell" and on and spent < CAP:
                p, sz = e[2], e[3]
                q = sz if p < B else (sz * QUEUE_AT_B if p == B else 0.0)
                q = min(q, (CAP - spent) / B)
                if q > 0:
                    shares += q; spent += q * B
        r = res[B]
        r[4] += rested
        if shares > 0:
            r[0] += 1; r[1] += won; r[2] += spent; r[3] += shares * ((1 if won else 0) - B)
            fills_log.append((B, slug, side, round(shares, 1), won))
    # taker alternative: first moment z >= Z with ask <= ASK_MAX
    on = False; cur = None
    for e in timeline:
        if e[1] == "z":
            on = e[2] >= Z and e[3] >= MARGIN_MIN
        elif e[1] == "ask":
            cur = (e[2], e[3])
        if on and cur and cur[0] is not None and 0.5 <= cur[0] <= ASK_MAX and end - e[0] >= 1:
            a, sz = cur; stake = min(a * sz, CAP)
            if stake > 0:
                taker[0] += 1; taker[1] += won; taker[2] += stake; taker[3] += stake / a * ((1 if won else 0) - a - 0.07 * a * (1 - a))
            break

print(f"\nmaker bid while z >= {Z} and margin >= {MARGIN_MIN} bp in the last {W:.0f} s (fills only from taker SELL prints "
      f"strictly below our bid{'' if not QUEUE_AT_B else f', {QUEUE_AT_B:.0%} of prints at it'}), ${CAP:.0f} cap per window-side:")
for B in BIDS:
    n, w, sp, pnl, rested = res[B]
    print(f"  bid {B:.2f}: windows with the bid resting {rested:5}  filled {n:4} ({n / max(rested, 1):.1%})  won {w / max(n, 1):.1%}  "
          f"spent ${sp:8.1f}  pnl ${pnl:+7.2f} ({pnl / sp if sp else 0:+.1%})")
n, w, sp, pnl = taker
print(f"  taker alternative (first ask <= {ASK_MAX} while z >= {Z}, + fee): windows {n}  won {w / max(n, 1):.1%}  spent ${sp:.1f}  "
      f"pnl ${pnl:+.2f} ({pnl / sp if sp else 0:+.1%})")
losers = [x for x in fills_log if not x[4]]
print(f"  filled-and-lost: {len(losers)}", losers[:12])
