"""Sharp-wallet whitelist from the 12-week taker entries (groups a, b, c): wallets that won in BOTH halves.
Per wallet (pre-event entries, price 0.03-0.97): entries, events, cost, P&L after fees, mean points per entry - overall and per half."""
import json, gzip, struct, collections, datetime as dt, sys
ROW = struct.Struct("<IIIhfffHHHIB")
B = "data/research/"
W = collections.defaultdict(lambda: {"n": [0, 0], "pnl": [0.0, 0.0], "cost": [0.0, 0.0], "pts": [0.0, 0.0], "ev": [set(), set()], "cat": collections.Counter(), "last": 0})
for g in "abc":
    meta = json.load(gzip.open(f"{B}entries_{g}_meta.json.gz")); blob = gzip.open(f"{B}entries_{g}.bin.gz").read(); MK = meta["markets"]; WL = meta["wallets"]
    at = dt.datetime.strptime(meta["at"], "%Y-%m-%d %H:%M").replace(tzinfo=dt.timezone.utc).timestamp(); cut = at - 45 * 86400
    for t, mi, wi, hb, S, C, F, a, a60, a300, lag, fl in ROW.iter_unpack(blob):
        if hb < 1 or S <= 0 or C <= 0:
            continue
        p = C / S
        if not 0.03 <= p <= 0.97:
            continue
        m = MK[mi]; h = 1 if m[4] >= cut else 0; w = W[WL[wi]]; win = 1 if fl & 2 else 0
        w["n"][h] += 1; w["pnl"][h] += S * win - C - F; w["cost"][h] += C; w["pts"][h] += win - p - F / S; w["ev"][h].add(m[1]); w["cat"][m[2]] += 1; w["last"] = max(w["last"], t)
print("wallets:", len(W))


def ok(w, n_min, ev_min, cost_min, roi_min, pts_min):
    for h in (0, 1):
        if w["n"][h] < n_min or len(w["ev"][h]) < ev_min or w["cost"][h] < cost_min:
            return False
        if w["pnl"][h] / w["cost"][h] < roi_min or w["pts"][h] / w["n"][h] < pts_min:
            return False
    return True


for lab, args in (("strict: each half >= 15 entries, >= 5 events, >= $500, P&L >= +5%, >= +2 pts/entry", (15, 5, 500, 0.05, 0.02)),
                  ("medium: each half >= 10 entries, >= 4 events, >= $200, P&L > 0, > +1 pt/entry", (10, 4, 200, 0.0, 0.01)),
                  ("loose: each half >= 8 entries, >= 3 events, P&L > 0, pts > 0", (8, 3, 0, 0.0, 0.0))):
    L = {a: w for a, w in W.items() if ok(w, *args)}
    n = sum(sum(w["n"]) for w in L.values()); cost = sum(sum(w["cost"]) for w in L.values()); pnl = sum(sum(w["pnl"]) for w in L.values())
    cats = collections.Counter()
    for w in L.values():
        cats.update(w["cat"])
    print(f"{lab}: {len(L)} wallets, {n:,} entries in 12 weeks ({n / 84:.0f} a day), cost ${cost / 1e6:.2f}M, P&L {100 * pnl / cost:+.1f}% (in sample); entries by category {dict(cats.most_common(6))}")
    if lab.startswith("strict"):
        S = L
out = {a: {"n": sum(w["n"]), "events": len(w["ev"][0] | w["ev"][1]), "cost": round(sum(w["cost"])), "roi": round(sum(w["pnl"]) / sum(w["cost"]), 3), "pts": round(100 * sum(w["pts"]) / sum(w["n"]), 2),
           "top_cat": w["cat"].most_common(1)[0][0]} for a, w in S.items()}
json.dump({"built": "2026-11-14", "rule": "12 weeks of pre-event taker entries (culture, weather, politics/economy/tech); in EACH half: >= 15 entries, >= 5 events, >= $500, P&L >= +5% of cost, >= +2 points per entry",
           "wallets": out}, open("research/slow/follow_whitelist.json", "w"), indent=0)
import os; print("file", os.path.getsize("research/slow/follow_whitelist.json"), "bytes")
top = sorted(out.items(), key=lambda kv: -kv[1]["cost"])[:8]
for a, v in top:
    print("  ", a, v)
