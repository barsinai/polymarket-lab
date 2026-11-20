"""Cycle 48, N103 (adjacent to COPY-1 / lesson 17): URGENT big takers - orders >= $200 that paid well above the last same-way print.
Why the crowd could be wrong: lesson 17 says big takers are informed on average (+1.2 pts at $200-1,000) but following them at the next
print keeps ~0.5 (N80). An order that SWEEPS the book (its worst fill >= 5c above the previous same-way print by someone else) is a trader
who would not wait - urgency is the classic sign of private information; a big order that fills at the last print is a patient rebalancer.
If urgency carries the information, the urgent subset should keep an edge at the follower's fill even after the price jump it caused.
Rules fixed BEFORE looking (written here first): big-order rows (orders_<g>.bin.gz, aggregated taker orders >= $100) on tapes a + b + c,
finished markets, cost >= $200, aprev > 0 (a same-way print by another wallet in the 24 h before), >= 1 h before end, follower fill a300
(next same-way print by someone else >= 300 s later) in 0.05-0.95, fee rate * p(1-p) paid.
Arms: URGENT amax - aprev >= 0.05; CALM amax - aprev <= 0.01 (placebo / base rate). First qualifying order per market per arm.
Unit = event (bootstrap 1,000), halves by end date, also by group.
DECISION: paper arm only if URGENT >= +2 pts, CI low > 0, >= 50 events, both halves >= +1, URGENT - CALM >= +1.5. Printed, not used to
pass: sweep >= 0.10, $1,000+, own fill (aavg) edge. Exposed to 1 (the jump is public: a300 is after it), 22, 23, 24, 5/6."""
import json, gzip, struct, collections, random, datetime as dt
ROW2 = struct.Struct("<IIIhffHHHHHIffB")
B = "data/research/"
random.seed(103)
R = []
for g in "abc":
    meta = json.load(gzip.open(f"{B}entries_{g}_meta.json.gz")); MK = meta["markets"]
    at = dt.datetime.strptime(meta["at"], "%Y-%m-%d %H:%M").replace(tzinfo=dt.timezone.utc).timestamp()
    blob = gzip.open(f"{B}orders_{g}.bin.gz").read()
    done = set()
    rows = sorted(ROW2.iter_unpack(blob), key=lambda r: r[0])
    for t, mi, wi, hb, c, sh, aavg, amax, aprev, a60, a300, lag, volp, cumw, fl in rows:
        m = MK[mi]
        if m[4] >= at or c < 200 or aprev <= 0 or a300 <= 0 or m[4] - t < 3600: continue
        p = a300 / 1e4
        if not 0.05 <= p <= 0.95: continue
        sweep = (amax - aprev) / 1e4
        arm = "URGENT" if sweep >= 0.05 else "CALM" if sweep <= 0.01 else None
        if arm is None or (mi, arm) in done: continue
        done.add((mi, arm))
        won = 1 if fl & 2 else 0
        q = aavg / 1e4
        R.append(dict(e=f"{g}:{m[1]}", g=g, end=m[4], arm=arm, c=c, sweep=sweep,
                      f=won - p - m[7] * p * (1 - p), own=won - q - m[7] * q * (1 - q)))
    del blob, rows


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
for arm in ("URGENT", "CALM"):
    rr = [r for r in R if r["arm"] == arm]
    if not rr: continue
    med = sorted(r["end"] for r in rr)[len(rr) // 2]
    out[arm] = dict(all=stat(rr), older=stat([r for r in rr if r["end"] < med]), newer=stat([r for r in rr if r["end"] >= med]),
                    own_fill=stat(rr, "own"), **{f"group_{g}": stat([r for r in rr if r["g"] == g]) for g in "abc"})
u = [r for r in R if r["arm"] == "URGENT"]
out["URGENT sweep>=0.10"] = stat([r for r in u if r["sweep"] >= 0.10])
out["URGENT $1000+"] = stat([r for r in u if r["c"] >= 1000])
U, C = out.get("URGENT", {}), out.get("CALM", {})
ok = (U and U["all"].get("events", 0) >= 50 and U["all"]["pts"] >= 2 and U["all"]["ci"][0] > 0
      and U["older"].get("pts", -9) >= 1 and U["newer"].get("pts", -9) >= 1 and U["all"]["pts"] - C["all"]["pts"] >= 1.5)
out["verdict"] = "PAPER" if ok else "DEAD"
json.dump(out, open("data/research/urgent_taker_report.json", "w"), indent=1)
print(json.dumps(out, indent=1))
