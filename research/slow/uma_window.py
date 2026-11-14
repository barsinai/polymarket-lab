"""N20 (UMA proposal window) decisive test on our 15-min order-book snapshots (data/books, 10-31..).

For every closed market in data/research/books_outcomes.json, take the snapshots between its endDate and its closedTime
(resolution on-chain). An undisputed UMA proposal resolves ~2 h after it is posted, so the snapshots in the last 2 h before
closedTime are inside the liveness window (we cannot see the proposal itself -> using the FINAL winner as the 'proposed side'
gives an UPPER bound: in reality you buy the proposed side and some proposals are disputed).

For each market: best executable ask of the eventual winner in that window (snapshot ts = receive time of the book), the size at
that ask, and the return after the lab's taker fee (feeSchedule rate * p(1-p), else 0.07 p(1-p) when feesEnabled). Counted by
EVENT (event slug) - one bet per event at the cheapest snapshot is an even more optimistic bound, so we report the FIRST in-window
snapshot (what a rule 'buy when you see it' gets), plus how often the loser side still had a bid >= 2c (real doubt).
Output: data/research/uma_window.json. Runs locally (no network)."""
import glob
import gzip
import json
import os
from collections import defaultdict
from datetime import datetime

OUT = "data/research/uma_window.json"
OUTC = json.load(open("data/research/books_outcomes.json"))


def pt(s):
    if not s:
        return None
    s = s.replace(" ", "T").replace("+00", "+00:00") if s.endswith("+00") else s.replace(" ", "T")
    s = s.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(s).timestamp()
    except ValueError:
        return None


mk = {}
for i, m in OUTC.items():
    if not m.get("closed"):
        continue
    try:
        pr = [float(x) for x in json.loads(m.get("outcomePrices") or "[]")]
    except (ValueError, TypeError):
        continue
    if len(pr) != 2 or max(pr) < 0.99:
        continue  # skip 50/50 or unresolved
    ct, ed = pt(m.get("closedTime")), pt(m.get("endDate"))
    if not ct or not ed:
        continue
    fs = m.get("feeSchedule") or {}
    rate = (float(fs.get("rate") or 0.07)) if m.get("feesEnabled") else 0.0
    ev = (m.get("events") or {}).get("slug") or i
    tags = (m.get("events") or {}).get("tags") or []
    mk[i] = {"win": pr.index(max(pr)), "ct": ct, "ed": ed, "rate": rate, "ev": ev, "sports": bool(m.get("gameStartTime") or m.get("sportsMarketType") or "sports" in tags),
             "src": (m.get("resolutionSource") or "").split("/")[2] if "//" in (m.get("resolutionSource") or "") else ""}

def lv(levels):
    out = []
    for x in levels or []:
        if isinstance(x, dict):
            out.append((float(x["price"]), float(x["size"])))
        else:
            out.append((float(x[0]), float(x[1])))
    return out


first = {}   # id -> first in-window observation
best = {}    # id -> cheapest in-window observation
seen_after_end = set()
files = sorted(glob.glob("data/books/*/*.json.gz"))
for f in files:
    try:
        d = json.load(gzip.open(f))
    except Exception:  # noqa: BLE001
        continue
    ts = d["ts"]; books = d.get("books") or {}
    for m in d.get("markets", []):
        i = m.get("id"); x = mk.get(i)
        if not x or ts < x["ed"] or ts > x["ct"]:
            continue
        seen_after_end.add(i)
        h = (x["ct"] - ts) / 3600
        try:
            toks = json.loads(m.get("clobTokenIds") or "[]")
        except ValueError:
            continue
        if len(toks) != 2:
            continue
        bw, bl = books.get(toks[x["win"]]), books.get(toks[1 - x["win"]])
        if not bw:
            continue
        asks = sorted(lv(bw.get("asks")))
        lbids = sorted(lv(bl.get("bids")), reverse=True) if bl else []
        if not asks:
            continue
        a, sz = asks[0]
        depth98 = sum(s for p, s in asks if p <= 0.98)
        lb = lbids[0][0] if lbids else 0.0
        o = {"ts": ts, "h_to_close": round(h, 2), "ask": a, "size": sz, "depth_le98": round(depth98, 1), "loser_bid": lb,
             "ret": round((1 - a - x["rate"] * a * (1 - a)) / a, 4)}
        if h <= 2.0:
            if i not in first:
                first[i] = o
            if i not in best or a < best[i]["ask"]:
                best[i] = o


def summ(sel, ids):
    rows = [sel[i] for i in ids if i in sel]
    if not rows:
        return {"n": 0}
    evs = defaultdict(list)
    for i in ids:
        if i in sel:
            evs[mk[i]["ev"]].append(sel[i])
    cheap = [r for r in rows if r["ask"] <= 0.98]
    cheap_ev = {mk[i]["ev"] for i in ids if i in sel and sel[i]["ask"] <= 0.98}
    doubt = [r for r in rows if r["loser_bid"] >= 0.02]
    return {"markets": len(rows), "events": len(evs), "ask_le_098": len(cheap), "events_le_098": len(cheap_ev),
            "median_ask": sorted(r["ask"] for r in rows)[len(rows) // 2],
            "mean_ret_all": round(sum(r["ret"] for r in rows) / len(rows), 4),
            "cheap_mean_ret": round(sum(r["ret"] for r in cheap) / len(cheap), 4) if cheap else None,
            "cheap_dollars_le98": round(sum(r["depth_le98"] * r["ask"] for r in cheap), 1),
            "cheap_profit_upper": round(sum(r["depth_le98"] * r["ask"] * r["ret"] for r in cheap), 2),
            "loser_bid_ge_2c": len(doubt)}


allids = list(mk)
res = {"files": len(files), "closed_markets": len(mk), "seen_after_end": len(seen_after_end), "in_2h_window": len(first),
       "first_obs": {"all": summ(first, allids), "non_sports": summ(first, [i for i in allids if not mk[i]["sports"]]),
                     "sports": summ(first, [i for i in allids if mk[i]["sports"]])},
       "cheapest_obs": {"all": summ(best, allids), "non_sports": summ(best, [i for i in allids if not mk[i]["sports"]])},
       "examples_cheap": sorted(([i] + [first[i][k] for k in ("ask", "size", "h_to_close", "loser_bid", "ret")]
                                 for i in first if first[i]["ask"] <= 0.98), key=lambda r: r[1])[:25]}
# timing: hours from endDate to closedTime (how long the window is)
gaps = sorted((mk[i]["ct"] - mk[i]["ed"]) / 3600 for i in mk)
ns = [i for i in first if not mk[i]["sports"]]
bysrc = defaultdict(list)
for i in ns:
    bysrc[mk[i]["src"]].append(i)
res["non_sports_by_source"] = {k: summ(first, v) for k, v in sorted(bysrc.items(), key=lambda kv: -len(kv[1]))[:8]}
res["examples_cheap"] = sorted(([i, mk[i]["src"]] + [first[i][k] for k in ("ask", "size", "h_to_close", "loser_bid", "ret")]
                                for i in ns if first[i]["ask"] <= 0.98), key=lambda r: r[2])[:40]
res["hours_end_to_close_quartiles"] = [round(gaps[int(len(gaps) * q)], 2) for q in (0.25, 0.5, 0.75)] if gaps else None
os.makedirs("data/research", exist_ok=True)
json.dump(res, open(OUT, "w"), indent=1)
print(json.dumps({k: v for k, v in res.items() if k != "examples_cheap"}, indent=1))
for r in res["examples_cheap"][:12]:
    print(r)
