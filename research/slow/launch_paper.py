"""N58 forward paper tracker (NO ORDERS, public endpoints only): buy NO right after a new CULTURE market lists.

Back-test (12-week tape, found after looking - LESSONS 22): culture NO, one follower fill per market in the launch hour, +7.4 pts per
share [5.5, 9.3] (cycle 25); N60 (cycle 26) with the follower >= 300 s later +8.4 [6.0, 10.7], halves +10.6 / +5.8, non-mention +5.6;
most of it is in the first 10 minutes after the first trade. The same NO 24-72 h later: +0.7.

Rule, fixed 11-16 before the first position:
  every POLL s list the newest open events of the culture tags (mention-markets, earnings-calls, mrbeast, youtube, movies, music,
  awards, pop-culture); for every binary market not seen before whose launch L (acceptingOrdersTimestamp, else createdAt) is < 60 min
  ago, that ends >= 24 h after L and >= 1 h from now: read the NO book; paper-buy $10 at the best NO ask if 0.05 <= ask <= 0.90 and
  NO ask - NO bid <= 0.10; fee = market rate * a(1-a) * shares. One position per market. Settled at resolution (Gamma closed=true).
  Also logged for every candidate (bought or not): age at sight, ask, spread, why skipped -> the opportunity rate.
Decision (pre-registered): kill if the forward edge <= +1 pt per share or its event interval reaches below -1 after 100 markets /
40 events; promote (propose with numbers) only after 300 markets / 100 events / 3 weeks. Report guard (LESSONS 28): 'settled N' and
'open past their end M'.
Storage: data/launch/pos-<day>.jsonl, upd-<day>.jsonl, cand-<day>.jsonl, state.json, report.json."""
import json, os, time, glob, random, datetime as dt, collections
import requests

G = "https://gamma-api.polymarket.com"; CLOB = "https://clob.polymarket.com"
RUN_MIN = float(os.environ.get("RUN_MIN", "55")); POLL = float(os.environ.get("POLL", "150")); STAKE = 10.0
D = os.environ.get("LN_DIR", "data/launch"); STATE = f"{D}/state.json"; REP = f"{D}/report.json"
TAGS = ["mention-markets", "earnings-calls", "mrbeast", "youtube", "movies", "music", "awards", "pop-culture"]
CAT = {"mention-markets": "mention", "earnings-calls": "mention"}
S = requests.Session(); S.headers["User-Agent"] = "polymarket-lab-research/0.1"
T0 = time.time(); stats = collections.Counter()


def get(url, params=None, tries=3):
    for k in range(tries):
        try:
            r = S.get(url, params=params, timeout=20)
            if r.status_code == 200:
                return r.json()
            stats[f"http {r.status_code}"] += 1
            if r.status_code != 429:
                return None
        except Exception:  # noqa: BLE001
            stats["http error"] += 1
        time.sleep(1 + 2 * k)
    return None


def ts(s):
    if not s:
        return None
    try:
        return dt.datetime.fromisoformat(str(s).replace(" ", "T").replace("Z", "+00:00").replace("+00+00:00", "+00:00")).timestamp()
    except Exception:  # noqa: BLE001
        try:
            return dt.datetime.fromisoformat(str(s)[:19]).replace(tzinfo=dt.timezone.utc).timestamp()
        except Exception:  # noqa: BLE001
            return None


def load(path, default):
    try:
        return json.load(open(path))
    except Exception:  # noqa: BLE001
        return default


def dump(obj, path):
    with open(path + ".tmp", "w") as fh:
        json.dump(obj, fh, indent=1)
    os.replace(path + ".tmp", path)


_checked = set()


def append(kind, obj):
    path = f"{D}/{kind}-{time.strftime('%Y-%m-%d', time.gmtime())}.jsonl"
    if path not in _checked:
        _checked.add(path)
        if os.path.exists(path) and os.path.getsize(path) and open(path, "rb").read()[-1:] != b"\n":
            open(path, "a").write("\n")
    with open(path, "a") as fh:
        fh.write(json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n")


def jl(x):
    if isinstance(x, list):
        return x
    try:
        return json.loads(x or "[]")
    except Exception:  # noqa: BLE001
        return []


def fee_rate(m):
    fs = m.get("feeSchedule") or {}
    if isinstance(fs, str):
        try:
            fs = json.loads(fs)
        except Exception:  # noqa: BLE001
            fs = {}
    return float(fs.get("rate") or 0) if str(m.get("feesEnabled")).lower() == "true" else 0.0


def book(token):
    b = get(f"{CLOB}/book", {"token_id": token})
    if not b:
        return None
    try:
        asks = sorted((float(o["price"]), float(o["size"])) for o in b.get("asks") or [])
        bids = sorted(((float(o["price"]), float(o["size"])) for o in b.get("bids") or []), reverse=True)
    except Exception:  # noqa: BLE001
        return None
    return {"ask": asks[0][0] if asks else None, "ask_sz": asks[0][1] if asks else 0, "bid": bids[0][0] if bids else None}


os.makedirs(D, exist_ok=True)
st = load(STATE, {})
seen = set(st.get("seen", [])); started = st.get("started") or int(time.time())
pos = {}
for f in sorted(glob.glob(f"{D}/pos-*.jsonl")):
    for l in open(f):
        try:
            p = json.loads(l); pos[p["mid"]] = p
        except Exception:  # noqa: BLE001
            pass
for f in sorted(glob.glob(f"{D}/upd-*.jsonl")):
    for l in open(f):
        try:
            u = json.loads(l); pos[u.pop("mid")].update(u)
        except Exception:  # noqa: BLE001
            pass


def scan():
    now = time.time()
    for tag in TAGS:
        evs = get(f"{G}/events", {"tag_slug": tag, "closed": "false", "order": "createdAt", "ascending": "false", "limit": 25}) or []
        stats["events listed"] += len(evs)
        for e in evs:
            for m in e.get("markets") or []:
                mid = str(m.get("id"))
                if mid in seen:
                    continue
                L = ts(m.get("acceptingOrdersTimestamp")) or ts(m.get("createdAt"))
                if L is None:
                    continue
                age = now - L
                if age > 3600:                       # old market: never a candidate, remember it so we do not look again
                    seen.add(mid); continue
                if age < 0:
                    continue                         # not open yet; look again next poll
                seen.add(mid); stats["new listings"] += 1
                c = {"mid": mid, "t": int(now), "age_s": int(age), "tag": tag, "cat": CAT.get(tag, "culture-other"), "ev": e.get("slug"),
                     "q": (m.get("question") or "")[:100], "end": ts(m.get("endDate"))}
                outs = [str(o).lower() for o in jl(m.get("outcomes"))]; tok = jl(m.get("clobTokenIds"))
                why = None
                if outs != ["yes", "no"] or len(tok) != 2:
                    why = "not a yes/no market"
                elif not c["end"] or c["end"] - L < 86400:
                    why = "lives < 24 h"
                elif c["end"] - now < 3600:
                    why = "ends in < 1 h"
                elif m.get("closed") or m.get("acceptingOrders") is False:
                    why = "not accepting orders"
                b = None if why else book(tok[1])
                if not why and (not b or b["ask"] is None):
                    why = "no NO ask"
                if b:
                    c.update(ask=b["ask"], bid=b["bid"], ask_sz=b["ask_sz"])
                if not why and not (0.05 <= b["ask"] <= 0.90):
                    why = "ask outside 0.05-0.90"
                if not why and (b["bid"] is None or b["ask"] - b["bid"] > 0.10 + 1e-9):
                    why = "spread > 10c"
                c["skip"] = why
                append("cand", c); stats["skip: " + (why or "none, bought")] += 1
                if why:
                    continue
                fr = fee_rate(m); a = b["ask"]; sh = round(STAKE / a, 4)
                p = dict(c, a=a, sh=sh, fee_rate=fr, fee=round(fr * a * (1 - a) * sh, 4), tok=tok[1])
                pos[mid] = p; append("pos", p); stats["paper positions"] += 1


def settle():
    ids = sorted(m for m, p in pos.items() if not p.get("res"))
    for i in range(0, len(ids), 40):
        d = get(f"{G}/markets", [("id", x) for x in ids[i:i + 40]] + [("closed", "true"), ("limit", 100)])
        for m in d or []:
            mid = str(m.get("id")); p = pos.get(mid)
            pr = [float(x) for x in jl(m.get("outcomePrices"))] if m.get("outcomePrices") else []
            if not p or p.get("res") or not m.get("closed") or len(pr) != 2:
                continue
            if max(pr) >= 0.99 or (abs(pr[0] - 0.5) < 0.01 and abs(pr[1] - 0.5) < 0.01):
                pay = 1.0 if pr[1] >= 0.99 else 0.5 if pr[1] > 0.4 else 0.0
                u = dict(res=1, pay=pay, pnl=round(p["sh"] * pay - STAKE - p["fee"], 3), pts=round(pay - p["a"] - p["fee_rate"] * p["a"] * (1 - p["a"]), 4),
                         t_res=int(time.time()))
                p.update(u); append("upd", dict(mid=mid, **u))


def boot(rows):
    ev = collections.defaultdict(lambda: [0.0, 0])
    for p in rows:
        ev[p["ev"]][0] += p["pts"]; ev[p["ev"]][1] += 1
    v = list(ev.values()); n = sum(y[1] for y in v)
    if not n:
        return {"n": 0}
    out = {"n": n, "events": len(v), "won": sum(1 for p in rows if p["pay"] >= 1), "avg_ask": round(sum(p["a"] for p in rows) / n, 3),
           "pts": round(100 * sum(y[0] for y in v) / n, 2), "pnl": round(sum(p["pnl"] for p in rows), 2)}
    if len(v) >= 5:
        r = random.Random(58); bs = []
        for _ in range(1000):
            s = [v[int(r.random() * len(v))] for _i in v]
            bs.append(sum(y[0] for y in s) / sum(y[1] for y in s))
        bs.sort(); out["ci"] = [round(100 * bs[25], 1), round(100 * bs[974], 1)]
    return out


def report():
    now = time.time(); P = list(pos.values()); done = [p for p in P if p.get("res")]
    cands = collections.Counter(); ages = []
    for f in glob.glob(f"{D}/cand-*.jsonl"):
        for l in open(f):
            try:
                c = json.loads(l)
            except Exception:  # noqa: BLE001
                continue
            cands[c.get("skip") or "bought"] += 1; ages.append(c.get("age_s", 0))
    ages.sort()
    rep = {"updated": time.strftime("%Y-%m-%d %H:%M", time.gmtime()), "started": time.strftime("%Y-%m-%d %H:%M", time.gmtime(started)),
           "days": round((now - started) / 86400, 2),
           "rule": "new culture listing < 60 min old, lives >= 24 h, NO ask 0.05-0.90, NO spread <= 10c: $10 at the NO ask, fee paid; one per market",
           "decision": "kill if <= +1 pt or event CI low < -1 after 100 markets / 40 events; promote only after 300 / 100 / 3 weeks",
           "positions": len(P), "settled": len(done), "open": len(P) - len(done),
           "open_past_end": sum(1 for p in P if not p.get("res") and p.get("end") and p["end"] < now - 3600),
           "all": boot(done), "mention": boot([p for p in done if p["cat"] == "mention"]),
           "non_mention": boot([p for p in done if p["cat"] != "mention"]),
           "candidates": dict(cands), "candidate_age_min_median": round(ages[len(ages) // 2] / 60, 1) if ages else None,
           "this_run": dict(stats)}
    dump(rep, REP)
    dump({"seen": sorted(seen)[-20000:], "started": started}, STATE)


while True:
    try:
        scan(); stats["polls"] += 1
        if stats["polls"] % 8 == 1:
            settle()
        report()
    except Exception as ex:  # noqa: BLE001
        stats["loop error"] += 1; print("loop error", repr(ex)[:200], flush=True)
    if time.time() - T0 > RUN_MIN * 60:
        break
    time.sleep(POLL)
print(json.dumps(dict(stats)), flush=True)
