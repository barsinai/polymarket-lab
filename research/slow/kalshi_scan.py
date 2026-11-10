"""Kalshi vs Polymarket price gaps (read-only, public data). Lists Kalshi's open events (skipping the KXMVE parlay
combos and sports), keeps liquid binary markets, and matches them to our Polymarket candidates by title similarity.
Writes data/slow/kalshi_markets.json and data/slow/kalshi_matches.json; prints the matches with both prices so the
pairs can be checked by eye before any of them is trusted (titles that look alike can resolve on different rules)."""
import json, re, time, collections
import requests
S = requests.Session(); S.headers["User-Agent"] = "polymarket-lab-research/0.1"
base = "https://api.elections.kalshi.com/trade-api/v2"
SKIP_CAT = {"Sports"}
events = []; cursor = None
for i in range(60):
    params = {"limit": 200, "status": "open", "with_nested_markets": "true"}
    if cursor: params["cursor"] = cursor
    r = S.get(f"{base}/events", params=params, timeout=30)
    if r.status_code != 200:
        print("events status", r.status_code, r.text[:200]); break
    d = r.json(); page = d.get("events", []); events += page; cursor = d.get("cursor")
    if not cursor or not page: break
print("open events", len(events), "categories", collections.Counter(e.get("category") for e in events).most_common(12), flush=True)
sample = next((m for e in events if not (e.get("series_ticker") or "").startswith("KXMVE") and e.get("category") not in SKIP_CAT for m in (e.get("markets") or [])), None)
print("sample nested market:", json.dumps(sample)[:1500] if sample else None, flush=True)
mk = []
for e in events:
    if (e.get("series_ticker") or "").startswith("KXMVE") or e.get("category") in SKIP_CAT: continue
    for m in e.get("markets", []) or []:
        vol = float(m.get("volume_24h") or m.get("volume_24h_fp") or m.get("volume") or m.get("volume_fp") or 0)
        yb, ya = m.get("yes_bid"), m.get("yes_ask")
        if yb is None and m.get("yes_bid_dollars") is not None:
            yb, ya = float(m["yes_bid_dollars"]) * 100, float(m.get("yes_ask_dollars") or 0) * 100
        if yb is None or ya is None or vol < 200: continue
        mk.append({"ticker": m.get("ticker"), "event": e.get("title"), "title": m.get("title") or m.get("yes_sub_title") or "", "sub": m.get("yes_sub_title"),
                   "category": e.get("category"), "yes_bid": yb / 100, "yes_ask": ya / 100, "vol24": vol, "volume": float(m.get("volume") or 0),
                   "close": (m.get("close_time") or "")[:16], "rules": (m.get("rules_primary") or "")[:1500]})
print("liquid non-sports binary markets", len(mk))
json.dump(mk, open("data/slow/kalshi_markets.json", "w"))
# match to Polymarket candidates by token overlap
STOP = set("will the be a an of in on by to at for or and is it this that before after than with from as its into over under up down yes no 2026 2025 november december october".split())
def toks(s): return {w for w in re.findall(r"[a-z0-9$%.]+", s.lower()) if w not in STOP and len(w) > 1}
C = json.load(open("data/slow/candidates.json"))
matches = []
for c in C:
    tq = toks(c["question"]); best = None
    for m in mk:
        tm = toks(f"{m['event']} {m['title']} {m['sub'] or ''}")
        j = len(tq & tm) / max(1, len(tq | tm))
        if best is None or j > best[0]: best = (j, m)
    if best and best[0] >= 0.25:
        m = best[1]; matches.append({"sim": round(best[0], 2), "poly": c["question"], "poly_yes": c["yes"], "poly_end": c["end"], "kalshi": f"{m['event']} | {m['title']} {m['sub'] or ''}",
                                      "k_bid": m["yes_bid"], "k_ask": m["yes_ask"], "k_close": m["close"], "k_vol24": m["vol24"], "ticker": m["ticker"], "slug": c["slug"], "k_rules": m["rules"]})
matches.sort(key=lambda x: -abs(x["poly_yes"] - (x["k_bid"] + x["k_ask"]) / 2))
json.dump(matches, open("data/slow/kalshi_matches.json", "w"), indent=0)
print(f"\nmatches (title similarity >= 0.25): {len(matches)}")
for x in matches[:50]:
    km = (x["k_bid"] + x["k_ask"]) / 2
    print(f"gap {x['poly_yes'] - km:+.2f}  poly {x['poly_yes']:.2f} | kalshi {x['k_bid']:.2f}-{x['k_ask']:.2f} vol24 {x['k_vol24']:.0f} sim {x['sim']}\n     P: {x['poly']}\n     K: {x['kalshi'][:120]}")
