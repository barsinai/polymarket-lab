"""N23 (adjacent, 11-14 c10): last-day favourites 0.95-0.99 on the 5-month non-sports history, split by a geopolitics / war
keyword filter fixed BEFORE looking at which markets lost (list below). Entry: first hourly price in the last 24 h before the end with
the favoured side in [0.95, 0.99]; cost = price + 0.5c + fee 0.07p(1-p) (executable-ish, LESSONS 3); one entry per market; independent
events = event slug stem (slug without the trailing option) per day. Read-only on data/research/hist_*.json."""
import json, re, collections, datetime as dt
C = {x["id"]: x for x in json.load(open("data/research/hist_cands.json")) if x["kind"] == "nonsport"}
P = json.load(open("data/research/hist_prices.json"))
GEO = re.compile(r"iran|israel|gaza|hamas|hezbollah|houthi|yemen|russia|ukrain|putin|zelensk|nato|china|taiwan|venezuela|maduro|"
                 r"north-korea|kim-jong|strike|attack|airspace|military|missile|troops|invade|invasion|war|ceasefire|truce|nuclear|"
                 r"drone|bomb|shipping|hormuz|red-sea|sanction|uae|saudi|syria|lebanon|iraq|pakistan|india|coup", re.I)
CRYPTO = re.compile(r"bitcoin|btc|ethereum|eth-|solana|xrp|crypto|updown|up-or-down", re.I)
rows = []
for i, x in C.items():
    h = P.get(i) or []
    ref = x["ref"]
    if CRYPTO.search(x["slug"]):
        continue
    for t, p in h:
        if not (ref - 24 * 3600 <= t <= ref - 3600):
            continue
        side = 0 if 0.95 <= p <= 0.99 else 1 if 0.95 <= 1 - p <= 0.99 else None
        if side is None:
            continue
        q = p if side == 0 else 1 - p
        c = q + 0.005 + 0.07 * q * (1 - q)
        won = (x["w"] == 0) == (side == 0)   # w = index of the winning outcome (checked: w=1 -> token0 last price ~0 in 1,812 of 1,853)
        rows.append(dict(id=i, slug=x["slug"], geo=bool(GEO.search(x["slug"])), q=q, ret=(1 if won else 0) / c - 1, won=won,
                         month=dt.datetime.fromtimestamp(ref, dt.timezone.utc).strftime("%Y-%m"), day=int(ref // 86400),
                         ev=re.sub(r"-[^-]+$", "", x["slug"]), vol=x.get("vol", 0)))
        break
out = {}
for name, f in (("all", lambda r: True), ("geo", lambda r: r["geo"]), ("ex_geo", lambda r: not r["geo"])):
    v = [r for r in rows if f(r)]
    ev = {(r["ev"], r["day"]) for r in v}
    bym = collections.defaultdict(list)
    for r in v:
        bym[r["month"]].append(r["ret"])
    out[name] = dict(n=len(v), events=len(ev), losses=sum(not r["won"] for r in v), ret_per_usd=round(sum(r["ret"] for r in v) / max(1, len(v)), 4),
                     by_month={m: [len(a), round(sum(a) / len(a), 4)] for m, a in sorted(bym.items())})
out["losses"] = [(r["slug"], round(r["q"], 3), r["geo"]) for r in rows if not r["won"]]
print(json.dumps(out, indent=1))
json.dump(out, open("data/research/converge_geo_split.json", "w"), indent=1)
