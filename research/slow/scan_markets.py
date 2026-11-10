"""Daily scan for the research track (read-only): every active Polymarket market that resolves within HORIZON days,
with enough liquidity to matter, minus the crypto price windows and other pure-price markets. Writes
data/slow/candidates.json (list) and prints a short table. Also tags each market's resolution rule with the mechanics
that have burned crowds before (specific data source, exact time / timezone, averages, rounding, 'official'
announcements, multiple conditions) so the rules can be read with those in mind.
"""
import json, os, re, time, datetime as dt
import requests

GAMMA = "https://gamma-api.polymarket.com"; D = "data/slow"; os.makedirs(D, exist_ok=True)
HORIZON = float(os.environ.get("HORIZON_DAYS", "28")); MIN_LIQ = float(os.environ.get("MIN_LIQ", "5000")); MIN_VOL = float(os.environ.get("MIN_VOL24", "500"))
S = requests.Session(); S.headers["User-Agent"] = "polymarket-lab-research/0.1"


def get(url, params, tries=4):
    for i in range(tries):
        try:
            r = S.get(url, params=params, timeout=25)
            if r.status_code == 200:
                return r.json()
            time.sleep(1 + i)
        except Exception:  # noqa: BLE001
            time.sleep(1 + i)
    return None


now = dt.datetime.now(dt.timezone.utc)
rows, offset = [], 0
while offset < 20000:
    d = get(f"{GAMMA}/markets", {"active": "true", "closed": "false", "limit": 100, "offset": offset, "order": "volume24hr", "ascending": "false"})
    if not d:
        break
    rows += d; offset += 100
    if len(d) < 100 or float(d[-1].get("volume24hr") or 0) < MIN_VOL / 4:
        break
print("markets fetched", len(rows), flush=True)

PRICE_RE = re.compile(r"\b(up or down|updown|above|below|price of|hit \$|reach \$|close at|higher than \$|lower than \$|\$[\d,]+(\.\d+)?k?\b.*\b(bitcoin|btc|eth|ethereum|solana|sol|xrp|doge|bnb|gold|silver|oil|s&p|nasdaq|dow|nvidia|tesla|stock)|\b(bitcoin|btc|ethereum|eth|solana|xrp)\b.*\$[\d,]+)", re.I)
TAGS = [
    ("data_source", re.compile(r"\b(according to|per the|as reported by|as published by|official(ly)?|data from|source|website|coinbase|binance|chainlink|bloomberg|reuters|nyt|associated press|ap\b)", re.I)),
    ("exact_time", re.compile(r"\b(\d{1,2}:\d{2}\s?(am|pm)?\s?(et|est|edt|utc|gmt|pt|pst|pdt)|noon|midnight|11:59|12:00|at the close|closing)\b", re.I)),
    ("average_or_twap", re.compile(r"\b(average|mean|twap|weighted|median|aggregate|cumulative|total)\b", re.I)),
    ("rounding_threshold", re.compile(r"\b(rounded|rounding|at least|or more|or higher|or lower|greater than or equal|strictly|inclusive|exclusive|between)\b", re.I)),
    ("announcement", re.compile(r"\b(announce|announced|announcement|confirm|confirmed|officially|press release|statement|declare|certif)", re.I)),
    ("multi_condition", re.compile(r"\b(and|both|all of|any of|either|unless|except|provided that)\b", re.I)),
    ("ambiguity_clause", re.compile(r"\b(ambigu|unclear|discretion|sole|reasonable|consensus of credible|credible reporting|in the event)\b", re.I)),
]
cands = []
for m in rows:
    try:
        end = dt.datetime.fromisoformat((m.get("endDate") or "").replace("Z", "+00:00"))
    except ValueError:
        continue
    days = (end - now).total_seconds() / 86400
    if not (0.5 <= days <= HORIZON):
        continue
    liq = float(m.get("liquidityNum") or m.get("liquidity") or 0); vol = float(m.get("volume24hr") or 0)
    if liq < MIN_LIQ or vol < MIN_VOL:
        continue
    q = m.get("question") or ""; desc = m.get("description") or ""
    if PRICE_RE.search(q) or re.search(r"updown|up-or-down", m.get("slug") or "", re.I):
        continue
    try:
        prices = [float(x) for x in json.loads(m.get("outcomePrices") or "[]")]; outcomes = json.loads(m.get("outcomes") or "[]")
    except ValueError:
        prices, outcomes = [], []
    if len(prices) != 2 or min(prices) < 0.03 or max(prices) > 0.97:
        continue                                     # near-settled or non-binary: no room for a forecast to differ
    tags = [t for t, rx in TAGS if rx.search(desc)]
    cands.append({"id": m.get("id"), "slug": m.get("slug"), "question": q, "end": end.strftime("%Y-%m-%d %H:%M"), "days": round(days, 1),
                  "yes": prices[0], "outcomes": outcomes, "liquidity": round(liq), "vol24": round(vol), "volume": round(float(m.get("volumeNum") or 0)),
                  "tags": tags, "rule_len": len(desc), "description": desc[:2500], "tokens": json.loads(m.get("clobTokenIds") or "[]"),
                  "event": (m.get("events") or [{}])[0].get("title") if m.get("events") else None, "scanned": now.strftime("%Y-%m-%d %H:%M")})
cands.sort(key=lambda c: -c["liquidity"])
json.dump(cands, open(f"{D}/candidates.json", "w"), indent=0)
print(f"candidates resolving in 0.5-{HORIZON:.0f} days with liquidity >= {MIN_LIQ:.0f} and 24h volume >= {MIN_VOL:.0f}: {len(cands)}")
print(f"{'days':>5} {'yes':>5} {'liq':>8} {'vol24':>7}  tags / question")
for c in cands[:60]:
    print(f"{c['days']:5.1f} {c['yes']:5.2f} {c['liquidity']:8} {c['vol24']:7}  [{','.join(c['tags'])}] {c['question'][:95]}")
from collections import Counter
print("\nrule tags over all candidates:", dict(Counter(t for c in cands for t in c["tags"])))
