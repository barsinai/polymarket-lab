"""Riskless-structure scanner (read-only, NO ORDERS). Two families of pricing that must hold by construction:

1. negRisk events (one market per outcome, exactly one resolves YES):
     buy every YES at its best ask: costs sum(ask_i), pays exactly 1        -> profit if sum < 1
     buy every NO  at its best ask: costs sum(noask_i), pays exactly n - 1  -> profit if sum < n - 1
2. ladders inside one event (same question, different date or threshold): 'by an earlier date' can never be more likely
   than 'by a later date'; 'reach a higher price' never more likely than 'reach a lower one' (and the reverse for 'dip to').
   A violation (earlier/harder YES bid > later/easier YES ask) is closed by buying the easier YES and the harder NO:
   cost = ask_easy + noask_hard, payoff >= 1 in every outcome.

Executable size = the smallest best-level size across the legs. Fees: reported both fee-free and with the
0.07*p*(1-p) taker fee per leg (conservative: most non-crypto markets have no taker fee). Writes data/slow/arb_scan.json
and appends every opportunity to data/slow/arb_log.jsonl (one line per opportunity per scan) so frequency and size over
time can be measured before anything is traded."""
import json, os, re, time, datetime as dt
from itertools import combinations
import requests

GAMMA = "https://gamma-api.polymarket.com"; CLOB = "https://clob.polymarket.com"; D = "data/slow"; os.makedirs(D, exist_ok=True)
S = requests.Session(); S.headers["User-Agent"] = "polymarket-lab-research/0.1"
MIN_EDGE = float(os.environ.get("MIN_EDGE", "0.003"))
now = dt.datetime.now(dt.timezone.utc)


def get(url, params=None, tries=3):
    for i in range(tries):
        try:
            r = S.get(url, params=params, timeout=25)
            if r.status_code == 200:
                return r.json()
            time.sleep(1 + i)
        except Exception:  # noqa: BLE001
            time.sleep(1 + i)
    return None


def books(tokens):
    """best ask (price, size) and best bid per token via the batch endpoint, 400 at a time"""
    out = {}
    tokens = list(dict.fromkeys(tokens))
    for i in range(0, len(tokens), 400):
        chunk = tokens[i:i + 400]
        for k in range(3):
            try:
                r = S.post(f"{CLOB}/books", json=[{"token_id": t} for t in chunk], timeout=40)
                if r.status_code == 200:
                    for b in r.json():
                        asks = sorted(((float(a["price"]), float(a["size"])) for a in b.get("asks") or []))
                        bids = sorted(((float(a["price"]), float(a["size"])) for a in b.get("bids") or []), reverse=True)
                        out[b.get("asset_id")] = (asks[0] if asks else None, bids[0] if bids else None)
                    break
                time.sleep(2 + k)
            except Exception:  # noqa: BLE001
                time.sleep(2 + k)
    return out


fee = lambda p: 0.07 * p * (1 - p)
events = []; offset = 0
while offset < 6000:
    page = get(f"{GAMMA}/events", {"active": "true", "closed": "false", "limit": 100, "offset": offset})
    if not page:
        break
    events += page; offset += 100
    if len(page) < 100:
        break
print("active events", len(events), flush=True)

SKIP = re.compile(r"updown|up-or-down|-5m-|-15m-|-4h-", re.I)
groups = []; tokens = []
for e in events:
    ms = [m for m in e.get("markets") or [] if m.get("active") and not m.get("closed") and m.get("clobTokenIds") and not SKIP.search(m.get("slug") or "")]
    rows = []
    for m in ms:
        try:
            t = json.loads(m["clobTokenIds"])
        except ValueError:
            continue
        if len(t) == 2:
            rows.append({"q": m.get("question") or "", "item": m.get("groupItemTitle") or "", "slug": m.get("slug"), "yes": t[0], "no": t[1],
                         "accepting": m.get("acceptingOrders", True), "end": m.get("endDate")})
            tokens += t
    if rows:
        groups.append({"title": e.get("title"), "slug": e.get("slug"), "neg_risk": bool(e.get("negRisk") or e.get("enableNegRisk")),
                       "n_markets_total": len(e.get("markets") or []), "rows": rows})
print("events with tradable binaries", len(groups), "tokens", len(tokens), flush=True)
B = books(tokens)
print("books read", len(B), flush=True)
opps = []

# ---- 1. negRisk sums (only when every outcome market of the event is open and has a book)
for g in groups:
    if not g["neg_risk"] or len(g["rows"]) < 2 or len(g["rows"]) != g["n_markets_total"]:
        continue
    ya = [B.get(r["yes"], (None, None))[0] for r in g["rows"]]; na = [B.get(r["no"], (None, None))[0] for r in g["rows"]]
    n = len(g["rows"])
    if all(ya):
        cost = sum(a[0] for a in ya); size = min(a[1] for a in ya); cost_fee = cost + sum(fee(a[0]) for a in ya)
        if 1 - cost >= MIN_EDGE:
            opps.append({"kind": "negrisk_all_yes", "event": g["title"], "slug": g["slug"], "n": n, "has_other": any(re.search(r"\b(other|none|no one|nobody|field)\b", (r["item"] + " " + r["q"]).lower()) for r in g["rows"]),
                         "outcomes": [r["item"] or r["q"][:40] for r in g["rows"]], "cost": round(cost, 4), "payoff": 1, "edge": round(1 - cost, 4),
                         "edge_after_fee": round(1 - cost_fee, 4), "size_shares": round(size, 2), "usd_at_size": round(size * cost, 2)})
    if all(na):
        cost = sum(a[0] for a in na); size = min(a[1] for a in na); cost_fee = cost + sum(fee(a[0]) for a in na)
        if (n - 1) - cost >= MIN_EDGE:
            opps.append({"kind": "negrisk_all_no", "event": g["title"], "slug": g["slug"], "n": n, "cost": round(cost, 4), "payoff": n - 1, "edge": round(n - 1 - cost, 4),
                         "edge_after_fee": round(n - 1 - cost_fee, 4), "size_shares": round(size, 2), "usd_at_size": round(size * cost, 2)})

# ---- 2. ladders: same text up to one date or one number
MONTHS = {m: i for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"], 1)}
DATE = re.compile(r"\b(by|before|on or before|through|until)\s+(?:the\s+end\s+of\s+)?(january|february|march|april|may|june|july|august|september|october|november|december)\s*(\d{1,2})?(?:,?\s*(20\d\d))?", re.I)
NUM = re.compile(r"\$?\s?(\d[\d,]*\.?\d*)\s*(k|m|b|%)?", re.I)


def date_key(q):
    m = DATE.search(q)
    if not m:
        return None, None
    mon = MONTHS[m.group(2).lower()]; day = int(m.group(3)) if m.group(3) else 31; yr = int(m.group(4)) if m.group(4) else now.year
    return (yr, mon, day), q[:m.start()] + "<DATE>" + q[m.end():]


def num_key(q):
    ms = list(NUM.finditer(q))
    ms = [m for m in ms if not re.fullmatch(r"20\d\d", m.group(1))]
    if len(ms) != 1:
        return None, None
    m = ms[0]; v = float(m.group(1).replace(",", "")) * {"k": 1e3, "m": 1e6, "b": 1e9}.get((m.group(2) or "").lower(), 1)
    return v, q[:m.start()] + "<N>" + q[m.end():]


for g in groups:
    rows = g["rows"]
    if len(rows) < 2:
        continue
    for kind, keyf in (("date", date_key), ("num", num_key)):
        buckets = {}
        for r in rows:
            k, tmpl = keyf(r["q"])
            if k is not None:
                buckets.setdefault(tmpl, []).append((k, r))
        for tmpl, L in buckets.items():
            if len(L) < 2:
                continue
            low = (tmpl + " " + (g["title"] or "")).lower()
            if kind == "date":
                if re.search(r"\b(through|until|continues?|remain|still|stays?|last|survive|hold)\b", low):
                    easier = lambda a, b: a[0] < b[0]                # survival ('continues through'): the EARLIER date is easier
                elif re.search(r"\b(by|before|on or before)\b", low):
                    easier = lambda a, b: a[0] > b[0]                # cumulative ('by'): the later date is easier
                else:
                    continue
            elif re.search(r"\(low\)|how low|\b(dip|fall|drop|below|under|less than|lower|bottom|low)\b", low):
                easier = lambda a, b: a[0] > b[0]                    # downward touch / 'below': the higher threshold is easier
            elif re.search(r"\(high\)|how high|\b(reach|hit|above|over|more than|at least|exceed|higher|or more|top|peak)\b|\+", low):
                easier = lambda a, b: a[0] < b[0]                    # upward touch / 'above': the lower threshold is easier
            else:
                continue                                              # 'between' buckets etc.: no ordering
            for a, b in combinations(L, 2):
                if a[0] == b[0]:
                    continue
                e_, h_ = (a, b) if easier(a, b) else (b, a)
                ya = B.get(e_[1]["yes"], (None, None))[0]; hb = B.get(h_[1]["yes"], (None, None))[1]; hna = B.get(h_[1]["no"], (None, None))[0]
                if not ya or not hna:
                    continue
                cost = ya[0] + hna[0]
                if 1 - cost >= MIN_EDGE:
                    size = min(ya[1], hna[1])
                    opps.append({"kind": f"ladder_{kind}", "event": g["title"], "slug": g["slug"], "easy": e_[1]["q"], "hard": h_[1]["q"], "easy_yes_ask": ya[0],
                                 "hard_no_ask": hna[0], "hard_yes_bid": hb[0] if hb else None, "cost": round(cost, 4), "edge": round(1 - cost, 4),
                                 "edge_after_fee": round(1 - cost - fee(ya[0]) - fee(hna[0]), 4), "size_shares": round(size, 2), "usd_at_size": round(size * cost, 2)})

opps.sort(key=lambda o: -o["edge"] * min(o["size_shares"], 1000))
stamp = now.strftime("%Y-%m-%d %H:%M")
json.dump({"scanned": stamp, "events": len(events), "groups": len(groups), "books": len(B), "opps": opps}, open(f"{D}/arb_scan.json", "w"), indent=0)
with open(f"{D}/arb_log.jsonl", "a") as fh:
    for o in opps:
        fh.write(json.dumps(dict(o, scanned=stamp), ensure_ascii=False) + "\n")
print(f"\nopportunities with edge >= {MIN_EDGE}: {len(opps)}")
for o in opps[:40]:
    extra = f"| easy: {o['easy'][:60]} | hard: {o['hard'][:60]}" if o["kind"].startswith("ladder") else f"| n {o['n']} other={o.get('has_other')} {o.get('outcomes', [])[:8]}"
    print(f"  {o['kind']:16} edge {o['edge']:+.4f} (after fee {o['edge_after_fee']:+.4f}) size {o['size_shares']:8.1f} sh ${o['usd_at_size']:8.1f}  {o['event'][:50]} {extra}")
