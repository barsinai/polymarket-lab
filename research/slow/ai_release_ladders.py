"""Cycle 35, N79 (outside the box): AI model release-date ladders ('next Gemini Pro / Claude / GPT / Grok model released on/by
<date>', ~30 events, ~600 markets in 12 weeks). Never touched before.
Why the crowd could be wrong: release markets are bought by AI fans on hype (leaks, 'soon' tweets, arena mystery models), so the
near dates of a ladder should carry YES too rich; labs slip. Or the opposite: insiders/leak-readers buy YES days before and NO is
the sucker side (lesson 17: informed takers win in tech).
Rules fixed BEFORE looking. Group c tape, category ai/tech, event slug contains 'releas' (model release ladders; launches/announce
excluded). All markets finished before the tape cut. Entry = taker entry by direction, >= 24 h before the market end; follower =
next print the same way by someone else >= 300 s later at 0.05-0.90, fee = rate * p(1-p); first follower fill per market per side.
Units: event slug AND model line (slug with digits, 'pt', 'on/by/released' and ids stripped -> e.g. 'next-google-gemini-pro-model').
Placebo/mirror = the YES side.
DECISION (NO side): DEAD if < 30 model lines, or pts <= +1, or event CI low <= 0, or halves (by entry time) disagree in sign.
Exposed to: 6 (one release resolves a whole ladder and the sibling events of the same model line), 11 (path questions: all finished
only), 5, 13 (release rumours are public), 1 (leak readers are faster than us)."""
import json, gzip, struct, collections, random, re, datetime as dt
ROW = struct.Struct("<IIIhfffHHHIB")
B = "data/research/"
random.seed(79)
meta = json.load(gzip.open(f"{B}entries_c_meta.json.gz")); MK = meta["markets"]
at = dt.datetime.strptime(meta["at"], "%Y-%m-%d %H:%M").replace(tzinfo=dt.timezone.utc).timestamp()
blob = gzip.open(f"{B}entries_c.bin.gz").read()


def line(slug):
    s = slug.lower()
    s = re.sub(r"-\d{8,}$", "", s); s = re.sub(r"\d+pt\d+", "", s); s = re.sub(r"\d+", "", s)
    s = re.sub(r"(released?|onptptpt|byptptpt|-on-|-by-|when-will-the|be-|which-week-will)", "-", s)
    s = s.replace("next-", "").replace("google-", "").replace("openais-", "openai-")
    return re.sub(r"-+", "-", s).strip("-")


first = {}
for t, mi, wi, hb, S, C, F, a, a60, a300, lag, fl in ROW.iter_unpack(blob):
    m = MK[mi]
    if m[2] != "ai/tech" or "releas" not in m[1] or m[4] >= at or S <= 0 or hb < 24:
        continue
    p = a300 / 1e4
    if not 0.05 <= p <= 0.90:
        continue
    side = "YES" if fl & 1 else "NO"
    k = (mi, side)
    if k in first and first[k]["t"] <= t:
        continue
    first[k] = dict(t=t, e=m[1], ln=line(m[1]), side=side, p=p, f=(1 if fl & 2 else 0) - p - m[7] * p * (1 - p))
del blob
R = list(first.values())


def stat(rr, unit="e"):
    ev = collections.defaultdict(lambda: [0.0, 0])
    for r in rr:
        ev[r[unit]][0] += r["f"]; ev[r[unit]][1] += 1
    v = list(ev.values()); n = sum(y[1] for y in v)
    if len(v) < 5:
        return {"n": n, unit: len(v), "pts": round(100 * sum(y[0] for y in v) / n, 2) if n else None}
    bs = []
    for _ in range(1000):
        s = [v[int(random.random() * len(v))] for _i in v]
        bs.append(sum(y[0] for y in s) / max(1, sum(y[1] for y in s)))
    bs.sort()
    return {"n": n, unit: len(v), "pts": round(100 * sum(y[0] for y in v) / n, 2), "ci": [round(100 * bs[25], 1), round(100 * bs[974], 1)],
            "avg_p": round(sum(r["p"] for r in rr) / n, 3)}


out = {"markets": len({k[0] for k in first}), "events": len({r["e"] for r in R}), "model_lines": sorted({r["ln"] for r in R})}
for side in ("NO", "YES"):
    S = [r for r in R if r["side"] == side]
    if not S:
        continue
    mid = sorted(r["t"] for r in S)[len(S) // 2]
    out[f"{side} by event"] = stat(S)
    out[f"{side} by model line"] = stat(S, "ln")
    out[f"{side} older half"] = stat([r for r in S if r["t"] < mid])
    out[f"{side} newer half"] = stat([r for r in S if r["t"] >= mid])
    for lo, hi in ((0.05, 0.30), (0.30, 0.60), (0.60, 0.90)):
        out[f"{side} price {lo}-{hi}"] = stat([r for r in S if lo <= r["p"] < hi])
no = out.get("NO by event", {}); nl = out.get("NO by model line", {})
h1, h2 = out.get("NO older half", {}).get("pts"), out.get("NO newer half", {}).get("pts")
dead = (len(out["model_lines"]) < 30 or (no.get("pts") or 0) <= 1 or not no.get("ci") or no["ci"][0] <= 0
        or h1 is None or h2 is None or (h1 > 0) != (h2 > 0))
out["verdict"] = "DEAD" if dead else "PASS"
out["dead_by_count"] = len(out["model_lines"]) < 30
print(json.dumps(out, indent=1))
json.dump(out, open(f"{B}ai_release_report.json", "w"), indent=1)
