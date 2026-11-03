"""Compare the live paper market makers over a time window, from the hourly report.json commits.
Usage: python research/mm_live_compare.py --since 2026-11-03T14:50 [--until ...]
Prints per variant: hours, rewards/h, rebates/h, trading/h (cash + inventory at mid), net/h, fills, capital.
"""
import argparse, json, subprocess
from datetime import datetime, timezone

ap = argparse.ArgumentParser()
ap.add_argument("--since", required=True); ap.add_argument("--until", default="2099-01-01T00:00")
a = ap.parse_args()
t0 = datetime.fromisoformat(a.since).replace(tzinfo=timezone.utc); t1 = datetime.fromisoformat(a.until).replace(tzinfo=timezone.utc)
VARS = {"v1": "data/paper_mm/report.json", "1c": "data/paper_mm2/report.json", "2c": "data/paper_mm2_2c/report.json", "2cv": "data/paper_mm2_2cv/report.json",
        "2cl": "data/paper_mm2_2cl/report.json", "wide": "data/paper_mm2_wide/report.json", "tight": "data/paper_mm2_tight/report.json", "park": "data/paper_mm2_park/report.json"}


def reports(path):
    out = []
    shas = subprocess.run(["git", "log", "--format=%H", "--", path], capture_output=True, text=True).stdout.split()
    for s in shas:
        try:
            r = json.loads(subprocess.run(["git", "show", f"{s}:{path}"], capture_output=True, text=True).stdout)
        except ValueError:
            continue
        ts = datetime.fromisoformat(r["updated"])
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        out.append((ts, r))
    return sorted(out)


print(f"{'variant':7} {'hours':>5} {'rew/h':>6} {'reb/h':>6} {'trade/h':>8} {'net/h':>6} {'fills':>5} {'capital':>8}  (window {a.since} .. {a.until[:16]})")
for v, p in VARS.items():
    rs = [x for x in reports(p) if t0 <= x[0] <= t1]
    if len(rs) < 2:
        continue
    (ta, A), (tb, B) = rs[0], rs[-1]
    h = (tb - ta).total_seconds() / 3600
    if h < 0.5:
        continue
    rew = B.get("rewards_earned", 0) - A.get("rewards_earned", 0)
    reb = B.get("maker_rebates", 0) - A.get("maker_rebates", 0)
    tr = (B.get("trading_cash", 0) + B.get("inventory_value_at_mid", 0)) - (A.get("trading_cash", 0) + A.get("inventory_value_at_mid", 0))
    fills = B.get("fills", 0) - A.get("fills", 0)
    cap = B.get("capital_in_use", B.get("capital_in_quotes_now", 0)) + B.get("capital_in_inventory", 0)
    print(f"{v:7} {h:5.1f} {rew/h:6.2f} {reb/h:6.2f} {tr/h:8.2f} {(rew+reb+tr)/h:6.2f} {fills:5d} {cap:8.0f}")
