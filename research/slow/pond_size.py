"""Cycle 55, N118 (adjacent to the big-taker base rate, lessons 17 / 30 / 31): a big ticket in a SMALL pond.
Why the crowd could be wrong: the first big taker per market is +2.5 pts at the follower's a300 fill (N105 FIRST arm), the one size
signal that held. A $200 ticket means little in a market that already traded $2M, but a lot in one that traded $600: the information
per ticket should scale with the ticket's share of the market so far, and a thin market has fewer followers to re-price it before a300.
All splits so far were absolute size or clock; this is size RELATIVE to the market, measured with only the past (volp = taker $ traded
in the market before the order, a knowable count - lesson 16 forbids final volume).
Exposed to 22 (a split -> rules fixed here, oos1 unseen ids scored as a second period), 24 (halves), 23 (follower fill), 16 (volume up
to t only), 5/6 (event-clustered), 2 (thin markets may be thin for a reason).
Rules fixed BEFORE looking (written here first): big-order rows (orders_<g>.bin.gz, aggregated taker orders) tapes a + b + c, finished
markets, cost >= $200, >= 1 h before the scheduled end, volp >= $500 (a pond exists), follower a300 in 0.05-0.95, fee rate * p(1-p) paid.
Per market + direction the EARLIEST such order. share = c / (volp + c). Arms: BIG_FISH share >= 0.25; SMALL_FISH share <= 0.02;
MID the rest (printed). Unit = event slug, bootstrap 1,000, halves by end.
DECISION -> paper arm in the follow chain only if BIG_FISH >= +3 pts, CI low > 0, >= 150 events, both halves >= +1.5,
BIG_FISH - SMALL_FISH >= +2, and on oos1 (condition ids not in the canonical tapes) BIG_FISH >= +1.5 and BIG_FISH - SMALL_FISH >= +1.
Printed, not used to pass: share >= 0.50, own fill (aavg) points, median a300 lag."""
import json, gzip, struct, collections, random, datetime as dt
ROW2 = struct.Struct("<IIIhffHHHHHIffB")
B = "data/research/"
random.seed(118)


def load(tag, skip=None):
    R = []
    for g in "abc":
        meta = json.load(gzip.open(f"{B}entries_{g}{tag}_meta.json.gz")); MK = meta["markets"]
        at = dt.datetime.strptime(meta["at"], "%Y-%m-%d %H:%M").replace(tzinfo=dt.timezone.utc).timestamp()
        first = {}
        for row in ROW2.iter_unpack(gzip.open(f"{B}orders_{g}{tag}.bin.gz").read()):
            t, mi, wi, hb, c, sh, aavg, amax, aprev, a60, a300, lag, volp, cumw, fl = row
            m = MK[mi]
            if m[4] >= at or c < 200 or volp < 500 or m[4] - t < 3600: continue
            if skip is not None and m[0] in skip[g]: continue
            k = (mi, fl & 1)
            if k not in first or t < first[k][0]: first[k] = (t, c, aavg, a300, lag, volp, fl)
        for (mi, d), (t, c, aavg, a300, lag, volp, fl) in first.items():
            m = MK[mi]
            p = a300 / 1e4
            if a300 <= 0 or not 0.05 <= p <= 0.95: continue
            q = aavg / 1e4; won = 1 if fl & 2 else 0
            share = c / (volp + c)
            arm = "BIG_FISH" if share >= 0.25 else "SMALL_FISH" if share <= 0.02 else "MID"
            R.append(dict(e=f"{g}:{m[1]}", g=g, end=m[4], arm=arm, share=share, lag=lag,
                          f=won - p - m[7] * p * (1 - p), own=won - q - m[7] * q * (1 - q)))
    return R


def stat(rr, key="f"):
    ev = collections.defaultdict(lambda: [0.0, 0])
    for r in rr:
        ev[r["e"]][0] += r[key]; ev[r["e"]][1] += 1
    E = list(ev.values())
    if len(E) < 3: return dict(n=len(rr), events=len(E))
    tot = lambda S: 100 * sum(s for s, _ in S) / sum(n for _, n in S)
    bs = sorted(tot([random.choice(E) for _ in E]) for _ in range(1000))
    return dict(n=len(rr), events=len(E), pts=round(tot(E), 2), ci=[round(bs[25], 2), round(bs[975], 2)])


def block(R):
    out = {}
    med = sorted(r["end"] for r in R)[len(R) // 2] if R else 0
    for arm in ("BIG_FISH", "SMALL_FISH", "MID"):
        rr = [r for r in R if r["arm"] == arm]
        if not rr: continue
        lags = sorted(r["lag"] for r in rr)
        out[arm] = dict(all=stat(rr), older=stat([r for r in rr if r["end"] < med]), newer=stat([r for r in rr if r["end"] >= med]),
                        own_fill=stat(rr, "own"), median_a300_lag_s=lags[len(lags) // 2],
                        **{f"group_{g}": stat([r for r in rr if r["g"] == g]) for g in "abc"})
    out["share >= 0.50"] = stat([r for r in R if r["share"] >= 0.5])
    return out


canon = load("")
seen = {g: {m[0] for m in json.load(gzip.open(f"{B}entries_{g}_meta.json.gz"))["markets"]} for g in "abc"}
oos = load("_oos1", seen)
out = {"rule": "first >= $200 taker order per market+direction with volp >= $500, share = c/(volp+c); BIG_FISH >= 0.25, SMALL_FISH <= 0.02; follower a300",
       "canonical": block(canon), "oos1_unseen": block(oos)}
c, o = out["canonical"], out["oos1_unseen"]
try:
    bf, sf = c["BIG_FISH"]["all"], c["SMALL_FISH"]["all"]
    ok = (bf["pts"] >= 3 and bf["ci"][0] > 0 and bf["events"] >= 150 and c["BIG_FISH"]["older"]["pts"] >= 1.5
          and c["BIG_FISH"]["newer"]["pts"] >= 1.5 and bf["pts"] - sf["pts"] >= 2
          and o["BIG_FISH"]["all"]["pts"] >= 1.5 and o["BIG_FISH"]["all"]["pts"] - o["SMALL_FISH"]["all"]["pts"] >= 1)
except (KeyError, TypeError):
    ok = False
out["decision"] = "PASS -> paper arm" if ok else "DEAD"
json.dump(out, open(f"{B}pond_size_report.json", "w"), indent=1)
print(json.dumps(out, indent=1))
