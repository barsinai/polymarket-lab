"""Cycle 41, N90 (adjacent to N58 / N82 / N52): 'another X by <date>' relists. Some series re-list right after the thing happened
('OpenAI reports another AI sandbox escape by Oct 15', 'another ChatGPT outage', 'Russia targets Kyiv again by ...'). Story: the
crowd has just watched it happen (recency), so on the fresh relist the near rungs' YES is overbid and NO is cheap.
Rules fixed BEFORE looking. Rows: tape groups a + c, finished markets (end < tape date), question has 'another' or 'again'
(RELIST); reference = all other markets of the same groups (OTHER). Entry window = launch day: first taker entry per market and
side within 24 h of the market's first trade L, market lives >= 48 h after L. Follower fill = next print the same way >= 300 s
later (a300), 0.05-0.95, fee = rate * p(1-p). Unit = event slug (bootstrap 1,000); halves by end date.
DECISION (tracker arm in launch_paper): RELIST NO >= +3 pts, CI low > 0, >= 30 events, both halves > 0, and above OTHER NO by >= 2.
Otherwise DEAD. YES side printed as the mirror. Exposed to 11 (path questions: finished only), 13 (the series' history is public),
5/6 (one series = one bet: also by family = slug without the date), 24 (halves), 22 (a single split fixed here)."""
import json, gzip, struct, collections, random, re, datetime as dt
ROW = struct.Struct("<IIIhfffHHHIB")
B = "data/research/"
random.seed(90)
RE = re.compile(r"\b(another|again)\b", re.I)
R = []
for g in "ac":
    meta = json.load(gzip.open(f"{B}entries_{g}_meta.json.gz")); MK = meta["markets"]
    at = dt.datetime.strptime(meta["at"], "%Y-%m-%d %H:%M").replace(tzinfo=dt.timezone.utc).timestamp()
    blob = gzip.open(f"{B}entries_{g}.bin.gz").read()
    L = {}
    for t, mi, *_ in ROW.iter_unpack(blob):
        if mi not in L or t < L[mi]:
            L[mi] = t
    first = {}
    for t, mi, wi, hb, S, C, F, a, a60, a300, lag, fl in ROW.iter_unpack(blob):
        m = MK[mi]
        if m[4] >= at or S <= 0 or C <= 0:
            continue
        l0 = L[mi]
        if m[4] - l0 < 48 * 3600 or t - l0 > 24 * 3600:
            continue
        p = a300 / 1e4
        if not 0.05 <= p <= 0.95:
            continue
        side = "YES" if fl & 1 else "NO"
        k = (g, mi, side)
        if k in first and first[k]["t"] <= t:
            continue
        won = 1 if fl & 2 else 0   # bit 2 = the token of this direction won (c40 check)
        fam = re.sub(r"-?(by|on|in)?-?(january|february|march|april|may|june|july|august|september|october|november|december).*$", "", m[1])
        first[k] = dict(t=t, e=(g, m[1]), fam=fam, side=side, end=m[4], cat=m[2], rel=bool(RE.search(m[3])), p=p,
                        f=won - p - m[7] * p * (1 - p))
    R += first.values()
    del blob


def stat(rr, key="e"):
    ev = collections.defaultdict(lambda: [0.0, 0])
    for r in rr:
        ev[r[key]][0] += r["f"]; ev[r[key]][1] += 1
    v = list(ev.values()); n = sum(y[1] for y in v)
    if len(v) < 5:
        return {"n": n, "events": len(v), "pts": round(100 * sum(y[0] for y in v) / n, 2) if n else None}
    bs = []
    for _ in range(1000):
        s = [v[int(random.random() * len(v))] for _i in v]
        bs.append(sum(y[0] for y in s) / max(1, sum(y[1] for y in s)))
    bs.sort()
    return {"n": n, "events": len(v), "pts": round(100 * sum(y[0] for y in v) / n, 2),
            "ci": [round(100 * bs[25], 1), round(100 * bs[974], 1)], "avg_p": round(sum(r["p"] for r in rr) / n, 3)}


mid = sorted(r["end"] for r in R if r["rel"])[len([r for r in R if r["rel"]]) // 2]
out = {"rows": len(R), "relist markets": len({r["e"] + (r["end"],) for r in R if r["rel"]}), "split_at": str(dt.datetime.fromtimestamp(mid, dt.timezone.utc))}
for side in ("NO", "YES"):
    sel = [r for r in R if r["side"] == side and r["rel"]]
    out[f"RELIST {side}"] = stat(sel)
    out[f"  RELIST {side} by family"] = stat(sel, "fam")
    out[f"  RELIST {side} older"] = stat([r for r in sel if r["end"] < mid])
    out[f"  RELIST {side} newer"] = stat([r for r in sel if r["end"] >= mid])
    out[f"  RELIST {side} by group"] = {g: stat([r for r in sel if r["e"][0] == g]) for g in "ac"}
    out[f"OTHER {side}"] = stat([r for r in R if r["side"] == side and not r["rel"]])
out["families"] = collections.Counter(r["fam"] for r in R if r["rel"] and r["side"] == "NO").most_common(15)
n = out["RELIST NO"]
ok = (n.get("events", 0) >= 30 and n["pts"] >= 3 and n["ci"][0] > 0 and out["  RELIST NO older"].get("pts", -1) > 0
      and out["  RELIST NO newer"].get("pts", -1) > 0 and n["pts"] - out["OTHER NO"]["pts"] >= 2)
out["verdict"] = "PASS -> tracker arm" if ok else "DEAD"
print(json.dumps(out, indent=1))
json.dump(out, open(f"{B}relist_no_report.json", "w"), indent=1)
