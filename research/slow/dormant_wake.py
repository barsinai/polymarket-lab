"""Cycle 48, N104 (outside the box): the first taker in a DORMANT market.
Why the crowd could be wrong: no bot or market maker watches a market nobody has touched for two days; whoever trades it first after a
long silence usually came because something happened (news, a source update) - the wake-up trade is a news alarm in a market where the
book is stale. If so, following the waker's direction at the next print should keep an edge (the stale book is not re-priced by bots).
Lesson 27 warns: anecdotes of 'someone knew' are the visible tail; this measures the base rate.
Rules fixed BEFORE looking (written here first): tapes a + b + c, finished markets. Activity = every first entry (wallet, market,
direction) in entries_<g> plus every big order (>= $100) in orders_<g> (repeat small trades by a wallet are NOT in the tape -> the silence
is 'no new trader and no $100+ order'; caveat). A WAKE is an entry row whose time is >= 48 h after the market's previous activity, with the
market's first activity >= 72 h earlier and >= 24 h left to its end. Placebo: gap 6-24 h (same rule otherwise). The waker's direction,
follower fill a300 in 0.05-0.95, fee rate * p(1-p) paid; first qualifying wake per market per arm. Unit = event, bootstrap 1,000, halves.
DECISION: paper only if WAKE >= +3 pts, CI low > 0, >= 50 events, halves >= +1.5, WAKE - PLACEBO >= +2. If WAKE <= -3 under the same
rules a fade is NOT computable here (the other side's ask is not in the tape) -> note only. Printed: waker's own fill, gap >= 7 d,
big waker (>= $200). Exposed to 27, 22, 24, 2, 5/6."""
import json, gzip, struct, collections, random, datetime as dt, bisect
ROW = struct.Struct("<IIIhfffHHHIB"); ROW2 = struct.Struct("<IIIhffHHHHHIffB")
B = "data/research/"
random.seed(104)
R = []
for g in "abc":
    meta = json.load(gzip.open(f"{B}entries_{g}_meta.json.gz")); MK = meta["markets"]
    at = dt.datetime.strptime(meta["at"], "%Y-%m-%d %H:%M").replace(tzinfo=dt.timezone.utc).timestamp()
    act = collections.defaultdict(list); ent = collections.defaultdict(list)
    for t, mi, wi, hb, S, C, F, a, a60, a300, lag, fl in ROW.iter_unpack(gzip.open(f"{B}entries_{g}.bin.gz").read()):
        if MK[mi][4] >= at: continue
        act[mi].append(t); ent[mi].append((t, C, a, a300, fl))
    for r in ROW2.iter_unpack(gzip.open(f"{B}orders_{g}.bin.gz").read()):
        if MK[r[1]][4] < at: act[r[1]].append(r[0])
    for mi, E in ent.items():
        m = MK[mi]; A = sorted(act[mi]); first = A[0]; done = set()
        for t, C, a, a300, fl in sorted(E):
            k = bisect.bisect_left(A, t)
            if k == 0: continue
            gap = (t - A[k - 1]) / 3600
            arm = "WAKE" if gap >= 48 else "PLACEBO" if 6 <= gap <= 24 else None
            if arm is None or arm in done or t - first < 72 * 3600 or m[4] - t < 24 * 3600 or a300 <= 0: continue
            p = a300 / 1e4
            if not 0.05 <= p <= 0.95: continue
            done.add(arm)
            won = 1 if fl & 2 else 0; q = a / 1e4
            R.append(dict(e=f"{g}:{m[1]}", g=g, end=m[4], arm=arm, gap=gap, c=C, yes=fl & 1,
                          f=won - p - m[7] * p * (1 - p), own=won - q - m[7] * q * (1 - q)))


def stat(rr, key="f"):
    ev = collections.defaultdict(lambda: [0.0, 0])
    for r in rr:
        ev[r["e"]][0] += r[key]; ev[r["e"]][1] += 1
    E = list(ev.values())
    if len(E) < 3: return dict(n=len(rr), events=len(E))
    tot = lambda S: 100 * sum(s for s, _ in S) / sum(n for _, n in S)
    bs = sorted(tot([random.choice(E) for _ in E]) for _ in range(1000))
    return dict(n=len(rr), events=len(E), pts=round(tot(E), 2), ci=[round(bs[25], 2), round(bs[975], 2)])


out = {}
for arm in ("WAKE", "PLACEBO"):
    rr = [r for r in R if r["arm"] == arm]
    if not rr: continue
    med = sorted(r["end"] for r in rr)[len(rr) // 2]
    out[arm] = dict(all=stat(rr), older=stat([r for r in rr if r["end"] < med]), newer=stat([r for r in rr if r["end"] >= med]),
                    own_fill=stat(rr, "own"), yes_side=stat([r for r in rr if r["yes"]]), no_side=stat([r for r in rr if not r["yes"]]),
                    **{f"group_{g}": stat([r for r in rr if r["g"] == g]) for g in "abc"})
w = [r for r in R if r["arm"] == "WAKE"]
out["WAKE gap>=7d"] = stat([r for r in w if r["gap"] >= 168])
out["WAKE big (>= $200)"] = stat([r for r in w if r["c"] >= 200])
W, P = out.get("WAKE", {}), out.get("PLACEBO", {})
ok = (W and W["all"].get("events", 0) >= 50 and W["all"]["pts"] >= 3 and W["all"]["ci"][0] > 0
      and W["older"].get("pts", -9) >= 1.5 and W["newer"].get("pts", -9) >= 1.5 and W["all"]["pts"] - P["all"]["pts"] >= 2)
out["verdict"] = "PAPER" if ok else "DEAD"
json.dump(out, open("data/research/dormant_wake_report.json", "w"), indent=1)
print(json.dumps({k: (v if not isinstance(v, dict) or "all" not in v else {kk: vv for kk, vv in v.items()}) for k, v in out.items()}))
