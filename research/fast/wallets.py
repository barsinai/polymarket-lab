"""Who wins in the Up/Down markets, and how? (Read-only study.)

For every window we have a result for: the official priceToBeat / finalPrice (Gamma eventMetadata) and the
full public trade tape (Data API, both sides of each match, with wallet addresses). Then per wallet: P&L to
resolution, volume, number of windows, timing (seconds before the end) and price of their buys, and whether
they buy the eventual winner. Output: data/fast/tape.jsonl.gz (all fills), data/fast/results_meta.json,
data/fast/wallets_summary.json, and a printed league table.
"""
import gzip, json, os, time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
import requests

D = "data/fast"
S = requests.Session(); S.headers["User-Agent"] = "polymarket-lab-research/0.1"
GAMMA, DATA = "https://gamma-api.polymarket.com", "https://data-api.polymarket.com"
res = json.load(open(f"{D}/results.json"))
try:
    meta = json.load(open(f"{D}/results_meta.json"))
except OSError:
    meta = {}


def get(url, params, tries=4):
    for i in range(tries):
        try:
            r = S.get(url, params=params, timeout=20)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 429:
                time.sleep(2 + 2 * i); continue
            return None
        except Exception:  # noqa: BLE001
            time.sleep(1 + i)
    return None


def fetch_meta(slug):
    ev = get(f"{GAMMA}/events", {"slug": slug})
    if not ev:
        return slug, None
    e = ev[0]; m = e["markets"][0]; md = e.get("eventMetadata") or {}
    pr = [float(x) for x in json.loads(m["outcomePrices"])]
    return slug, {"cid": m["conditionId"], "up": bool(pr[0] > pr[1]) if max(pr) >= 0.99 else None,
                  "ptb": md.get("priceToBeat"), "final": md.get("finalPrice"), "start": int(slug.rsplit("-", 1)[1]),
                  "window": 900 if "-15m-" in slug else 300, "volume": float(m.get("volumeNum") or 0)}


def fetch_tape(slug, cid, probe=False):
    """Data API v2: GET /v2/trades?condition_id=..&limit=500 (+cursor), both sides when taker_only=false works"""
    out, cursor = [], None
    for _ in range(40):
        params = {"condition_id": cid, "limit": 500, "taker_only": "false"}
        if cursor:
            params["cursor"] = cursor
        d = get(f"{DATA}/v2/trades", params)
        rows = (d or {}).get("data") if isinstance(d, dict) else None
        if probe:
            print("probe", slug, "status", type(d).__name__, "rows", len(rows or []), "sample", json.dumps((rows or [None])[0])[:400])
            probe = False
        if not rows:
            break
        out += rows
        pg = d.get("pagination") or {}
        if not pg.get("has_more") or not pg.get("next_cursor"):
            break
        cursor = pg["next_cursor"]
    rows = []
    for t in out:
        try:
            oi = t.get("outcome_index"); o = t.get("outcome") or ("Up" if oi == 0 else "Down" if oi == 1 else None)
            rows.append({"slug": slug, "w": t.get("proxy_wallet") or t.get("proxyWallet"), "side": t.get("side"), "o": o,
                         "p": float(t.get("price")), "s": float(t.get("size")), "ts": int(float(t.get("timestamp"))),
                         "tx": (t.get("transaction_hash") or t.get("transactionHash") or "")[:12], "role": t.get("trader_side") or t.get("role")})
        except (TypeError, ValueError):
            pass
    return rows


slugs = set(res)
for f in ("windows.jsonl", "trades.jsonl", "model.jsonl", "obs.jsonl"):
    try:
        for line in open(f"{D}/{f}"):
            try:
                slugs.add(json.loads(line)["slug"])
            except (ValueError, KeyError):
                pass
    except OSError:
        pass
slugs = sorted(slugs)
todo = [s for s in slugs if s not in meta or meta[s].get("up") is None]
with ThreadPoolExecutor(6) as ex:
    for slug, md in ex.map(fetch_meta, todo):
        if md:
            meta[slug] = md
json.dump(meta, open(f"{D}/results_meta.json", "w"))
print("windows", len(slugs), "meta", len(meta))

have = set()
try:
    with gzip.open(f"{D}/tape.jsonl.gz", "rt") as fh:
        for line in fh:
            have.add(json.loads(line)["slug"])
except OSError:
    pass
todo = [s for s in slugs if s in meta and meta[s]["cid"] and meta[s].get("up") is not None and s not in have]
print("tape to fetch", len(todo))
if todo:
    fetch_tape(todo[0], meta[todo[0]]["cid"], probe=True)
with gzip.open(f"{D}/tape.jsonl.gz", "at") as fh, ThreadPoolExecutor(4) as ex:
    n = 0
    for rows in ex.map(lambda s: fetch_tape(s, meta[s]["cid"]), todo):
        for r in rows:
            fh.write(json.dumps(r) + "\n")
        n += len(rows)
print("fills fetched", n)

# ---- analysis
tape = []
with gzip.open(f"{D}/tape.jsonl.gz", "rt") as fh:
    for line in fh:
        tape.append(json.loads(line))
tape = [t for t in tape if t["slug"] in meta and meta[t["slug"]].get("up") is not None and t["w"]]
print("fills with result", len(tape), "wallets", len({t["w"] for t in tape}))

W = defaultdict(lambda: {"n": 0, "vol": 0.0, "pnl": 0.0, "wins": 0, "buys": 0, "late": 0, "rem": [], "px": [], "win_side": 0, "windows": set(), "sells": 0})
for t in tape:
    md = meta[t["slug"]]; end = md["start"] + md["window"]
    up_won = md["up"]; is_up = str(t["o"]).lower() == "up"
    won = 1.0 if (is_up == up_won) else 0.0
    buy = str(t["side"]).upper() == "BUY"
    pnl = t["s"] * ((won - t["p"]) if buy else (t["p"] - won))
    w = W[t["w"]]
    w["n"] += 1; w["vol"] += t["s"] * t["p"]; w["pnl"] += pnl; w["windows"].add(t["slug"])
    if buy:
        w["buys"] += 1; w["rem"].append(end - t["ts"]); w["px"].append(t["p"]); w["win_side"] += won
        if end - t["ts"] <= 60:
            w["late"] += 1
    else:
        w["sells"] += 1
rows = []
for a, w in W.items():
    r = sorted(w["rem"]); p = sorted(w["px"])
    rows.append({"wallet": a, "fills": w["n"], "windows": len(w["windows"]), "volume": round(w["vol"], 1), "pnl": round(w["pnl"], 1),
                 "pnl_per_$": round(w["pnl"] / w["vol"], 3) if w["vol"] else 0, "buys": w["buys"], "sells": w["sells"],
                 "buy_win_rate": round(w["win_side"] / w["buys"], 3) if w["buys"] else None,
                 "median_rem_s": r[len(r) // 2] if r else None, "share_last60": round(w["late"] / w["buys"], 2) if w["buys"] else None,
                 "median_price": p[len(p) // 2] if p else None})
rows.sort(key=lambda r: -r["pnl"])
tot_pnl = sum(r["pnl"] for r in rows); tot_vol = sum(r["volume"] for r in rows)
print(f"all wallets: fills {sum(r['fills'] for r in rows)} volume ${tot_vol:,.0f} net pnl ${tot_pnl:,.0f} (should be ~0 before fees)")
print("\nTOP 25 by P&L")
for r in rows[:25]:
    print(json.dumps(r))
print("\nBOTTOM 10 by P&L")
for r in rows[-10:]:
    print(json.dumps(r))
big = [r for r in rows if r["windows"] >= 30]
big.sort(key=lambda r: -r["pnl_per_$"])
print(f"\nwallets active in >= 30 windows: {len(big)}; top 15 by P&L per $")
for r in big[:15]:
    print(json.dumps(r))
# timing/price profile of winners vs losers (buys only)
def profile(sel, label):
    rem = defaultdict(lambda: [0, 0.0, 0.0]); pxb = defaultdict(lambda: [0, 0.0, 0.0])
    for t in tape:
        if t["w"] not in sel or str(t["side"]).upper() != "BUY":
            continue
        md = meta[t["slug"]]; end = md["start"] + md["window"]; r = end - t["ts"]
        won = 1.0 if ((str(t["o"]).lower() == "up") == md["up"]) else 0.0
        kb = "last30" if r <= 30 else "last60" if r <= 60 else "last120" if r <= 120 else "last300" if r <= 300 else "earlier"
        pb = "<0.3" if t["p"] < 0.3 else "<0.6" if t["p"] < 0.6 else "<0.85" if t["p"] < 0.85 else "<0.95" if t["p"] < 0.95 else ">=0.95"
        for d, k in ((rem, kb), (pxb, pb)):
            d[k][0] += 1; d[k][1] += t["s"] * t["p"]; d[k][2] += t["s"] * (won - t["p"])
    print(f"\n{label}: by time left  " + "  ".join(f"{k}: n={v[0]} ${v[1]:,.0f} pnl/$ {v[2] / v[1]:+.3f}" for k, v in sorted(rem.items()) if v[1]))
    print(f"{label}: by price      " + "  ".join(f"{k}: n={v[0]} ${v[1]:,.0f} pnl/$ {v[2] / v[1]:+.3f}" for k, v in sorted(pxb.items()) if v[1]))
top = {r["wallet"] for r in rows[:20]}; bot = {r["wallet"] for r in rows[-20:]}
profile(top, "TOP-20 wallets"); profile(bot, "BOTTOM-20 wallets"); profile(set(W), "ALL wallets")
json.dump({"generated": time.time(), "wallets": rows[:300], "n_wallets": len(rows), "fills": len(tape)}, open(f"{D}/wallets_summary.json", "w"), indent=0)
# does the official priceToBeat equal our proxy's pre-60 mean?  (compare later with the feed TWAP)
W2 = [json.loads(l) for l in open(f"{D}/windows.jsonl")]
diffs = []
for w in W2:
    md = meta.get(w["slug"])
    if md and md.get("ptb") and w.get("mean_pre60"):
        diffs.append((md["ptb"] - w["mean_pre60"]) / md["ptb"] * 1e4)
if diffs:
    diffs.sort(); print(f"\nofficial priceToBeat vs Binance pre-60 mean: median {diffs[len(diffs)//2]:+.1f} bp, 10-90%: {diffs[len(diffs)//10]:+.1f}..{diffs[9*len(diffs)//10]:+.1f} bp (n={len(diffs)})")
