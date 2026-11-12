"""Probe (read-only, NO ORDERS): Polymarket "Bitcoin/Ethereum above X on <date>" and "price between" markets vs the
risk-neutral probability implied by Deribit options on the same coin.

Deribit (public API, no key): every listed BTC/ETH option with its mark implied vol and the forward of its expiry.
For a Polymarket strike K resolving at time T (the Binance 1-minute close at 12:00 ET on the date, per the market
rules): total variance w(K, T) interpolated linearly in time between the two Deribit expiries around T, at strike K
(linear in strike between the listed strikes), forward F interpolated the same way. Digital P(S_T > K) = N(d2) minus
the skew term (a digital is a call spread: dC/dK = -N(d2) + vega * dsigma/dK). Between-markets = P(> lo) - P(> hi).
Writes data/research/options_probe.json and prints the gaps vs the Polymarket book (YES ask, bid)."""
import json, math, os, re, time, datetime as dt
import requests

GAMMA = "https://gamma-api.polymarket.com"; CLOB = "https://clob.polymarket.com"; DERIBIT = "https://www.deribit.com/api/v2/public"
S = requests.Session(); S.headers["User-Agent"] = "polymarket-lab-research/0.1"
now = dt.datetime.now(dt.timezone.utc)
COIN = {"bitcoin": "BTC", "ethereum": "ETH"}
MON = {m: i + 1 for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august", "september",
                                       "october", "november", "december"])}


def get(url, params=None, tries=3):
    for i in range(tries):
        try:
            r = S.get(url, params=params, timeout=30)
            if r.status_code == 200:
                return r.json()
            print("HTTP", r.status_code, url, r.text[:200])
        except Exception as e:  # noqa: BLE001
            print("ERR", url, str(e)[:200])
        time.sleep(1 + i)
    return None


def N(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


# 1. Deribit surface
surf = {}
for cur in ("BTC", "ETH"):
    r = get(f"{DERIBIT}/get_book_summary_by_currency", {"currency": cur, "kind": "option"})
    if not r or "result" not in r:
        print("Deribit unavailable for", cur); continue
    by_exp = {}
    for o in r["result"]:
        name = o["instrument_name"]                       # BTC-14NOV26-95000-C
        parts = name.split("-")
        if len(parts) != 4 or not o.get("mark_iv"):
            continue
        exp = dt.datetime.strptime(parts[1], "%d%b%y").replace(hour=8, tzinfo=dt.timezone.utc)
        if exp <= now:
            continue
        k = float(parts[2])
        e = by_exp.setdefault(exp, {"F": o.get("underlying_price"), "iv": {}})
        e["iv"].setdefault(k, []).append(o["mark_iv"] / 100.0)
        if o.get("underlying_price"):
            e["F"] = o["underlying_price"]
    surf[cur] = {exp: {"F": e["F"], "iv": sorted((k, sum(v) / len(v)) for k, v in e["iv"].items())} for exp, e in by_exp.items()}
    print(cur, "expiries", len(surf[cur]), [x.strftime("%m-%d") for x in sorted(surf[cur])][:8])


def iv_at(smile, K):
    ks = [k for k, _ in smile]
    if K <= ks[0]:
        return smile[0][1], 0.0
    if K >= ks[-1]:
        return smile[-1][1], 0.0
    for (k1, v1), (k2, v2) in zip(smile, smile[1:]):
        if k1 <= K <= k2:
            sl = (v2 - v1) / (k2 - k1)
            return v1 + sl * (K - k1), sl
    return smile[-1][1], 0.0


def digital(cur, K, T, skew_on=True):
    """P(S_T > K) from the Deribit surface, T a datetime (skew_on=False: plain N(d2) at the strike's vol)"""
    exps = sorted(surf.get(cur, {}))
    if not exps:
        return None
    tau = (T - now).total_seconds() / (365.25 * 86400)
    lo = [e for e in exps if e <= T]; hi = [e for e in exps if e >= T]
    pts = []
    for e in ([lo[-1]] if lo else []) + ([hi[0]] if hi else []):
        t_e = max((e - now).total_seconds() / (365.25 * 86400), 1e-6)
        sig, sl = iv_at(surf[cur][e]["iv"], K)
        pts.append((t_e, sig * sig * t_e, surf[cur][e]["F"], sl * math.sqrt(t_e)))
    if len(pts) == 2 and pts[1][0] > pts[0][0]:
        a = (tau - pts[0][0]) / (pts[1][0] - pts[0][0])
        w = pts[0][1] + a * (pts[1][1] - pts[0][1]); F = pts[0][2] + a * (pts[1][2] - pts[0][2]); skew = pts[0][3] + a * (pts[1][3] - pts[0][3])
    else:
        t_e, w1, F, skew = pts[-1]; w = w1 * tau / t_e
    if w <= 0 or not F:
        return None
    sw = math.sqrt(w)
    d2 = (math.log(F / K) - w / 2) / sw
    d1 = d2 + sw
    # digital call = N(d2) - K * phi(d1)... in forward terms: -dC/dK = N(d2) - F*phi(d1)*sqrt(tau)*dsigma/dK
    phi = math.exp(-d1 * d1 / 2) / math.sqrt(2 * math.pi)
    p = N(d2) - (F * phi * skew if skew_on else 0.0)            # skew already = dsigma/dK * sqrt(t)
    return min(max(p, 0.0), 1.0)


def touch(cur, K, T):
    """P(the price touches K before T): reflection formula (zero-drift risk-neutral GBM) at the strike's vol, scaled by
    the skew-adjusted / plain terminal probability on the same side (a touch is ~2x the terminal digital)"""
    exps = sorted(surf.get(cur, {}))
    if not exps:
        return None
    S0 = surf[cur][exps[0]]["F"]
    tau = (T - now).total_seconds() / (365.25 * 86400)
    e = min((x for x in exps if x >= T), default=exps[-1])
    sig, _ = iv_at(surf[cur][e]["iv"], K)
    sw = sig * math.sqrt(max(tau, 1e-8))
    up = K >= S0
    b = math.log(K / S0) if up else math.log(S0 / K)
    if up:
        p = N((-b - sw * sw / 2) / sw) + (S0 / K) * N((-b + sw * sw / 2) / sw)
    else:
        p = N((-b + sw * sw / 2) / sw) + (S0 / K) * N((-b - sw * sw / 2) / sw)
    d_sk, d_fl = digital(cur, K, T), digital(cur, K, T, skew_on=False)
    if d_sk is None or d_fl is None:
        return min(p, 1.0)
    t_sk, t_fl = (d_sk, d_fl) if up else (1 - d_sk, 1 - d_fl)
    return min(p * (t_sk / t_fl), 1.0) if t_fl > 1e-6 else min(p, 1.0)


# 2. Polymarket markets
events = {}
emin = now.strftime("%Y-%m-%dT%H:%M:%SZ"); emax = (now + dt.timedelta(days=60)).strftime("%Y-%m-%dT%H:%M:%SZ")
for tag in ("bitcoin", "ethereum", "crypto-prices", "crypto", None):
    n0 = len(events)
    for off in range(0, 2000, 100):
        prm = {"closed": "false", "limit": 100, "offset": off, "end_date_min": emin, "end_date_max": emax, "order": "endDate", "ascending": "true"}
        if tag:
            prm["tag_slug"] = tag
        page = get(f"{GAMMA}/events", prm)
        if not page:
            break
        for ev in page:
            events[ev.get("id")] = ev
        if len(page) < 100:
            break
    print(f"tag {tag}: +{len(events) - n0} events")
events = list(events.values())
print("events scanned", len(events))
rows = []
MONTHS = "january|february|march|april|may|june|july|august|september|october|november|december"
SKIP = re.compile(r"hashprice|dominance|volatility index|kimchi|gas price|\bfirst\b|etf|flows|reserve|treasury|mcap|market cap", re.I)
NUM = r"\$?([\d,]+(?:\.\d+)?)(k?)"


def num(x, k):
    return float(x.replace(",", "")) * (1000 if k else 1)


def et(y, mo, d, h=12, mi=0):           # ET -> UTC (EST from early November to March)
    return dt.datetime(y, mo, d, h, mi, tzinfo=dt.timezone.utc) + dt.timedelta(hours=5)


def parse(q):
    c = re.search(r"\b(bitcoin|ethereum)\b", q, re.I)
    if not c or SKIP.search(q):
        return None
    coin = COIN[c.group(1).lower()]
    md = re.search(rf"\b({MONTHS})\s+(\d{{1,2}})(?:\s*-\s*(\d{{1,2}}))?(?:,\s*(\d{{4}}))?", q, re.I)
    mm = re.search(rf"\bin\s+({MONTHS})\b", q, re.I)
    tm = re.search(r"(\d{1,2})(?::(\d\d))?\s*(AM|PM)\s*ET", q, re.I)
    def yr(mo, y4):
        return int(y4) if y4 else now.year + (1 if mo < now.month - 1 else 0)
    tch = re.search(rf"\b(reach|hit|dip to)\s+{NUM}", q, re.I)
    if tch:
        K = num(tch.group(2), tch.group(3))
        if md:
            mo = MON[md.group(1).lower()]; d = int(md.group(3) or md.group(2))
            T = et(yr(mo, md.group(4)), mo, d, 23, 59)
        elif mm:
            mo = MON[mm.group(1).lower()]; y = yr(mo, None)
            T = et(y + (mo == 12), mo % 12 + 1, 1, 0, 0) - dt.timedelta(minutes=1)
        else:
            return None
        return {"kind": "touch", "coin": coin, "lo": K, "hi": None, "T": T}
    if not md:
        return None
    mo = MON[md.group(1).lower()]; y = yr(mo, md.group(4)); d = int(md.group(2))
    if tm:
        h = int(tm.group(1)) % 12 + (12 if tm.group(3).upper() == "PM" else 0)
        T = et(y, mo, d, h, int(tm.group(2) or 0))
    else:
        T = et(y, mo, d, 12, 0)
    bt = re.search(rf"\bbetween\s+{NUM}\s+and\s+{NUM}", q, re.I)
    if bt:
        return {"kind": "between", "coin": coin, "lo": num(bt.group(1), bt.group(2)), "hi": num(bt.group(3), bt.group(4)), "T": T}
    lt = re.search(rf"\b(less than|below|under)\s+{NUM}", q, re.I)
    if lt:
        return {"kind": "below", "coin": coin, "lo": num(lt.group(2), lt.group(3)), "hi": None, "T": T}
    gt = re.search(rf"\b(above|greater than|more than|over)\s+{NUM}", q, re.I)
    if gt:
        return {"kind": "above", "coin": coin, "lo": num(gt.group(2), gt.group(3)), "hi": None, "T": T}
    return None


seen_titles = {}
for ev in events:
    for m in ev.get("markets") or []:
        q = m.get("question") or ""
        r = parse(q)
        if not r:
            t = ev.get("title") or ""
            if re.search(r"bitcoin|ethereum", t, re.I) and re.search(r"price|above|below|between|hit|reach", t, re.I):
                seen_titles.setdefault(t, q)
            continue
        try:
            toks = json.loads(m.get("clobTokenIds") or "[]")
        except ValueError:
            continue
        if len(toks) != 2 or r["T"] <= now:
            continue
        r.update({"q": q, "T": r["T"].isoformat(), "yes": toks[0], "no": toks[1], "end": m.get("endDate"), "slug": m.get("slug"),
                  "desc": (m.get("description") or "")[:400]})
        rows.append(r)
print("price-threshold markets:", len(rows))
print("unmatched crypto price events (title | first question):")
for t, q in list(seen_titles.items())[:40]:
    print("  ", t, "|", q)
if rows:
    print("example rules:", rows[0]["q"], "|", rows[0]["desc"])

# 3. books
books = {}
toks = [t for r in rows for t in (r["yes"], r["no"])]
for i in range(0, len(toks), 400):
    try:
        resp = S.post(f"{CLOB}/books", json=[{"token_id": t} for t in toks[i:i + 400]], timeout=40)
        for bk in resp.json():
            asks = sorted((float(x["price"]), float(x["size"])) for x in bk.get("asks") or [])
            bids = sorted(((float(x["price"]), float(x["size"])) for x in bk.get("bids") or []), reverse=True)
            books[bk["asset_id"]] = (asks[0] if asks else None, bids[0] if bids else None)
    except Exception as e:  # noqa: BLE001
        print("books error", e)

out = []
for r in rows:
    T = dt.datetime.fromisoformat(r["T"])
    if r["kind"] == "touch":
        p = touch(r["coin"], r["lo"], T)
    else:
        p = digital(r["coin"], r["lo"], T)
        if p is not None and r["kind"] == "below":
            p = 1 - p
        if p is not None and r["kind"] == "between":
            p2 = digital(r["coin"], r["hi"], T)
            p = None if p2 is None else max(p - p2, 0.0)
    ask, bid = books.get(r["yes"], (None, None))
    no_ask, no_bid = books.get(r["no"], (None, None))
    r.update({"model": None if p is None else round(p, 4), "ask": ask, "bid": bid, "no_ask": no_ask,
              "days": round((T - now).total_seconds() / 86400, 2)})
    out.append(r)
os.makedirs("data/research", exist_ok=True)
json.dump({"at": now.isoformat(), "rows": out,
           "surface": {c: {e.isoformat(): v for e, v in d.items()} for c, d in surf.items()}}, open("data/research/options_probe.json", "w"), indent=0)
good = [r for r in out if r["model"] is not None and r["ask"] and r["bid"]]
print(f"\npriced with both: {len(good)}")
gaps = sorted(((r["ask"][0] + r["bid"][0]) / 2 - r["model"]) for r in good)
if gaps:
    print("mid - model: p10 %+.3f median %+.3f p90 %+.3f" % (gaps[len(gaps) // 10], gaps[len(gaps) // 2], gaps[9 * len(gaps) // 10]))
# summary by kind and horizon
for kind in ("above", "below", "between", "touch"):
    for lo_d, hi_d in ((0, 0.5), (0.5, 3), (3, 10), (10, 400)):
        G = [((r["ask"][0] + r["bid"][0]) / 2 - r["model"]) for r in good if r["kind"] == kind and lo_d <= r["days"] < hi_d]
        if G:
            G.sort()
            print(f"  {kind:7} {lo_d:>4}-{hi_d:<4} d: n {len(G):3}  mid - model median {G[len(G) // 2]:+.3f}  p10 {G[len(G) // 10]:+.3f}  p90 {G[9 * len(G) // 10]:+.3f}")
for r in sorted(good, key=lambda r: (r["coin"], r["T"], r["lo"])):
    if r["days"] < 0.5:
        continue
    mid = (r["ask"][0] + r["bid"][0]) / 2
    na = r["no_ask"][0] if r.get("no_ask") else None
    flag = " BUY YES" if r["model"] - r["ask"][0] >= 0.03 else (" BUY NO" if na is not None and (1 - r["model"]) - na >= 0.03 else "")
    print(f"  {r['coin']} {r['days']:5.1f} d  {r['kind']:>7} {r['lo']:>9,.0f}{'' if r['hi'] is None else '-' + format(r['hi'], ',.0f'):>9}"
          f"  model {r['model']:.3f}  bid {r['bid'][0]:.3f} ask {r['ask'][0]:.3f} (size {r['ask'][1]:.0f})  mid-model {mid - r['model']:+.3f}{flag}")
