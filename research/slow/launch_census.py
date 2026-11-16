"""Cycle 25, N59 (outside the box): NEW MARKET LAUNCHES. Rules fixed here BEFORE looking at outcomes.

Idea: when a market is listed, its first book is seed liquidity quoted around a guess (often the creator's / a market maker's
default). The first takers who actually read the question pick off stale seed quotes; if the seed has depth, a follower who
watches new listings and trades the same way a minute later still gets a good price. Never touched: young markets (N1/N17) looked
at price levels over 72 h, not at the first hour, and not at who trades it.
Exposed to: 1 (listing snipers are bots, the seed may be gone in seconds), 2 (a seed price that survives is right), 17 (most
early takers are small retail), 22 (rule fixed here), 5/6 (one event launches many markets at once -> unit = event).

Data: the 12-week public trade tape (entries_a/b/c: culture, weather (1/3 sample), politics/econ/tech/geo), one entry per
wallet+direction+market, real fills, resolution known.
Launch L = the market's first trade in the tape (all trades of each market are fetched). Markets must live >= 24 h after L.
Arms (entries >= 1 h before the end, follower price 0.05-0.95):
  LAUNCH HOUR    L <= t < L + 1 h                       (decision arm)
  LAUNCH 1-6 h   L + 1 h <= t < L + 6 h
  CONTROL        L + 24 h <= t < L + 72 h
Fill = the next print in the same direction by someone else >= 60 s later (a fill that happened; 'follower'); fee = market fee
rate * p(1-p). Points per share = win - price - fee. Unit = event slug (bootstrap 1,000), also by launch day; halves by L.
Also reported: the takers' own fills (what the first takers earned), YES vs NO direction, first entry of each market.
DEAD if the pooled LAUNCH-HOUR follower <= +1 pt, or its event interval reaches below -1, or the halves disagree in sign.
READY (forward tracker) only if it also beats CONTROL by >= 1 pt in both halves."""
import json, gzip, struct, collections, random, datetime as dt
ROW = struct.Struct("<IIIhfffHHHIB")
B = "data/research/"
random.seed(59)
R = []
for g in "abc":
    meta = json.load(gzip.open(f"{B}entries_{g}_meta.json.gz")); MK = meta["markets"]
    at = dt.datetime.strptime(meta["at"], "%Y-%m-%d %H:%M").replace(tzinfo=dt.timezone.utc).timestamp()
    blob = gzip.open(f"{B}entries_{g}.bin.gz").read()
    L = {}
    for t, mi, *_ in ROW.iter_unpack(blob):
        if mi not in L or t < L[mi]:
            L[mi] = t
    for t, mi, wi, hb, S, C, F, a, a60, a300, lag, fl in ROW.iter_unpack(blob):
        m = MK[mi]; l0 = L[mi]
        if m[4] >= at or S <= 0 or C <= 0 or hb < 1 or m[4] - l0 < 24 * 3600:
            continue
        age = t - l0
        arm = "LAUNCH HOUR" if age < 3600 else "LAUNCH 1-6 h" if age < 6 * 3600 else "CONTROL 24-72 h" if 24 * 3600 <= age < 72 * 3600 else None
        if arm is None:
            continue
        win = 1 if fl & 2 else 0; fee = m[7]
        own = win - C / S - F / S
        p = a60 / 1e4
        fol = win - p - fee * p * (1 - p) if 0.05 <= p <= 0.95 else None
        R.append(dict(g=g, cat=m[2], e=m[1], arm=arm, own=own, fol=fol, c=C, yes=bool(fl & 1), first=(t == l0), l0=l0,
                      day=int(l0 // 86400), m=mi))
    del blob
l_all = sorted(r["l0"] for r in R); mid = l_all[len(l_all) // 2]
for r in R:
    r["half"] = "older" if r["l0"] < mid else "newer"
print("rows", len(R), "launch-hour rows", sum(r["arm"] == "LAUNCH HOUR" for r in R), "mid", dt.datetime.fromtimestamp(mid, dt.timezone.utc))


def stat(rows, key="e", f="fol"):
    ev = collections.defaultdict(lambda: [0.0, 0])
    for r in rows:
        if r[f] is None:
            continue
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
for arm in ("LAUNCH HOUR", "LAUNCH 1-6 h", "CONTROL 24-72 h"):
    A = [r for r in R if r["arm"] == arm]
    out[f"{arm} | follower by event"] = stat(A)
    out[f"{arm} | own fill by event"] = stat(A, f="own")
    for h in ("older", "newer"):
        out[f"{arm} | follower {h} half"] = stat([r for r in A if r["half"] == h])
    for g in "abc":
        out[f"{arm} | follower group {g}"] = stat([r for r in A if r["g"] == g])
    if arm == "LAUNCH HOUR":
        out[f"{arm} | follower by launch day"] = stat(A, "day")
        out[f"{arm} | follower YES side"] = stat([r for r in A if r["yes"]])
        out[f"{arm} | follower NO side"] = stat([r for r in A if not r["yes"]])
        out[f"{arm} | very first entry, follower"] = stat([r for r in A if r["first"]])
        out[f"{arm} | very first entry, own"] = stat([r for r in A if r["first"]], f="own")
        out[f"{arm} | own >= $200 (lookahead)"] = stat([r for r in A if r["c"] >= 200], f="own")
        out[f"{arm} | own < $10"] = stat([r for r in A if r["c"] < 10], f="own")
        for c_ in sorted({r["cat"] for r in A}):
            out[f"{arm} | follower cat {c_}"] = stat([r for r in A if r["cat"] == c_])
print(json.dumps(out, indent=1))
json.dump(out, open(f"{B}launch_report.json", "w"), indent=1)
