"""Cycle 31, N70 (adjacent to N58 / N68): culture launch-hour NO ABOVE the tracker's band (NO 0.90-0.98, i.e. YES 'hope' at 2-10c).
Rules fixed BEFORE looking. Why it could work: N58 shows fans over-price YES on fresh culture markets; launch_paper.py skips NO asks
> 0.90 (41 of 207 candidates so far = the largest priced skip). If fans also keep a few cents of hope on near-dead YES, NO at 0.90-0.98
pays; if not, the tracker's cap is right. Exposed to 2 / 15 (near-certain NO: the 1-in-20 loss is the whole edge), 8 (cents), 5 (events).
Same unit as culture_decay.py: culture market living >= 24 h, listed >= 7 d after the tape start; taker NO entry < 1 h after listing;
follower buys NO at the next other-wallet print >= 300 s later (a300) in the band; fee m[7]*p*(1-p); first follower fill per market;
points per share clustered by event (bootstrap 1000). Control row: the tracker's own band 0.05-0.90 (should reproduce ~+7).
DECISION (0.90-0.98): PASS only if >= 40 events, pts > +1, event CI low > 0, both halves (by listing) > 0, ex-mention > 0."""
import json, gzip, struct, collections, random, datetime as dt
ROW = struct.Struct("<IIIhfffHHHIB")
B = "data/research/"
random.seed(70)
CULT = {"mention", "movies", "music", "youtube", "awards", "pop-culture"}
BANDS = {"NO 0.90-0.98 (DECISION)": (0.90, 0.98), "NO 0.05-0.90 (tracker band, control)": (0.05, 0.90),
         "NO 0.90-0.95": (0.90, 0.95), "NO 0.95-0.98": (0.95, 0.98)}
R = []
meta = json.load(gzip.open(f"{B}entries_a_meta.json.gz")); MK = meta["markets"]
at = dt.datetime.strptime(meta["at"], "%Y-%m-%d %H:%M").replace(tzinfo=dt.timezone.utc).timestamp()
blob = gzip.open(f"{B}entries_a.bin.gz").read()
L = {}
for t, mi, *_ in ROW.iter_unpack(blob):
    if mi not in L or t < L[mi]:
        L[mi] = t
t0 = min(L.values())
for t, mi, wi, hb, S, C, F, a, a60, a300, lag, fl in ROW.iter_unpack(blob):
    m = MK[mi]
    if m[2] not in CULT or fl & 1 or m[4] >= at or S <= 0 or hb < 1:
        continue
    l0 = L[mi]
    if m[4] - l0 < 24 * 3600 or l0 < t0 + 7 * 86400 or t - l0 >= 3600:
        continue
    p = a300 / 1e4
    if not 0.05 <= p <= 0.98:
        continue
    R.append(dict(e=m[1], m=mi, cat=m[2], t=t, l0=l0, p=p, win=1 if fl & 2 else 0,
                  fol=(1 if fl & 2 else 0) - p - m[7] * p * (1 - p)))
del blob
_lm = sorted({r["m"]: r["l0"] for r in R}.values()); mid = _lm[len(_lm) // 2]


def stat(rows):
    ev = collections.defaultdict(lambda: [0.0, 0])
    for r in rows:
        ev[r["e"]][0] += r["fol"]; ev[r["e"]][1] += 1
    v = list(ev.values()); n = sum(y[1] for y in v)
    if len(v) < 5:
        return {"n": n, "events": len(v)}
    bs = []
    for _ in range(1000):
        s = [v[int(random.random() * len(v))] for _i in v]
        bs.append(sum(y[0] for y in s) / max(1, sum(y[1] for y in s)))
    bs.sort()
    return {"n": n, "events": len(v), "pts": round(100 * sum(y[0] for y in v) / n, 2),
            "ci": [round(100 * bs[25], 1), round(100 * bs[974], 1)], "avg_p": round(sum(r["p"] for r in rows) / n, 3),
            "win": round(sum(r["win"] for r in rows) / n, 3), "losses": sum(1 - r["win"] for r in rows)}


out = {"markets": len({r["m"] for r in R}), "split_at": str(dt.datetime.fromtimestamp(mid, dt.timezone.utc))}
dec = None
for name, (lo, hi) in BANDS.items():
    first = {}
    for r in sorted(R, key=lambda r: r["t"]):
        if lo <= r["p"] < hi:
            first.setdefault(r["m"], r)
    F = list(first.values())
    out[name] = s = stat(F)
    if dec is None:
        dec = (s, {h: stat([r for r in F if (r["l0"] < mid) == (h == "older")]) for h in ("older", "newer")},
               stat([r for r in F if r["cat"] != "mention"]))
        out["  older half"], out["  newer half"] = dec[1]["older"], dec[1]["newer"]
        out["  ex-mention"] = dec[2]
s0, hv, xm = dec
ok = (s0.get("events", 0) >= 40 and s0["pts"] > 1 and s0["ci"][0] > 0 and all(v.get("pts", -1) > 0 for v in hv.values())
      and xm.get("pts", -1) > 0)
out["verdict"] = "PASS" if ok else "FAIL"
print(json.dumps(out, indent=1))
json.dump(out, open(f"{B}culture_highno_report.json", "w"), indent=1)
