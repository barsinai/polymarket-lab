"""Reward-pool tracker (idea 1: boost hunting).

Every INTERVAL seconds for RUN_MIN minutes:
  - read Polymarket's sampling-markets (all markets with a liquidity-reward pool)
  - write every CHANGE of (daily rate, min size, max spread) with a timestamp
    -> data/boosts/changes/<day>.jsonl   {ts, cid, q, old:[rate,min,spread], new:[...]}
  - for each market whose rate went UP (a boost) or appeared, follow its order book for WATCH_MIN
    minutes: the depth that would compete with us for the reward at each step
    -> data/boosts/books/<day>.jsonl     {ts, cid, since_boost_s, rate, v, minsize, mid, comp_bid, comp_ask, best_bid, best_ask}
The question it answers: after a pool is boosted, how fast do competing makers arrive, and what share
of the pool would a small two-sided quote earn in the first minutes vs an hour later.
State: data/boosts/state.json (last seen config, markets under watch).
"""
import json, os, sys, time
from datetime import datetime, timezone
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import collect  # noqa: E402

INTERVAL = int(os.environ.get("INTERVAL", "300"))
RUN_MIN = float(os.environ.get("RUN_MIN", "320"))
WATCH_MIN = float(os.environ.get("WATCH_MIN", "180"))
D = "data/boosts"
os.makedirs(f"{D}/changes", exist_ok=True); os.makedirs(f"{D}/books", exist_ok=True)


def load_state():
    try:
        return json.load(open(f"{D}/state.json"))
    except (OSError, ValueError):
        return {"cfg": {}, "watch": {}}


def sampling():
    out, cursor = {}, ""
    for _ in range(500):
        d = collect.get(f"{collect.CLOB}/sampling-markets", {"next_cursor": cursor})
        if not d:
            break
        for m in d.get("data") or []:
            r = m.get("rewards") or {}
            rate = sum(x.get("rewards_daily_rate") or 0 for x in r.get("rates") or [])
            toks = [str(t.get("token_id")) for t in m.get("tokens") or []]
            if m.get("condition_id"):
                out[m["condition_id"]] = {"cfg": [rate, float(r.get("min_size") or 0), float(r.get("max_spread") or 0)],
                                          "q": (m.get("question") or "")[:120], "tok": toks[0] if toks else None,
                                          "end": m.get("end_date_iso")}
        cursor = d.get("next_cursor") or ""
        if not cursor or cursor == "LTE=":
            break
    return out


def comp_depth(levels, mid, v, minsize, is_bid):
    s_ = 0.0
    for p, size in levels:
        s = 100 * ((mid - p) if is_bid else (p - mid))
        if 0 <= s < v and size >= minsize:
            s_ += ((v - s) / v) ** 2 * size
    return s_


def books(tokens):
    from record_books import books_for
    out = {}
    for k in range(0, len(tokens), 100):
        out.update(books_for(tokens[k:k + 100]))
    return out


def main():
    st = load_state()
    end = time.time() + RUN_MIN * 60
    while time.time() < end:
        t0 = time.time(); now = int(t0); day = datetime.fromtimestamp(now, timezone.utc).strftime("%Y-%m-%d")
        cur = sampling()
        if not cur:
            time.sleep(60); continue
        ch = []
        for cid, m in cur.items():
            old = st["cfg"].get(cid)
            if old != m["cfg"]:
                ch.append({"ts": now, "cid": cid, "q": m["q"], "old": old, "new": m["cfg"]})
                if st["cfg"] and m["cfg"][0] > 0 and (old is None or m["cfg"][0] > (old[0] or 0) * 1.2 + 1):
                    st["watch"][cid] = {"since": now, "tok": m["tok"]}
                st["cfg"][cid] = m["cfg"]
        for cid in [c for c in st["cfg"] if c not in cur]:
            ch.append({"ts": now, "cid": cid, "old": st["cfg"][cid], "new": None}); st["cfg"].pop(cid)
        if ch:
            with open(f"{D}/changes/{day}.jsonl", "a") as fh:
                for c in ch:
                    fh.write(json.dumps(c) + "\n")
        st["watch"] = {c: w for c, w in st["watch"].items() if now - w["since"] <= WATCH_MIN * 60 and c in cur}
        toks = [w["tok"] for w in st["watch"].values() if w.get("tok")]
        bk = books(toks) if toks else {}
        rows = []
        for cid, w in st["watch"].items():
            b = bk.get(w["tok"])
            if not b:
                continue
            bids = sorted(((float(x["price"]), float(x["size"])) for x in b.get("bids") or []), reverse=True)
            asks = sorted((float(x["price"]), float(x["size"])) for x in b.get("asks") or [])
            if not bids or not asks:
                continue
            mid = (bids[0][0] + asks[0][0]) / 2
            rate, minsize, v = cur[cid]["cfg"]
            rows.append({"ts": now, "cid": cid, "since_boost_s": now - w["since"], "rate": rate, "v": v, "minsize": minsize,
                         "mid": round(mid, 4), "best_bid": bids[0][0], "best_ask": asks[0][0],
                         "comp_bid": round(comp_depth(bids, mid, v, minsize, True), 1), "comp_ask": round(comp_depth(asks, mid, v, minsize, False), 1)})
        if rows:
            with open(f"{D}/books/{day}.jsonl", "a") as fh:
                for r in rows:
                    fh.write(json.dumps(r) + "\n")
        json.dump(st, open(f"{D}/state.json", "w"))
        print(f"{datetime.now(timezone.utc):%H:%M} markets {len(cur)} changes {len(ch)} watching {len(st['watch'])} books {len(rows)}", flush=True)
        time.sleep(max(5, INTERVAL - (time.time() - t0)))


if __name__ == "__main__":
    main()
