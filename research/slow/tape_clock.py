"""N32 (cycle 13, outside the box): does the informed taker sleep? Maker P&L by the clock of the taker's entry.
LESSONS 17: on Polymarket the passive side pays the informed side. If informed takers are rarer at night (US) and on weekends, a maker
that quotes only in those hours would face mostly uninformed flow. Slots fixed BEFORE looking: weekend (Sat+Sun UTC) vs weekday;
weekday 04-12 UTC (US night) vs weekday 12-04 UTC. Unit: one taker entry (wallet x market x direction, first-trade time t), maker
P&L = taker cost - shares x win (maker fee 0), reported as % of taker cost and in points per share (equal weight per entry),
event-clustered bootstrap, both halves (older / newer 6 weeks), entries >= 1 h before the scheduled end.
Caveat (LESSONS 23): this is the maker's average across ALL prints in the slot, not the fill a single resting quote would get."""
import json, gzip, struct, collections, random, datetime as dt
ROW = struct.Struct("<IIIhfffHHHIB")
B = "data/research/"
random.seed(13)
E = []
for g in "abc":
    meta = json.load(gzip.open(f"{B}entries_{g}_meta.json.gz")); blob = gzip.open(f"{B}entries_{g}.bin.gz").read()
    MK = meta["markets"]
    at = dt.datetime.strptime(meta["at"], "%Y-%m-%d %H:%M").replace(tzinfo=dt.timezone.utc).timestamp(); cut = at - 45 * 86400
    for t, mi, wi, hb, S, C, F, a, a60, a300, lag, fl in ROW.iter_unpack(blob):
        if S <= 0 or C <= 0 or hb < 1:
            continue
        p = C / S
        if not (0.03 <= p <= 0.97):
            continue
        m = MK[mi]
        d = dt.datetime.fromtimestamp(t, dt.timezone.utc)
        wk = d.weekday() >= 5
        night = (not wk) and 4 <= d.hour < 12
        E.append((m[1], m[2], S, C, 1 if fl & 2 else 0, m[4] >= cut, "weekend" if wk else ("wkday_04-12" if night else "wkday_12-04")))
    del blob
print("entries", len(E))


def stat(R):
    ev = collections.defaultdict(lambda: [0.0, 0.0, 0.0, 0])       # maker pnl $, taker cost $, maker pts sum, n
    for e, c, S, C, w, new, slot in R:
        x = ev[e]; x[0] += C - S * w; x[1] += C; x[2] += (C / S) - w; x[3] += 1
    if len(ev) < 10:
        return None
    v = list(ev.values()); n = len(v)
    tot = [sum(x[i] for x in v) for i in range(4)]
    bs = []; bp = []
    for _ in range(400):
        s = [v[int(random.random() * n)] for _i in range(n)]
        bs.append(sum(x[0] for x in s) / sum(x[1] for x in s)); bp.append(sum(x[2] for x in s) / sum(x[3] for x in s))
    bs.sort(); bp.sort()
    return {"entries": tot[3], "events": n, "maker_pct_of_cost": round(100 * tot[0] / tot[1], 2),
            "ci_pct": [round(100 * bs[10], 1), round(100 * bs[389], 1)],
            "maker_pts_per_entry": round(100 * tot[2] / tot[3], 2), "ci_pts": [round(100 * bp[10], 1), round(100 * bp[389], 1)]}


out = {}
cats = sorted({r[1] for r in E})
for c in ["ALL"] + cats:
    Rc = E if c == "ALL" else [r for r in E if r[1] == c]
    for slot in ("weekend", "wkday_04-12", "wkday_12-04"):
        for half, f in (("older", lambda r: not r[5]), ("newer", lambda r: r[5]), ("all", lambda r: True)):
            s = stat([r for r in Rc if r[6] == slot and f(r)])
            if s:
                out[f"{c} | {slot} | {half}"] = s
for k, v in out.items():
    print(f"{k:42} n {v['entries']:8} ev {v['events']:5}  maker {v['maker_pct_of_cost']:+6.2f}% {v['ci_pct']}  pts {v['maker_pts_per_entry']:+6.2f} {v['ci_pts']}")
json.dump(out, open("data/research/tape_clock.json", "w"), indent=0)
