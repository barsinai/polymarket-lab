"""Cycle 33, N75 (outside the box): YouTube view-count bucket ladders ('# of views of (next) MrBeast (gaming) video on day N / week N',
GTA VI trailer views). Never tested as their own family. Why the crowd could be wrong: view growth curves are very regular (day-1
views pin day-4 / day-7 within a few %) while the ladder is priced by fans who spread mass over neighbouring buckets; the count is
public live on the video page. Exposed to 26 (public live tally -> priced within the hour?), 9 (we bring a growth-curve model only),
6/5 (one video = several day-N events = one bet), 13, 15.
Rules fixed BEFORE looking: group a markets whose slug starts 'of-views-of' (or contains '-of-views-of-'), finished on the tape; taker
entries 1-48 h before the scheduled end; follower = next print the same way >= 300 s later (a300), fee = rate * p(1-p); one fill per
market+direction (first); arms by the follower's token: FAV = token priced 0.50-0.95, FADE = token priced 0.50-0.95 on the NO side
(i.e. selling a 0.05-0.50 YES bucket). Unit = VIDEO (slug with the day/week number removed and its date kept), bootstrap 1,000;
halves by end time. PASS: arm >= 20 videos, pts > +3, video CI low > 0, both halves > 0. DEAD by count if < 20 videos."""
import json, gzip, struct, collections, random, re, datetime as dt
ROW = struct.Struct("<IIIhfffHHHIB")
B = "data/research/"
random.seed(75)
meta = json.load(gzip.open(f"{B}entries_a_meta.json.gz")); MK = meta["markets"]
at = dt.datetime.strptime(meta["at"], "%Y-%m-%d %H:%M").replace(tzinfo=dt.timezone.utc).timestamp()
blob = gzip.open(f"{B}entries_a.bin.gz").read()


def video(slug):
    s = re.sub(r"-(on-)?(day|week)-\d+", "", slug)
    return re.sub(r"-(higher|lower|smaller|even-higher)-[a-z-]*", "", s)


first = {}
for t, mi, wi, hb, S, C, F, a, a60, a300, lag, fl in sorted(ROW.iter_unpack(blob)):
    m = MK[mi]
    if not ("of-views-of" in m[1]) or m[4] >= at or S <= 0:
        continue
    hbe = (m[4] - t) / 3600
    if not 1 <= hbe < 48:
        continue
    p = a300 / 1e4
    if not 0.50 <= p <= 0.95:
        continue
    yes = bool(fl & 1); k = (mi, yes)
    if k in first:
        continue
    win = 1 if fl & 2 else 0
    first[k] = dict(v=video(m[1]), end=m[4], arm="FAV" if yes else "FADE", p=p, f=win - p - m[7] * p * (1 - p))
del blob
R = list(first.values())


def stat(rr):
    ev = collections.defaultdict(lambda: [0.0, 0])
    for r in rr:
        ev[r["v"]][0] += r["f"]; ev[r["v"]][1] += 1
    v = list(ev.values()); n = sum(y[1] for y in v)
    if len(v) < 5:
        return {"n": n, "videos": len(v), "pts": round(100 * sum(y[0] for y in v) / n, 2) if n else None}
    bs = []
    for _ in range(1000):
        s = [v[int(random.random() * len(v))] for _i in v]
        bs.append(sum(y[0] for y in s) / max(1, sum(y[1] for y in s)))
    bs.sort()
    return {"n": n, "videos": len(v), "pts": round(100 * sum(y[0] for y in v) / n, 2), "ci": [round(100 * bs[25], 1), round(100 * bs[974], 1)],
            "avg_p": round(sum(r["p"] for r in rr) / n, 3)}


out = {"rows": len(R), "videos": len({r["v"] for r in R})}
for arm in ("FAV", "FADE"):
    A = [r for r in R if r["arm"] == arm]
    if not A:
        continue
    mid = sorted(r["end"] for r in A)[len(A) // 2]
    s0 = stat(A); o = stat([r for r in A if r["end"] < mid]); nw = stat([r for r in A if r["end"] >= mid])
    out[arm] = s0; out[arm + " older"] = o; out[arm + " newer"] = nw
    ok = s0.get("videos", 0) >= 20 and s0["pts"] > 3 and s0.get("ci", [-1])[0] > 0 and (o.get("pts") or -1) > 0 and (nw.get("pts") or -1) > 0
    out[arm + " verdict"] = "PASS" if ok else ("DEAD by count" if s0.get("videos", 0) < 20 else "FAIL")
print(json.dumps(out, indent=1))
json.dump(out, open(f"{B}views_buckets_report.json", "w"), indent=1)
