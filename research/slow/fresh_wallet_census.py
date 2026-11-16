"""Cycle 24, two pre-registered tests on the 12-week public trade tape (rules fixed here BEFORE looking at outcomes).

N56 (outside the box): the insider footprint. Famous Polymarket insider cases (a new wallet that buys one political / geopolitical
  outcome big, days before the news) suggest the informed often trade from FRESH wallets. A fresh wallet is knowable at the time it
  trades (we watch the public feed; its address has never traded before). Never tested: COPY-1 follows wallets WITH a record; fresh
  ones have none. Why the crowd could be wrong: a first trade by an unknown address looks like retail noise. Exposed to 17 (most new
  accounts are small retail - they lose), 22 (forking; rule fixed here), 5/6 (one news event = one bet), 1 (others watch for this too).
  Groups: c (politics, geopolitics, ai/tech, economy).
N57 (adjacent to COPY-1 / lesson 17): the same rule in the culture categories (group a: mention, movies, music, youtube, awards,
  pop-culture) where the tape says informed takers are paid most clearly.
Rules (both):
  fresh entry = the wallet's FIRST entry anywhere in the tape (groups a, b, c by address), at least 21 days after the tape start (so
  'fresh' means no activity in these categories for 3+ weeks), and >= 1 h before the market's end.
  Follower fill = the next print in the same direction by someone else >= 60 s later (a fill that really happened), fee 0.07 p(1-p)
  style (market fee rate), price 0.05-0.95. Points per share = win - price - fee. Unit = event slug; also by end day.
  Arms: FRESH all sizes (decision arm); FRESH total cost >= $500 (LOOKAHEAD upper bound: total cost includes the wallet's later adds);
  controls: OLD wallets all sizes, OLD >= $500.
  DEAD if FRESH-all follower <= +1 pt, or its event interval reaches below -1, or the two halves (by entry date) disagree in sign;
  decisively dead if even the >= $500 upper bound is <= +1.5 pts.
Known gap: a wallet may be old on sports/crypto (not in this tape) -> 'fresh' is 'fresh to these categories'."""
import json, gzip, struct, collections, random, datetime as dt
ROW = struct.Struct("<IIIhfffHHHIB")
B = "data/research/"
random.seed(56)
first = {}           # address -> first entry time across all groups
metas = {}
for g in "abc":
    meta = json.load(gzip.open(f"{B}entries_{g}_meta.json.gz")); metas[g] = meta
    W = meta["wallets"]
    blob = gzip.open(f"{B}entries_{g}.bin.gz").read()
    for t, mi, wi, *_ in ROW.iter_unpack(blob):
        a = W[wi]
        if a not in first or t < first[a]:
            first[a] = t
    del blob
at = dt.datetime.strptime(metas["c"]["at"], "%Y-%m-%d %H:%M").replace(tzinfo=dt.timezone.utc).timestamp()
start = min(first.values()); fresh_from = start + 21 * 86400; mid = (fresh_from + at) / 2
print("tape start", dt.datetime.fromtimestamp(start, dt.timezone.utc), "fresh_from", dt.datetime.fromtimestamp(fresh_from, dt.timezone.utc),
      "wallets", len(first))


def load(g):
    meta = metas[g]; MK = meta["markets"]; W = meta["wallets"]; R = []
    blob = gzip.open(f"{B}entries_{g}.bin.gz").read()
    for t, mi, wi, hb, S, C, F, a, a60, a300, lag, fl in ROW.iter_unpack(blob):
        m = MK[mi]
        if m[4] >= at or S <= 0 or C <= 0 or t < fresh_from or hb < 1:
            continue
        p = a60 / 1e4
        if not (0.05 <= p <= 0.95):
            continue
        win = 1 if fl & 2 else 0
        R.append(dict(e=m[1], cat=m[2], day=int(m[4] // 86400), fresh=first[W[wi]] == t, c=C, pts=win - p - m[7] * p * (1 - p),
                      own=win - C / S - F / S, half="older" if t < mid else "newer", hb=hb))
    del blob
    return R


def stat(rows, key="e", f="pts"):
    ev = collections.defaultdict(lambda: [0.0, 0])
    for r in rows:
        ev[r[key]][0] += r[f]; ev[r[key]][1] += 1
    v = list(ev.values()); n = sum(y[1] for y in v)
    if len(v) < 5:
        return {"n": n, "units": len(v)}
    bs = []
    for _ in range(1000):
        s = [v[int(random.random() * len(v))] for _i in v]
        bs.append(sum(y[0] for y in s) / max(1, sum(y[1] for y in s)))
    bs.sort()
    return {"n": n, "units": len(v), "pts": round(100 * sum(y[0] for y in v) / n, 2), "ci": [round(100 * bs[25], 1), round(100 * bs[974], 1)],
            "units_pos": sum(1 for y in v if y[0] > 0)}


out = {}
for name, g in (("N56 politics/geo/tech/econ", "c"), ("N57 culture", "a")):
    R = load(g)
    arms = {"FRESH all": [r for r in R if r["fresh"]], "FRESH >=$500 (lookahead UB)": [r for r in R if r["fresh"] and r["c"] >= 500],
            "OLD all": [r for r in R if not r["fresh"]], "OLD >=$500": [r for r in R if not r["fresh"] and r["c"] >= 500]}
    for k, v in arms.items():
        out[f"{name} | {k} follower by event"] = stat(v)
    fa = arms["FRESH all"]; fb = arms["FRESH >=$500 (lookahead UB)"]
    out[f"{name} | FRESH all by end day"] = stat(fa, "day")
    out[f"{name} | FRESH all own fill"] = stat(fa, f="own")
    for h in ("older", "newer"):
        out[f"{name} | FRESH all {h} half"] = stat([r for r in fa if r["half"] == h])
        out[f"{name} | FRESH >=$500 {h} half"] = stat([r for r in fb if r["half"] == h])
    for c_ in sorted({r["cat"] for r in fa}):
        out[f"{name} | FRESH all cat {c_}"] = stat([r for r in fa if r["cat"] == c_])
        out[f"{name} | FRESH >=$500 cat {c_}"] = stat([r for r in fb if r["cat"] == c_])
    out[f"{name} | FRESH >=$500 by end day"] = stat(fb, "day")
    out[f"{name} | FRESH >=$500 >= 24 h before end"] = stat([r for r in fb if r["hb"] >= 24])
    del R
print(json.dumps(out, indent=1))
json.dump(out, open(f"{B}fresh_wallet_report.json", "w"), indent=1)
