"""Daily snapshot of Polymarket's liquidity-reward programme for every market that has one
(CLOB 'sampling-markets'): daily reward pool, minimum order size, maximum spread from the
midpoint that still earns, fees, tags (incl. holding-reward tags like 'Earn 3.25%').
Saves data/live/rewards/YYYY-MM-DD.jsonl.gz."""
import gzip, json, os, sys, time
from datetime import datetime, timezone
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import collect  # noqa: E402

out, cursor = [], ""
for _ in range(2000):
    d = collect.get(f"{collect.CLOB}/sampling-markets", {"next_cursor": cursor})
    if not d:
        break
    for m in d.get("data") or []:
        out.append({k: m.get(k) for k in ("condition_id", "question", "market_slug", "end_date_iso", "neg_risk",
                                          "minimum_order_size", "minimum_tick_size", "maker_base_fee", "taker_base_fee",
                                          "rewards", "tags", "accepting_orders")}
                   | {"tokens": [{k: t.get(k) for k in ("token_id", "outcome", "price")} for t in m.get("tokens") or []]})
    cursor = d.get("next_cursor") or ""
    if not cursor or cursor == "LTE=":
        break
    time.sleep(0.1)
now = datetime.now(timezone.utc)
os.makedirs("data/live/rewards", exist_ok=True)
collect.write_jsonl_gz(f"data/live/rewards/{now:%Y-%m-%d}.jsonl.gz", out)
pool = sum(sum(r.get("rewards_daily_rate") or 0 for r in (m.get("rewards") or {}).get("rates") or []) for m in out)
print(f"{len(out)} reward markets, total daily reward pool ${pool:,.0f}")
