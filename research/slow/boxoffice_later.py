"""Cycle 43, N3 (adjacent to N2b, never tested since 11-12): later-weekend box-office brackets ('X 2nd..8th Weekend Box Office').
Rules fixed BEFORE looking. Rows: tape group a, finished markets, question matches 'Nth Weekend Box Office' (not 'Opening').
Event = event slug (film + weekend). Follower fill = next print the same way >= 300 s later (a300), fee = rate * p(1-p).
(A) Saturday favourite (the N2b rule moved to later weekends): first entry per market+side with t on Sat 14:00 - Sun 02:00 UTC of
    the weekend before end, a300 in 0.80-0.97.
(B) Drop-ratio chain: for a ladder whose previous weekend ladder (same film, weekend N-1) is on the tape and resolved, predicted
    gross = midpoint of the previous winning bracket x 0.45 (2nd weekend; prev = opening, needs the opening ladder on the tape) or
    x 0.60 (3rd+). Buy YES on the bracket that contains the prediction, first entry within 24 h of the ladder's first print.
DECISION: PASS only with >= 30 events, >= +5 pts, CI low > 0 and both halves > 0 (A or B). Otherwise DEAD (by count if < 30 events).
Exposed to 5/6 (one weekend's films share a market-wide attendance shock), 13 (drop ratios are public), 3, 24."""
import json, gzip, struct, collections, random, re, datetime as dt
ROW = struct.Struct("<IIIhfffHHHIB")
B = "data/research/"
random.seed(3)
meta = json.load(gzip.open(f"{B}entries_a_meta.json.gz")); MK = meta["markets"]
at = dt.datetime.strptime(meta["at"], "%Y-%m-%d %H:%M").replace(tzinfo=dt.timezone.utc).timestamp()
blob = gzip.open(f"{B}entries_a.bin.gz").read()
RW = re.compile(r"(\d+)(?:st|nd|rd|th) Weekend Box Office", re.I)
RO = re.compile(r"Opening Weekend Box Office", re.I)


def bracket(q):
    q = q.replace(",", "")
    m = re.search(r"between \$?([\d.]+)m and \$?([\d.]+)m", q, re.I)
    if m: return float(m[1]), float(m[2])
    m = re.search(r"(less than|under|below) \$?([\d.]+)m", q, re.I)
    if m: return 0.0, float(m[2])
    m = re.search(r"(more than|greater than|over|above|at least|or more) \$?([\d.]+)m", q, re.I) or re.search(r"\$?([\d.]+)m\+", q)
    if m: v = float(m.groups()[-1]); return v, v * 1.4
    return None


def film_week(m):
    q = m[3]; w = RW.search(q)
    if w: n = int(w[1])
    elif RO.search(q): n = 1
    else: return None
    f = re.split(r" (?:\d+(?:st|nd|rd|th)|Opening) Weekend", q)[0]
    f = re.sub(r"^Will ", "", f).strip(' "\'').lower()
    return f, n


L = {}; yeswon = {}
for t, mi, wi, hb, S, C, F, a, a60, a300, lag, fl in ROW.iter_unpack(blob):
    L[mi] = min(L.get(mi, t), t)
    if fl & 1: yeswon[mi] = 1 if fl & 2 else 0
    elif mi not in yeswon: yeswon[mi] = 0 if fl & 2 else 1
info = {}
for mi, m in enumerate(MK):
    if mi in L and m[4] < at:
        fw = film_week(m); br = bracket(m[3])
        if fw and br: info[mi] = dict(f=fw[0], n=fw[1], br=br, slug=m[1], end=m[4])
# previous weekend's winning bracket per film/week (by end date, first ladder of that week)
win = {}
for mi, d in info.items():
    if yeswon.get(mi) == 1:
        win.setdefault((d["f"], d["n"]), (d["br"]))
A = {}; Bm = {}
for t, mi, wi, hb, S, C, F, a, a60, a300, lag, fl in ROW.iter_unpack(blob):
    d = info.get(mi)
    if not d or d["n"] < 2: continue
    p = a300 / 1e4
    if not 0.02 <= p <= 0.98: continue
    side = "YES" if fl & 1 else "NO"; won = 1 if fl & 2 else 0
    r = dict(t=t, e=d["slug"], end=d["end"], p=p, f=won - p - MK[mi][7] * p * (1 - p))
    tt = dt.datetime.fromtimestamp(t, dt.timezone.utc); ee = dt.datetime.fromtimestamp(d["end"], dt.timezone.utc)
    sat = (ee - tt).days < 4 and ((tt.weekday() == 5 and tt.hour >= 14) or (tt.weekday() == 6 and tt.hour < 2))
    if sat and 0.80 <= p <= 0.97:
        k = (mi, side)
        if k not in A or A[k]["t"] > t: A[k] = r
    prev = win.get((d["f"], d["n"] - 1))
    if side == "YES" and prev and t - L[mi] <= 86400:
        mid = (prev[0] + prev[1]) / 2 * (0.45 if d["n"] == 2 else 0.60)
        if d["br"][0] <= mid < d["br"][1] and (mi not in Bm or Bm[mi]["t"] > t): Bm[mi] = r
del blob


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


ends = sorted(d["end"] for d in info.values() if d["n"] >= 2); mid = ends[len(ends) // 2] if ends else 0
out = {"later-weekend markets": sum(1 for d in info.values() if d["n"] >= 2),
       "later-weekend events": len({d["slug"] for d in info.values() if d["n"] >= 2}),
       "film-weekends with a resolved previous ladder": len({(d["f"], d["n"]) for d in info.values() if d["n"] >= 2 and (d["f"], d["n"] - 1) in win})}
for name, rows in (("A saturday favourite", list(A.values())), ("B drop-chain YES", list(Bm.values()))):
    out[name] = stat(rows)
    out[name + " older"] = stat([r for r in rows if r["end"] < mid]); out[name + " newer"] = stat([r for r in rows if r["end"] >= mid])
ok = any(out[k].get("events", 0) >= 30 and out[k].get("pts", -99) >= 5 and out[k].get("ci", [-1])[0] > 0
         and out[k + " older"].get("pts", -1) > 0 and out[k + " newer"].get("pts", -1) > 0 for k in ("A saturday favourite", "B drop-chain YES"))
out["verdict"] = "PASS -> paper arm" if ok else ("DEAD by count" if out["later-weekend events"] < 30 else "DEAD")
print(json.dumps(out, indent=1))
json.dump(out, open(f"{B}boxoffice_later_report.json", "w"), indent=1)
