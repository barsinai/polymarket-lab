"""Cycle 54, N116 (adjacent to the big-taker base rate, lessons 17 / 30 / 31): follow a big taker who arrives OFF-HOURS.
Why the crowd could be wrong: the first big taker in a market is +2.5 pts at the follower's a300 fill (N105 FIRST arm) - the only
size signal that held. At US night (04-12 UTC on weekdays) and on weekends fewer makers and followers are awake, so a big ticket
that lands then may sit longer before the book re-prices: the follower's a300 print should be closer to the informed price than in
US trading hours. Never split anything by clock time before (CYCLE brainstorm: time-of-day / weekend liquidity).
Exposed to 22 (a split = forking paths: rules fixed here and a second period is scored), 24 (halves), 23 (simulate the follower's
fill), 30 (calm vs urgent), 5/6 (event-clustered), 1 (the slow book may also be the stale one).
Rules fixed BEFORE looking (written here first): tapes a + b + c (canonical, finished markets) and, as the second period, the oos1
tapes scored only on condition ids NOT in the canonical tapes. Big entry = first-entry row with cost >= $200 and own fill
0.05-0.95; per market + direction the EARLIEST big entry; >= 1 h left to the scheduled end; follower fill a300 (next same-way print
by someone else >= 300 s later) in 0.05-0.95, fee rate * p(1-p) paid. Clock of the big entry (UTC): OFF = Sat / Sun any hour, or
Mon-Fri 04:00-11:59; ON = Mon-Fri 13:00-21:59; MID = the rest (printed only). Unit = event slug, bootstrap 1,000, halves by end.
DECISION -> paper arm in the follow chain only if OFF >= +3 pts, CI low > 0, >= 150 events, both halves >= +1.5, OFF - ON >= +1.5,
and on the oos1 markets OFF >= +1.5 and OFF - ON >= +1. Also printed: weekday-night and weekend alone, per group, median a300 lag
(is the follower really later off-hours?), own-fill points."""
import json, gzip, struct, collections, random, datetime as dt
ROW = struct.Struct("<IIIhfffHHHIB")
B = "data/research/"
random.seed(116)


def clock(t):
    d = dt.datetime.fromtimestamp(t, dt.timezone.utc)
    if d.weekday() >= 5: return "OFF", "weekend"
    if 4 <= d.hour < 12: return "OFF", "night"
    if 13 <= d.hour < 22: return "ON", "on"
    return "MID", "mid"


def load(tag, skip_ids=None):
    R = []
    for g in "abc":
        meta = json.load(gzip.open(f"{B}entries_{g}{tag}_meta.json.gz")); MK = meta["markets"]
        at = dt.datetime.strptime(meta["at"], "%Y-%m-%d %H:%M").replace(tzinfo=dt.timezone.utc).timestamp()
        first = {}
        for t, mi, wi, hb, S, C, F, a, a60, a300, lag, fl in ROW.iter_unpack(gzip.open(f"{B}entries_{g}{tag}.bin.gz").read()):
            m = MK[mi]
            if m[4] >= at or C < 200 or not 500 <= a <= 9500: continue
            if skip_ids is not None and m[0] in skip_ids[g]: continue
            k = (mi, fl & 1)
            if k not in first or t < first[k][0]: first[k] = (t, a, a300, lag, fl)
        for (mi, d), (t, a, a300, lag, fl) in first.items():
            m = MK[mi]
            if m[4] - t < 3600 or not 500 <= a300 <= 9500: continue
            p = a300 / 1e4; q = a / 1e4; won = 1 if fl & 2 else 0
            arm, sub = clock(t)
            R.append(dict(e=f"{g}:{m[1]}", g=g, end=m[4], arm=arm, sub=sub, lag=lag,
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
    for arm in ("OFF", "ON", "MID"):
        rr = [r for r in R if r["arm"] == arm]
        if not rr: continue
        lags = sorted(r["lag"] for r in rr)
        out[arm] = dict(all=stat(rr), older=stat([r for r in rr if r["end"] < med]), newer=stat([r for r in rr if r["end"] >= med]),
                        own_fill=stat(rr, "own"), median_a300_lag_s=lags[len(lags) // 2],
                        **{f"group_{g}": stat([r for r in rr if r["g"] == g]) for g in "abc"})
    for sub in ("night", "weekend"):
        out[f"OFF {sub} only"] = stat([r for r in R if r["sub"] == sub])
    return out


canon = load("")
seen = {g: {m[0] for m in json.load(gzip.open(f"{B}entries_{g}_meta.json.gz"))["markets"]} for g in "abc"}
oos = load("_oos1", seen)
out = {"rule": "first big (>= $200) taker per market+direction, follower a300, OFF = weekend or Mon-Fri 04-12 UTC, ON = Mon-Fri 13-22 UTC",
       "canonical": block(canon), "oos1_unseen": block(oos)}
c, o = out["canonical"], out["oos1_unseen"]
try:
    off, on = c["OFF"], c["ON"]
    ok = (off["all"]["pts"] >= 3 and off["all"]["ci"][0] > 0 and off["all"]["events"] >= 150 and off["older"]["pts"] >= 1.5
          and off["newer"]["pts"] >= 1.5 and off["all"]["pts"] - on["all"]["pts"] >= 1.5
          and o["OFF"]["all"]["pts"] >= 1.5 and o["OFF"]["all"]["pts"] - o["ON"]["all"]["pts"] >= 1)
except (KeyError, TypeError):
    ok = False
out["decision"] = "PASS -> paper arm" if ok else "DEAD"
json.dump(out, open(f"{B}offhours_big_report.json", "w"), indent=1)
print(json.dumps(out, indent=1))
