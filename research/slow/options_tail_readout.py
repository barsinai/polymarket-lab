"""N42 read-out (cycle 17, adjacent): options paper split by price - tails (paid < 0.20) vs the rest - in price points per share
(LESSONS 19), clustered by coin + resolution date (LESSONS 6), and the direction of each tail (does it pay if crypto FALLS?).
In-sample (all settled before 11-15 09:00 UTC) vs forward (opened >= 11-15 09:00). No bot change."""
import json, collections, datetime as dt
FWD = "2026-11-15 09:00"
P = [json.loads(l) for l in open("data/research/options_positions.jsonl")]


def down_bet(p):
    q = p["q"].lower(); yes = p["side"] == "YES"
    if "dip" in q or "less than" in q or "below" in q:
        return yes
    if "above" in q or "reach" in q:
        return not yes
    return None


out = {}
for per in ("in_sample", "forward"):
    for grp in ("tail<0.20", "rest"):
        v = [p for p in P if p.get("result") and ((p["opened"] >= FWD) == (per == "forward")) and ((p["price"] < 0.20) == (grp == "tail<0.20"))]
        ev = collections.defaultdict(list)
        for p in v:
            ev[(p["coin"], p["T"][:10])].append((1 if p["result"] == "won" else 0) - p["price"])
        n = len(v)
        out[f"{per} {grp}"] = {"n": n, "won": sum(p["result"] == "won" for p in v), "events": len(ev),
                              "pts_per_share": round(100 * sum(sum(x) for x in ev.values()) / n, 1) if n else None,
                              "events_pos": sum(1 for x in ev.values() if sum(x) > 0), "pnl": round(sum(p["pnl"] for p in v), 1),
                              "down_bets": sum(1 for p in v if down_bet(p))}
openv = [p for p in P if not p.get("result")]
out["open"] = {"n": len(openv), "tails": sum(p["price"] < 0.20 for p in openv), "tails_down_bets": sum(1 for p in openv if p["price"] < 0.20 and down_bet(p)),
               "rest_down_bets": sum(1 for p in openv if p["price"] >= 0.20 and down_bet(p)), "rest": sum(p["price"] >= 0.20 for p in openv)}
# N114 (c53, rule fixed then): tails opened >= 11-21 12:00, ONE position per coin+date (the largest edge), kill if <= 0 pts after 15 coin-dates
N114 = "2026-11-21 12:00"
best = {}
for p in P:
    if p["opened"] >= N114 and p["price"] < 0.20:
        k = (p["coin"], p["T"][:10])
        if k not in best or p["edge"] > best[k]["edge"]:
            best[k] = p
done = [p for p in best.values() if p.get("result")]
out["N114 tails one per coin-date"] = {"coin_dates": len(best), "settled": len(done), "won": sum(p["result"] == "won" for p in done),
    "pts_per_share": round(100 * sum((1 if p["result"] == "won" else 0) - p["price"] for p in done) / len(done), 1) if done else None,
    "down_bets": sum(1 for p in best.values() if down_bet(p)), "kill_rule": "<= 0 pts after 15 settled coin-dates"}
print(json.dumps(out, indent=1))
