"""Young-market NO, history re-check at EXECUTABLE prices (research cycle 11-12 evening). NO ORDERS.
The history said: young stand-alone non-sports binaries priced YES 0.30-0.50 resolve YES ~24%. History prices are mids
(LESSONS 3). The paper tracker (young_paper.py) measured the real NO ask over the NO mid: median +10.5c (n 36).
This script: same history set, first observed price within 72 h of the start, YES 0.30-0.50; return of buying NO at
(1 - p) + h with h = 0 / 0.05 / 0.105 and fee 0.07*q*(1-q); split by question type (path-dependent 'hit/reach/by/before'
questions, which resolve YES early, vs fixed-date); counted per EVENT (independent unit) and per half-year (replication).
Usage: python3 research/slow/young_exec_history.py  -> prints a table, writes data/research/young_exec_history.json"""
import json, os, re, collections

H = "data/history"
SPORT = re.compile(r"\b(vs\.?|nba|nfl|nhl|mlb|ncaa|ufc|mma|premier|la liga|serie a|bundesliga|ligue|champions|europa|mls|atp|wta|tennis|open|cup|league|match|game|win on|spread|o/u|over/under|f1|grand prix|boxing|fight|cricket|rugby|golf|pga|nascar|esports|lol|cs2|dota|valorant)\b", re.I)
SKIP = re.compile(r"updown|up-or-down|-5m-|-15m-|-4h-|highest-temperature", re.I)
PATH = re.compile(r"\b(hit|reach|by|before|dip|touch|announce|announced)\b", re.I)


def ts(s):
    import datetime as dt
    return dt.datetime.fromisoformat(s).replace(tzinfo=dt.timezone.utc).timestamp()


rows = []
for l in open(f"{H}/markets.jsonl"):
    m = json.loads(l)
    if m.get("neg_risk") or SPORT.search(m["question"]) or SKIP.search(m["slug"]) or m.get("yes_won") not in (0, 1):
        continue
    f = f"{H}/prices/{m['id']}.json"
    if not os.path.exists(f) or not m.get("start"):
        continue
    pr = json.load(open(f))
    t0 = ts(m["start"])
    first = [p for t, p in pr if t0 <= t <= t0 + 72 * 3600]
    if not first:
        continue
    p = first[0]
    if not 0.30 <= p <= 0.50:
        continue
    rows.append(dict(id=m["id"], ev=m.get("event") or m["question"], q=m["question"], p=p, y=m["yes_won"],
                     typ="path" if PATH.search(m["question"]) else "fixed", half=m["start"][:4] + ("H1" if m["start"][5:7] <= "06" else "H2")))


def ret(r, h):
    q = min(0.99, 1 - r["p"] + h)
    fee = 0.07 * q * (1 - q)
    return ((1 - r["y"]) - q - fee) / q


out = {}
for name, sel in [("all", lambda r: True), ("path", lambda r: r["typ"] == "path"), ("fixed", lambda r: r["typ"] == "fixed")] + \
        [(hf, (lambda hf: lambda r: r["half"] == hf)(hf)) for hf in sorted({r["half"] for r in rows})]:
    s = [r for r in rows if sel(r)]
    if not s:
        continue
    evs = collections.defaultdict(list)
    for r in s:
        evs[r["ev"]].append(r)
    res = {"n": len(s), "events": len(evs), "mean_p": round(sum(r["p"] for r in s) / len(s), 3),
           "yes_rate": round(sum(r["y"] for r in s) / len(s), 3)}
    for h in (0, 0.05, 0.105):
        # per event: average return of its markets (one bet per event)
        per_ev = [sum(ret(r, h) for r in v) / len(v) for v in evs.values()]
        res[f"ret_h{h}"] = round(100 * sum(per_ev) / len(per_ev), 1)
    out[name] = res
    print(name, res)
os.makedirs("data/research", exist_ok=True)
json.dump(out, open("data/research/young_exec_history.json", "w"), indent=1)
