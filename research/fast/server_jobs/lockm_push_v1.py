"""Server job: what would a PUSH-driven lock_m earn? (websocket recordings since the K fix, exact price to beat)
Since 11-11 13:00 UTC the bot's K equals the official priceToBeat, so the study may use md['ptb'] without hindsight.
lifetimes.py replays every book change and every Chainlink print: an opportunity opens when z >= 2.5, margin >= 1 bp,
>= 6 s left and the best ask is in [0.50, cap]; the trade is taken at the ask prevailing R seconds after it opened
(R = decision + order latency). One trade per window and side, $20. Per asset and R, for caps 0.97 and 0.92."""
import json, os, subprocess, sys, tempfile, collections
STORE = os.environ.get("STORE", "/home/runner/pilot-data")
out = tempfile.mktemp(suffix=".jsonl")
for cap in ("0.97", "0.92"):
    env = dict(os.environ, K_EST="ptb", MARGIN_MIN="1", REM_MIN="6", ASK_MAX=cap, SINCE="2026-11-11T13", UNTIL="9", R_LO="0", R_HI="60", OUT=out)
    r = subprocess.run([sys.executable, "research/fast/lifetimes.py"], env=env, capture_output=True, text=True, timeout=190)
    print(f"--- cap {cap}: " + " | ".join(l for l in r.stdout.splitlines() if "windows with" in l or "R 0.05" in l or "R 0.25" in l or "R 1.00" in l))
    if r.returncode:
        print(r.stderr[-800:])
L = [json.loads(l) for l in open(out)] if os.path.exists(out) else []
for summ in L:
    print(f"\ncap {summ['ask_max']}: windows {summ['windows']}, episodes {summ['episodes']} (won {summ['episodes_won']})")
    for R, v in summ["window_level"].items():
        by = collections.defaultdict(lambda: [0, 0, 0.0, 0.0])
        for t in v["trades"]:
            a = t["slug"].split("-")[0]; ask = t["ask"]
            if ask is None:
                continue
            pnl = 20 / ask * ((1 if t["won"] else 0) - ask - 0.07 * ask * (1 - ask))
            for k in (a, "ALL"):
                b = by[k]; b[0] += 1; b[1] += t["won"]; b[2] += 20; b[3] += pnl
        print(f"  R {float(R):4.2f} s: " + "  ".join(f"{k} {b[0]}/{b[1]} {b[3] / b[2]:+.0%}" for k, b in sorted(by.items(), key=lambda x: (x[0] != 'ALL', x[0]))))
