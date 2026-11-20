"""Cycle 45, N97 (adjacent to N95 RT ladders): fan-count threshold ladders EX-Rotten-Tomatoes, NO side on the upper rungs.
Rules fixed BEFORE looking (written in this docstring first):
Tape group a (movies / pop-culture / youtube / music / awards; mention excluded, any question naming 'tomato' excluded), finished
markets (end < tape time) whose question has a numeric threshold ('at least N', 'N or more', 'N+'). Ladder = event slug with >= 3
parsed rungs; rung position q = rank / (rungs - 1) by threshold value; upper = q >= 0.5. Entry = first taker entry per market and side,
follower fill a300 (next print >= 300 s later), price 0.05-0.95, fee = rate * p(1-p). Unit = event, bootstrap 1,000; halves by end.
DECISION: survives only if NO upper: >= +5 pts, CI low > 0, >= 30 events, both halves >= +2 -> paper arm. Kind splits (box office /
youtube views / netflix / sales / other) and 24-168 h are printed, NOT used to pass (lesson 22). Placebo: NO on lower rungs; YES upper.
Exposed to 22 (RT was found by looking), 24 (halves), 13 (the counts are public), 26, 5/6."""
import json, gzip, struct, collections, random, re, datetime as dt
ROW = struct.Struct("<IIIhfffHHHIB")
B = "data/research/"
random.seed(97)
meta = json.load(gzip.open(f"{B}entries_a_meta.json.gz")); MK = meta["markets"]
at = dt.datetime.strptime(meta["at"], "%Y-%m-%d %H:%M").replace(tzinfo=dt.timezone.utc).timestamp()
NUM = r"\$?(\d[\d,]*(?:\.\d+)?)"
PATS = [re.compile(r"at least\s+" + NUM, re.I), re.compile(NUM + r"\s*(?:million|m|k|b)?\s*(?:or more|\+)", re.I)]
CATS = {"movies", "pop-culture", "youtube", "music", "awards"}
def kind(q):
    q = q.lower()
    if "box office" in q: return "box office"
    if "netflix" in q: return "netflix"
    if "view" in q: return "views"
    if "sales" in q or "units" in q: return "sales"
    return "other"
thr = {}
for mi, m in enumerate(MK):
    if m[2] not in CATS or "tomato" in m[3].lower() or m[4] >= at: continue
    for P in PATS:
        t = P.search(m[3])
        if t:
            try: thr[mi] = float(t[1].replace(",", "")); break
            except ValueError: pass
lad = collections.defaultdict(list)
for mi, v in thr.items(): lad[MK[mi][1]].append(v)
q = {}
for mi, v in thr.items():
    vs = sorted(set(lad[MK[mi][1]]))
    if len(vs) >= 3: q[mi] = vs.index(v) / (len(vs) - 1)
blob = gzip.open(f"{B}entries_a.bin.gz").read()
first = {}
for t, mi, wi, hb, S, C, F, a, a60, a300, lag, fl in ROW.iter_unpack(blob):
    if mi not in q or S <= 0 or C <= 0: continue
    p = a300 / 1e4
    if not 0.05 <= p <= 0.95: continue
    side = "YES" if fl & 1 else "NO"; m = MK[mi]; k = (mi, side)
    if k in first and first[k]["t"] <= t: continue
    first[k] = dict(t=t, e=m[1], side=side, end=m[4], p=p, h=(m[4] - t) / 3600, q=q[mi], kind=kind(m[3]),
                    f=(1 if fl & 2 else 0) - p - m[7] * p * (1 - p))
del blob
R = list(first.values())
def stat(rr):
    ev = collections.defaultdict(lambda: [0.0, 0])
    for r in rr: ev[r["e"]][0] += r["f"]; ev[r["e"]][1] += 1
    v = list(ev.values()); n = sum(y[1] for y in v)
    if not n: return {"n": 0, "events": 0}
    o = {"n": n, "events": len(v), "pts": round(100 * sum(y[0] for y in v) / n, 2), "avg_p": round(sum(r["p"] for r in rr) / n, 3)}
    if len(v) >= 5:
        bs = sorted(sum(y[0] for y in s) / max(1, sum(y[1] for y in s)) for s in ([v[int(random.random() * len(v))] for _ in v] for _ in range(1000)))
        o["ci"] = [round(100 * bs[25], 1), round(100 * bs[974], 1)]
    return o
mid = sorted(r["end"] for r in R)[len(R) // 2] if R else 0
def half(rr): return {"older": stat([r for r in rr if r["end"] < mid]), "newer": stat([r for r in rr if r["end"] >= mid])}
NOU = [r for r in R if r["side"] == "NO" and r["q"] >= 0.5]
out = {"markets_parsed": len(thr), "ladder_markets": len(q), "ladders": len({MK[mi][1] for mi in q}), "rows": len(R),
       "split_at": str(dt.datetime.fromtimestamp(mid, dt.timezone.utc)) if R else None,
       "NO upper": stat(NOU), "NO upper halves": half(NOU),
       "NO lower (placebo)": stat([r for r in R if r["side"] == "NO" and r["q"] < 0.5]),
       "YES upper": stat([r for r in R if r["side"] == "YES" and r["q"] >= 0.5]),
       "NO all": stat([r for r in R if r["side"] == "NO"])}
for kd in ["box office", "views", "netflix", "sales", "other"]:
    rr = [r for r in NOU if r["kind"] == kd]
    out[f"NO upper {kd}"] = {**stat(rr), **{k: (v.get("pts"), v.get("events")) for k, v in half(rr).items()}}
rr = [r for r in NOU if 24 <= r["h"] <= 168]
out["NO upper 24-168h"] = {**stat(rr), **{k: (v.get("pts"), v.get("events")) for k, v in half(rr).items()}}
s, h = out["NO upper"], out["NO upper halves"]
ok = s.get("pts", -9) >= 5 and s.get("ci", [-1])[0] > 0 and s.get("events", 0) >= 30 and all((h[x].get("pts") or -9) >= 2 for x in h)
out["verdict"] = "PASS -> paper arm" if ok else "DEAD (fails the fixed rule)"
print(json.dumps(out, indent=1))
json.dump(out, open(f"{B}fan_ladder_report.json", "w"), indent=1)
