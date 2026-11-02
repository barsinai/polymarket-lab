"""Logic arbitrage between related date markets ("ladders").

If question A's event is contained in question B's (A: "released on Nov 10", B: "released by
Nov 30"; or A: "by Nov 15", B: "by Nov 30"), then B-Yes pays at least whenever A-Yes pays.
Buying B-Yes and A-No costs ask(B_yes) + ask(A_no) and always pays >= $1 (pays $2 when B
happens but A doesn't). Guaranteed profit per set = 1 - cost when cost < 1.
Scan every recorded hourly book: how often, how big (in dollars actually available at the
best asks), how long the gaps last. Also report *near* misses (cost < 1.02) which a market
maker could capture by quoting rather than taking.
"""
import glob, gzip, json, re, sys, os
from collections import defaultdict
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import collect  # noqa: E402

MONTHS = "january|february|march|april|may|june|july|august|september|october|november|december"
RX_BY = re.compile(rf"\b(?:by|before)\s+({MONTHS})\s+(\d{{1,2}})(?:,?\s*(\d{{4}}))?", re.I)
RX_ON = re.compile(rf"\bon\s+({MONTHS})\s+(\d{{1,2}})(?:,?\s*(\d{{4}}))?", re.I)
RX_BETWEEN = re.compile(rf"\bbetween\s+({MONTHS})\s+(\d{{1,2}})\s+(?:and|-)\s+(?:({MONTHS})\s+)?(\d{{1,2}})(?:,?\s*(\d{{4}}))?", re.I)
RX_IN = re.compile(rf"\bin\s+({MONTHS})(?:\s+(\d{{4}}))?\s*\?", re.I)


def day(mon, d, year=None):
    try:
        return datetime(int(year or 2026), datetime.strptime(mon[:3].title(), "%b").month, int(d)).toordinal()
    except ValueError:
        return None


def parse(q):
    """-> (stem, lo_day, hi_day) interval of dates on which the event must fall, or None"""
    ql = q.strip()
    m = RX_BETWEEN.search(ql)
    if m:
        lo = day(m.group(1), m.group(2), m.group(5)); hi = day(m.group(3) or m.group(1), m.group(4), m.group(5))
        return (RX_BETWEEN.sub("<D>", ql).lower(), lo, hi)
    m = RX_BY.search(ql)
    if m:
        return (RX_BY.sub("<D>", ql).lower(), 0, day(m.group(1), m.group(2), m.group(3)))
    m = RX_ON.search(ql)
    if m:
        d = day(m.group(1), m.group(2), m.group(3)); return (RX_ON.sub("<D>", ql).lower(), d, d)
    m = RX_IN.search(ql)
    if m:
        lo = day(m.group(1), 1, m.group(2)); hi = day(m.group(1), 28, m.group(2))
        return (RX_IN.sub("<D>?", ql).lower(), lo, hi)
    return None


meta = {}
for f in sorted(glob.glob("data/live/meta/*.jsonl.gz")):
    for m in collect.read_jsonl_gz(f):
        meta[m["id"]] = m
NOW_ORD = datetime.utcnow().toordinal()


def parse_with_end(m):
    """Years are often missing ('by March 31' usually means the next March 31 from the time of
    writing): a date without a year that is already > 7 days in the past gets the next year.
    Gamma's endDate can be the whole event's placeholder, so it is NOT used.
    Negated questions ('not IPO by', 'no next model') are skipped."""
    q = m.get("question") or ""
    if re.search(r"\bnot\b|\bno\b|\bno longer\b|\bout as\b|\bbefore\b", q, re.I):
        return None
    p = parse(q)
    if not p or p[2] is None:
        return None
    stem, lo, hi = p
    has_year = bool(re.search(r"\b20\d\d\b", q))
    if not has_year and hi < NOW_ORD - 7:
        lo, hi = (lo + 365 if lo else lo), hi + 365
    return (stem, lo, hi)


P = {mid: parse_with_end(m) for mid, m in meta.items()}
stems = defaultdict(list)
for mid, p in P.items():
    if p and p[1] is not None and p[2] is not None:
        stems[p[0]].append(mid)
stems = {k: v for k, v in stems.items() if len(v) >= 2}
print(f"{sum(len(v) for v in stems.values())} markets in {len(stems)} date ladders")

opps, near = [], []
files = sorted(glob.glob("data/live/20*/*.json.gz"))
for f in files:
    d = json.load(gzip.open(f))
    if "market_columns" not in d:
        continue
    for stem, mids in stems.items():
        live = [m for m in mids if m in d["markets"]]
        for a in live:
            for b in live:
                if a == b:
                    continue
                la, ha = P[a][1], P[a][2]; lb, hb = P[b][1], P[b][2]
                if not (lb <= la and ha <= hb and (la, ha) != (lb, hb)):
                    continue  # need A strictly inside B
                ba_yes = d["books"].get(f"{b}:0"); aa_no = d["books"].get(f"{a}:1")
                if not ba_yes or not ba_yes[3] or not aa_no or not aa_no[3]:
                    continue
                (pb, sb), (pa, sa) = ba_yes[3][0], aa_no[3][0]
                cost = pb + pa
                sets = min(sb, sa)
                rec = {"ts": d["ts"], "cost": round(cost, 3), "sets": sets, "profit_usd": round(sets * (1 - cost), 2),
                       "B": meta[b]["question"], "A": meta[a]["question"]}
                (opps if cost < 0.999 else near if cost < 1.02 else []).append(rec)
by_pair = defaultdict(list)
for o in opps:
    by_pair[(o["A"], o["B"])].append(o)
print(f"\n{len(files)} snapshots; {len(opps)} arbitrage observations in {len(by_pair)} distinct pairs; {len(near)} near-misses (cost 1.00-1.02)")
tot = 0
for k, v in sorted(by_pair.items(), key=lambda x: -max(o["profit_usd"] for o in x[1]))[:12]:
    best = max(v, key=lambda o: o["profit_usd"]); tot += best["profit_usd"]
    print(f"  ${best['profit_usd']:7.2f} once ({len(v)} hours seen, cost {best['cost']:.3f}, {best['sets']:.0f} sets) | A: {k[0][:48]} | B: {k[1][:48]}")
print(f"total if each pair taken once at its best: ${sum(max(o['profit_usd'] for o in v) for v in by_pair.values()):.2f}")
json.dump({"opps": opps[:2000], "near": near[:2000], "ladders": len(stems)}, open("results/ladder_arb.json", "w"))
