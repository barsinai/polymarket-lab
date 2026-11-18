"""Cycle 37, N83 (outside the box): earthquake markets vs the Gutenberg-Richter (GR) prior.
Polymarket lists daily 'biggest earthquake on <date> be under 5.3 / 5.3-5.4 / ... / 6.1 or more?' ladders and weekly 'how many
M5.5+ / M6.5+ earthquakes worldwide' counts. Before the day / week starts nothing is known except the base rate, which follows a
textbook law: N(>= M) per day ~ 3.97 * 10^-(M - 5) worldwide (USGS ~1,450 M5+ a year, b = 1). Few traders know it; buckets are
narrow; a long-shot / favourite bias in the ladder would show against this prior. (Lesson 13 says a public base rate is priced -
this tests whether that holds where the base rate is a physics law nobody in the crowd looks up.)
Rules fixed BEFORE looking (constants are textbook, not fitted): magnitudes are reported to 0.1, so 'under 5.3' = true max < 5.25,
'5.3 to 5.4' = [5.25, 5.45), 'X or more' = >= X - 0.05. Daily: P(max < x) = exp(-3.97 * 10^-(x-5)) (Poisson, whole UTC day).
Weekly counts: Poisson with mean 7 * 3.97 * 10^-(M-5) (ignores aftershock clustering: the prior is TOO narrow, which favours
the tails; read the tails with that in mind). Rows = taker entries (group b tape) made BEFORE the period starts (daily: before
00:00 UTC of the date; weekly: before the first day), follower price a300 (next print same side >= 300 s later), fee 0 (weather
fee rate is 0 on these markets - checked in meta). One fill per market + side (earliest). Rule: buy the side when GR prob - price
>= 0.05. Edge = win - price, points per share; unit = event (day / week); bootstrap 1,000.
Also: Brier of the market price vs GR on the same entries (YES-equivalent).
DECISION: DEAD if edge <= +1 pt; PARKED-by-count if < 30 events; READY (tracker reading USGS via Actions) only if >= +5 pts with
CI low > 0 and both halves > 0. Exposed to: 13, 9 (is GR better informed than the crowd?), 5 / 22 (count), 26 (intraday read)."""
import json, gzip, struct, collections, random, re, math, datetime as dt
ROW = struct.Struct("<IIIhfffHHHIB")
B = "data/research/"
random.seed(83)
meta = json.load(gzip.open(f"{B}entries_b_meta.json.gz")); MK = meta["markets"]
at = dt.datetime.strptime(meta["at"], "%Y-%m-%d %H:%M").replace(tzinfo=dt.timezone.utc).timestamp()
N5 = 3.97
MON = {m: i + 1 for i, m in enumerate("january february march april may june july august september october november december".split())}


def rate(M):
    return N5 * 10 ** (-(M - 5))


def day_prob(q):
    """P(YES) for a daily-max bucket question, or None."""
    m = re.search(r"biggest earthquake on (\w+) (\d+), (\d{4}) be (under ([\d.]+)|([\d.]+) to ([\d.]+)|([\d.]+) or more)", q, re.I)
    if not m:
        return None, None
    d0 = dt.datetime(int(m.group(3)), MON[m.group(1).lower()], int(m.group(2)), tzinfo=dt.timezone.utc).timestamp()
    F = lambda x: math.exp(-rate(x))                                  # P(max < x)
    if m.group(5):
        p = F(float(m.group(5)) - 0.05)
    elif m.group(6):
        p = F(float(m.group(7)) + 0.05) - F(float(m.group(6)) - 0.05)
    else:
        p = 1 - F(float(m.group(8)) - 0.05)
    return p, d0


def week_prob(slug, q):
    m = re.search(r"how-many-(\d)pt(\d)-or-above-earthquakes-(?:worldwide-)?(\w+)-(\d+)-", slug)
    k = re.search(r"be (\d+|more than (\d+)) earthquakes?", q)
    if not m or not k:
        return None, None
    M = float(f"{m.group(1)}.{m.group(2)}"); lam = 7 * rate(M - 0.05)
    mon = MON.get(m.group(3).lower())
    if not mon:
        return None, None
    d0 = dt.datetime(2026, mon, int(m.group(4)), tzinfo=dt.timezone.utc).timestamp()
    pois = lambda n: math.exp(-lam) * lam ** n / math.factorial(n)
    if k.group(2):
        p = 1 - sum(pois(i) for i in range(int(k.group(2)) + 1))
    else:
        p = pois(int(k.group(1)))
    return p, d0


info = {}
for i, m in enumerate(MK):
    if "earthquake" not in (m[1] + (m[3] or "")).lower() or m[4] >= at:
        continue
    p, d0 = day_prob(m[3] or "")
    kind = "daily"
    if p is None:
        p, d0 = week_prob(m[1], m[3] or ""); kind = "weekly"
    if p is not None:
        info[i] = (p, d0, kind, m[1], m[6], m[7])
blob = gzip.open(f"{B}entries_b.bin.gz").read()
first = {}
for t, mi, wi, hb, S, C, F, a, a60, a300, lag, fl in ROW.iter_unpack(blob):
    if mi not in info or S <= 0:
        continue
    g, d0, kind, ev, y0, fr = info[mi]
    if t >= d0:
        continue
    d = 1 if fl & 1 else -1
    key = (mi, d)
    if key in first and first[key]["t"] <= t:
        continue
    p = a300 / 1e4
    if not 0.01 <= p <= 0.99:
        continue
    q = g if d == 1 else 1 - g
    first[key] = dict(t=t, e=ev, kind=kind, p=p, q=q, win=1 if fl & 2 else 0, yp=p if d == 1 else 1 - p, g=g, y0=y0, fee=fr * p * (1 - p))
del blob
R = list(first.values())


def stat(rr):
    ev = collections.defaultdict(lambda: [0.0, 0])
    for r in rr:
        ev[r["e"]][0] += r["win"] - r["p"] - r["fee"]; ev[r["e"]][1] += 1
    v = list(ev.values()); n = sum(y[1] for y in v)
    if not v:
        return {"n": 0}
    o = {"n": n, "events": len(v), "pts": round(100 * sum(y[0] for y in v) / n, 2)}
    if len(v) >= 5:
        bs = []
        for _ in range(1000):
            s = [v[int(random.random() * len(v))] for _i in v]
            bs.append(sum(y[0] for y in s) / max(1, sum(y[1] for y in s)))
        bs.sort(); o["ci"] = [round(100 * bs[25], 1), round(100 * bs[974], 1)]
    return o


out = {"markets": len(info), "events": len({x[3] for x in info.values()}), "entry_rows": len(R)}
# calibration on the YES-equivalent of each row (one per market: earliest row)
cal = {}
for r in sorted(R, key=lambda r: r["t"]):
    cal.setdefault((r["e"], r["g"]), r)
C = list(cal.values())
if C:
    out["brier market"] = round(sum((c["yp"] - c["y0"]) ** 2 for c in C) / len(C), 4)
    out["brier GR"] = round(sum((c["g"] - c["y0"]) ** 2 for c in C) / len(C), 4)
    out["calibration markets"] = len(C)
sig = [r for r in R if r["q"] - r["p"] >= 0.05]
mid = sorted(r["t"] for r in sig)[len(sig) // 2] if sig else 0
out["rule (GR - price >= 5c)"] = stat(sig)
out["rule halves"] = [stat([r for r in sig if r["t"] < mid]).get("pts"), stat([r for r in sig if r["t"] >= mid]).get("pts")]
for k in ("daily", "weekly"):
    out[f"rule {k}"] = stat([r for r in sig if r["kind"] == k])
out["rule buys YES-tail (GR < 0.20)"] = stat([r for r in sig if r["q"] < 0.20])
out["rule buys >= 0.20"] = stat([r for r in sig if r["q"] >= 0.20])
out["all entries (any side, no rule)"] = stat(R)
s = out["rule (GR - price >= 5c)"]
if s.get("n", 0) == 0 or s["pts"] <= 1:
    out["verdict"] = "DEAD"
elif s["events"] < 30:
    out["verdict"] = "PARKED-by-count"
elif s["pts"] >= 5 and s["ci"][0] > 0 and min(x or -1 for x in out["rule halves"]) > 0:
    out["verdict"] = "READY"
else:
    out["verdict"] = "DEAD"
print(json.dumps(out, indent=1))
json.dump(out, open(f"{B}quake_gr_report.json", "w"), indent=1)
