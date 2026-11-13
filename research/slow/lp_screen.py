"""Liquidity-provider screen (read-only, 11-13): where is the reward pool large relative to the taker flow?
Paper MM evidence: our fills lose ~5.4% of their notional to informed flow (2cl, 11 days, every category -3.6..-11.3%), and the
live pilot was paid ~1/5 of the reward we estimated. Net per market ~ share x (h * R - 0.054 * V) with R = pool $/day,
V = taker volume $/day, h = realized/estimated reward (0.2 in the pilot). So the only candidates are markets where R/V is high.
Steps: all reward markets (CLOB sampling-markets: pool, min size, max spread) -> Gamma volume24hr / volume1wk / liquidity / end
-> current books for the ones with R/V >= 0.05 (up to 1,500) -> competing score near the mid and our estimated share for a
two-sided quote of the minimum size at 1c from the mid. Writes data/research/lp_screen.json and prints the summary."""
import json, time, datetime as dt
import requests
S = requests.Session(); S.headers["User-Agent"] = "polymarket-lab-research/0.1"
CLOB = "https://clob.polymarket.com"; GAMMA = "https://gamma-api.polymarket.com"
T0 = time.time()


def get(url, params=None, method="GET", body=None):
    for k in range(4):
        try:
            r = S.request(method, url, params=params, json=body, timeout=30)
            if r.status_code == 429:
                time.sleep(2 + 2 * k); continue
            return r.json() if r.status_code == 200 else None
        except Exception:  # noqa: BLE001
            time.sleep(1 + k)
    return None


# 1. reward markets
rw = {}; cur = ""
for _ in range(600):
    d = get(f"{CLOB}/sampling-markets", {"next_cursor": cur})
    if not d:
        break
    for m in d.get("data") or []:
        r = m.get("rewards") or {}
        rate = sum(x.get("rewards_daily_rate") or 0 for x in r.get("rates") or [])
        toks = [str(t.get("token_id")) for t in m.get("tokens") or []]
        if rate > 0 and m.get("condition_id") and toks:
            rw[m["condition_id"]] = {"rate": rate, "min": float(r.get("min_size") or 0), "v": float(r.get("max_spread") or 0),
                                     "q": (m.get("question") or "")[:110], "tok": toks[0], "end": m.get("end_date_iso"),
                                     "tick": float(m.get("minimum_tick_size") or 0.01)}
    cur = d.get("next_cursor") or ""
    if not cur or cur == "LTE=":
        break
print("reward markets", len(rw), "total pool $/day", round(sum(x["rate"] for x in rw.values())), flush=True)
# 2. Gamma volumes
cids = list(rw)
for i in range(0, len(cids), 40):
    ms = get(f"{GAMMA}/markets", [("condition_ids", c) for c in cids[i:i + 40]] + [("limit", 100)]) or []
    for m in ms:
        c = m.get("conditionId")
        if c in rw:
            rw[c].update(v24=float(m.get("volume24hr") or 0), v1w=float(m.get("volume1wk") or 0), liq=float(m.get("liquidityNum") or 0),
                         spread=m.get("spread"), bid=m.get("bestBid"), ask=m.get("bestAsk"), slug=m.get("slug"))
    if time.time() - T0 > 1500:
        break
have = [c for c in rw if "v1w" in rw[c]]
print("with Gamma volume", len(have), "(batch of 40 condition_ids per Gamma call)", flush=True)
# 3. books for the high pool/volume ones
for c in have:
    x = rw[c]; vday = max(x["v1w"] / 7, x["v24"], 1.0); x["vday"] = vday; x["r_over_v"] = x["rate"] / vday
cand = sorted([c for c in have if rw[c]["r_over_v"] >= 0.05], key=lambda c: -rw[c]["rate"])[:1500]
toks = [rw[c]["tok"] for c in cand]
books = {}
for i in range(0, len(toks), 50):
    bl = get(f"{CLOB}/books", method="POST", body=[{"token_id": t} for t in toks[i:i + 50]]) or []
    for b in bl:
        books[str(b.get("asset_id"))] = b
    if time.time() - T0 > 2400:
        break


def score(levels, mid, v, ms, is_bid):
    s_ = 0.0
    for p, sz in levels:
        s = 100 * ((mid - p) if is_bid else (p - mid))
        if 0 <= s < v and sz >= ms:
            s_ += ((v - s) / v) ** 2 * sz
    return s_


for c in cand:
    x = rw[c]; b = books.get(x["tok"])
    if not b:
        continue
    bids = sorted(((float(o["price"]), float(o["size"])) for o in b.get("bids") or []), reverse=True)
    asks = sorted((float(o["price"]), float(o["size"])) for o in b.get("asks") or [])
    if not bids or not asks:
        x["book"] = "one-sided"; continue
    mid = (bids[0][0] + asks[0][0]) / 2; x["mid"] = mid; x["book_spread"] = round(asks[0][0] - bids[0][0], 4)
    cb, ca = score(bids, mid, x["v"], x["min"], True), score(asks, mid, x["v"], x["min"], False)
    comp = max(min(cb, ca), (cb + ca) / 3)
    size = max(x["min"], 20.0); f = ((x["v"] - 1) / x["v"]) ** 2 if x["v"] > 1 else 0
    ours = size * f
    x["comp"] = round(comp, 1); x["our_size"] = size
    x["share_est"] = ours / (comp + ours) if ours > 0 else 0
    x["rpd_est"] = x["rate"] * x["share_est"] if 0.10 <= mid <= 0.90 or True else 0
    x["capital"] = size * 1.0
json.dump({"at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M"), "markets": rw}, open("data/research/lp_screen.json", "w"))
# 4. summary
tot = sum(x["rate"] for x in rw.values())
for thr in (0.054, 0.27, 1.0):
    sel = [x for x in rw.values() if x.get("r_over_v", 0) >= thr]
    print(f"pool/volume >= {thr}: markets {len(sel)}  pool ${sum(x['rate'] for x in sel):,.0f}/day of ${tot:,.0f}")
q = [x for x in rw.values() if "share_est" in x and 0.10 <= x.get("mid", 0) <= 0.90]
q.sort(key=lambda x: -x["rpd_est"] / x["capital"])
print("\nbooked candidates (mid 0.10-0.90):", len(q))
for h in (1.0, 0.2):
    for n in (20, 50, 100):
        top = q[:n]
        R = sum(x["rpd_est"] for x in top) * h; cap = sum(x["capital"] for x in top)
        fl = sum(x["share_est"] * x["vday"] for x in top) * 0.054
        print(f"  haircut {h:.1f}, best {n:3} markets: est reward ${R:7.1f}/day on ${cap:6.0f} min-size quotes; expected fill loss ~${fl:6.1f}/day -> net ${R - fl:+7.1f}/day")
print("\ntop 25 by estimated reward per $ (before haircut):")
for x in q[:25]:
    print(f"  pool ${x['rate']:6.1f}/d  vol ${x['vday']:9.0f}/d  min {x['min']:4.0f}  v {x['v']:.1f}c  comp {x['comp']:8.1f}  book {x['book_spread']:.3f}  mid {x['mid']:.3f}  "
          f"share {x['share_est']:.2f}  ${x['rpd_est']:6.2f}/d  {x['q'][:60]}")
