"""Idea 2 (combos): are combo quotes mispriced vs the product of their legs?
REQUEST-ONLY: asks the RFQ makers for quotes on 2-leg combos and records them. NEVER accepts a quote
(accept_combo_quote is not imported or called anywhere in this file). Runs on the pilot server (Finland).
Each run: list combo-eligible markets, build up to MAX_Q 2-leg combos from legs in DIFFERENT events
(independent: fair price = product of leg prices) plus some same-event pairs (correlated), request a
quote for each, and save quote vs leg mids. Output: data/combos/quotes.jsonl
"""
import json, os, random, sys, time
from datetime import datetime, timezone
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, os.path.join(os.path.dirname(HERE), "live"))
import netprefs  # noqa: E402,F401
OUT = "data/combos"; os.makedirs(OUT, exist_ok=True)
MAX_Q = int(os.environ.get("COMBO_MAX_Q", "12"))
AMOUNT = os.environ.get("COMBO_AMOUNT", "10")


def dump(o):
    try:
        return o.model_dump(mode="json")
    except Exception:  # noqa: BLE001
        return repr(o)[:2000]


def main():
    from polymarket import RelayerApiKey, SecureClient
    rk, ra = os.environ.get("POLYMARKET_RELAYER_API_KEY"), os.environ.get("POLYMARKET_SIGNER_ADDRESS")
    c = SecureClient.create(private_key=os.environ["POLYMARKET_PRIVATE_KEY"], wallet=os.environ.get("POLYMARKET_WALLET_ADDRESS"),
                            api_key=RelayerApiKey(key=rk, address=ra) if rk and ra else None)
    mk = []
    for i, m in enumerate(c.list_combo_markets(page_size=50).iter_items()):
        mk.append(dump(m))
        if i >= 400:
            break
    json.dump(mk[:5], open(f"{OUT}/sample_markets.json", "w"), indent=1, default=str)
    print(len(mk), "combo markets; sample keys", list(mk[0].keys()) if mk and isinstance(mk[0], dict) else mk[:1], flush=True)
    # legs: each market's outcome position ids, its event, and a price if the model carries one
    legs = []
    for m in mk:
        if not isinstance(m, dict):
            continue
        ev = m.get("event_id") or m.get("event_slug") or m.get("game_id") or m.get("event") or m.get("slug")
        outs = m.get("outcomes") or m.get("positions") or m.get("tokens") or []
        if isinstance(outs, dict):  # combo API: {"yes": {label, position_id, price}, "no": {...}}
            outs = [dict(v, outcome=v.get("label") or k) for k, v in outs.items() if isinstance(v, dict)]
        for o in outs:
            if not isinstance(o, dict):
                continue
            pid = o.get("position_id") or o.get("token_id") or o.get("id")
            px = o.get("price") or o.get("mid_price") or o.get("mid")
            if pid:
                legs.append({"pid": str(pid), "ev": str(ev), "px": float(px) if px not in (None, "") else None,
                             "name": str(o.get("outcome") or o.get("name") or "")[:40], "q": str(m.get("question") or m.get("title") or "")[:80]})
    print(len(legs), "legs; sample", legs[:2], flush=True)
    if len(legs) < 2:
        return
    random.seed(int(time.time()) // 3600)
    pairs = []
    for _ in range(MAX_Q * 20):
        a, b = random.sample(legs, 2)
        if a["ev"] != b["ev"] and a["px"] and b["px"] and 0.2 < a["px"] < 0.8 and 0.2 < b["px"] < 0.8:
            pairs.append((a, b, "independent"))
        if len(pairs) >= MAX_Q:
            break
    out = []
    for a, b, kind in pairs:
        rec = {"ts": int(time.time()), "kind": kind, "legs": [a, b], "fair_independent": round(a["px"] * b["px"], 4)}
        try:
            qte = c.request_combo_quote(leg_position_ids=[a["pid"], b["pid"]], direction="BUY", amount=AMOUNT)
            rec["quote"] = dump(qte)
        except Exception as e:  # noqa: BLE001
            rec["error"] = str(e)[:300]
        out.append(rec)
        time.sleep(2)
    with open(f"{OUT}/quotes.jsonl", "a") as fh:
        for r in out:
            fh.write(json.dumps(r, default=str) + "\n")
    print(f"{datetime.now(timezone.utc):%H:%M} {len(out)} quote requests, {sum(1 for r in out if 'quote' in r)} answered", flush=True)
    if out:
        print(json.dumps(out[0], default=str)[:1500], flush=True)


if __name__ == "__main__":
    main()
