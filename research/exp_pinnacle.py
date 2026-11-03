"""Polymarket soccer prices vs Pinnacle closing odds (football-data.co.uk).

For each league game (8 leagues, since Aug 2025): Polymarket's Yes price for home win / draw /
away win at H hours before kickoff, versus the de-vigged Pinnacle closing probability
(PSCH/PSCD/PSCA, margin removed proportionally). Pinnacle is the sharpest public book, so
  edge = pinnacle_prob - polymarket_price
is a candidate signal. Tests (all on resolved games, out of sample by construction - no fitting):
  1. Is Polymarket calibrated relative to Pinnacle?  (regress outcome on both)
  2. Taker strategy: buy the outcome whose Polymarket price is below Pinnacle by > threshold,
     pay the taker fee (sports: 5% * p * (1-p) per share), settle at resolution. Profit per $?
  3. Same for selling (buying the complementary side).
Output: results/exp_pinnacle.json
"""
import csv, difflib, glob, gzip, json, os, re, sys
from datetime import datetime, timezone
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import collect  # noqa: E402

HOURS = [1, 6, 24]
FEE = 0.05
ALIAS = {"man city": "manchester city", "man united": "manchester united", "spurs": "tottenham hotspur", "nott'm forest": "nottingham forest",
         "wolves": "wolverhampton wanderers", "sheffield united": "sheffield utd", "newcastle": "newcastle united", "west ham": "west ham united",
         "brighton": "brighton & hove albion", "leicester": "leicester city", "norwich": "norwich city", "ipswich": "ipswich town",
         "ath madrid": "atletico madrid", "ath bilbao": "athletic club", "betis": "real betis", "sociedad": "real sociedad", "celta": "celta vigo",
         "espanol": "espanyol", "vallecano": "rayo vallecano", "alaves": "deportivo alaves", "psg": "paris saint-germain", "paris sg": "paris saint-germain",
         "inter": "inter milan", "milan": "ac milan", "roma": "as roma", "lazio": "ss lazio", "bayern munich": "bayern munchen", "dortmund": "borussia dortmund",
         "m'gladbach": "borussia monchengladbach", "leverkusen": "bayer leverkusen", "ein frankfurt": "eintracht frankfurt", "rb leipzig": "rb leipzig",
         "fc koln": "1. fc koln", "mainz": "mainz 05", "stuttgart": "vfb stuttgart", "wolfsburg": "vfl wolfsburg", "hoffenheim": "tsg hoffenheim",
         "psv eindhoven": "psv", "sp lisbon": "sporting cp", "porto": "fc porto", "benfica": "sport lisboa e benfica"}


def norm(s):
    s = s.lower().replace("ü", "u").replace("ö", "o").replace("é", "e").replace("ó", "o").replace("í", "i").replace("á", "a").replace("ñ", "n")
    s = ALIAS.get(s.strip(), s)
    s = re.sub(r"\b(fc|cf|sc|ac|as|ss|afc|ss|club|de|1\.|cd|ud|sd|rcd|real|deportivo|sv|vfb|vfl|tsg|bv|fsv|sl|sporting|clube|the)\b", " ", s)
    return re.sub(r"[^a-z0-9 ]", " ", s).split()


def sim(a, b):
    ta, tb = set(norm(a)), set(norm(b))
    if not ta or not tb:
        return 0.0
    j = len(ta & tb) / len(ta | tb)
    return max(j, difflib.SequenceMatcher(None, " ".join(norm(a)), " ".join(norm(b))).ratio() * 0.9)


# --- Pinnacle closing odds
games = {}  # (div, date) -> list of dict
for f in glob.glob("data/external/football/*.csv"):
    div = os.path.basename(f).split("_")[1][:-4]
    for r in csv.DictReader(open(f, encoding="latin-1")):
        try:
            d = datetime.strptime(r["Date"], "%d/%m/%Y").date().isoformat()
            h, dr, a = float(r.get("PSCH") or r["PSH"]), float(r.get("PSCD") or r["PSD"]), float(r.get("PSCA") or r["PSA"])
        except (KeyError, ValueError):
            continue
        inv = 1 / h + 1 / dr + 1 / a
        games.setdefault((div, d), []).append({"home": r["HomeTeam"], "away": r["AwayTeam"], "ftr": r.get("FTR"),
                                               "p": {"home": 1 / h / inv, "draw": 1 / dr / inv, "away": 1 / a / inv}, "margin": inv - 1})
print(f"{sum(len(v) for v in games.values())} games with Pinnacle closing odds", flush=True)

# --- Polymarket markets + histories
mk = {m["id"]: m for m in collect.read_jsonl_gz("data/external/soccer/markets.jsonl.gz")}
hist = {}
for f in glob.glob("data/external/soccer/prices/*.jsonl.gz"):
    for r in collect.read_jsonl_gz(f):
        hist[r["id"]] = r["history"]
print(f"{len(mk)} markets, {len(hist)} with history", flush=True)
# group by game slug prefix: "epl-wol-mac-2025-08-16"
bygame = {}
for m in mk.values():
    parts = m["slug"].split("-")
    key = "-".join(parts[:6]); tail = parts[-1]
    home, away = parts[1], parts[2]
    role = "draw" if tail == "draw" else ("home" if tail == home else ("away" if tail == away else None))
    if role:
        bygame.setdefault(key, {})[role] = m
rows = []
matched = unmatched = 0
for key, ms in bygame.items():
    m0 = next(iter(ms.values()))
    gst = collect.parse_ts(m0["gameStartTime"])
    date = datetime.fromtimestamp(gst, timezone.utc).date().isoformat()
    cands = games.get((m0["div"], date), [])
    # team names from questions: "Will Arsenal FC win on ...?" / "Will X vs. Y end in a draw?"
    qh = ms.get("home", {}).get("question", ""); qa = ms.get("away", {}).get("question", ""); qd = ms.get("draw", {}).get("question", "")
    th = re.sub(r"^Will (.*) win on .*$", r"\1", qh) if qh else None
    ta = re.sub(r"^Will (.*) win on .*$", r"\1", qa) if qa else None
    if qd and (not th or not ta):
        mm = re.match(r"^Will (.*) vs\.? (.*) end in a draw\?$", qd)
        if mm:
            th, ta = th or mm.group(1), ta or mm.group(2)
    if not cands or not th or not ta:
        unmatched += 1
        continue
    best = max(cands, key=lambda g: sim(th, g["home"]) + sim(ta, g["away"]))
    if sim(th, best["home"]) + sim(ta, best["away"]) < 1.0:
        unmatched += 1
        continue
    matched += 1
    for role, m in ms.items():
        h = hist.get(m["id"])
        if not h:
            continue
        try:
            pr = [float(x) for x in json.loads(m["outcomePrices"] or "[]")]
        except ValueError:
            continue
        if len(pr) != 2 or max(pr) < 0.99:
            continue
        y = 1.0 if pr[0] > pr[1] else 0.0
        hh = np.array(h)
        for H in HOURS:
            t = gst - H * 3600
            j = np.searchsorted(hh[:, 0], t, side="right") - 1
            if j < 0 or t - hh[j, 0] > 6 * 3600:
                continue
            rows.append((H, best["p"][role], float(hh[j, 1]), y, m["volume"], role))
print(f"games matched {matched}, unmatched {unmatched}; {len(rows)} (market, horizon) rows", flush=True)
out = {"games_matched": matched, "games_unmatched": unmatched, "by_horizon": {}}
for H in HOURS:
    R = np.array([r[:5] for r in rows if r[0] == H], dtype=float)
    if len(R) < 50:
        continue
    pin, pm, y = R[:, 1], R[:, 2], R[:, 3]
    res = {"n": len(R), "mean_abs_diff_cents": round(float(np.abs(pin - pm).mean() * 100), 2),
           "brier_polymarket": round(float(((pm - y) ** 2).mean()), 4), "brier_pinnacle": round(float(((pin - y) ** 2).mean()), 4),
           "corr_diff_vs_error": round(float(np.corrcoef(pin - pm, y - pm)[0, 1]), 4)}
    # taker test: buy Yes when pinnacle > polymarket + thr (pay fee on the share), else buy No when pinnacle < polymarket - thr
    for thr in (0.02, 0.04, 0.06):
        pnl, n = [], 0
        for a, b, yy in zip(pin, pm, y):
            if a - b > thr:   # buy Yes at the price (+1c slippage), fee on p(1-p)
                px = min(b + 0.01, 0.99); pnl.append((yy - px) - FEE * px * (1 - px)); n += 1
            elif b - a > thr:  # buy No at 1 - price + 1c
                px = min(1 - b + 0.01, 0.99); pnl.append(((1 - yy) - px) - FEE * px * (1 - px)); n += 1
        if n:
            pnl = np.array(pnl)
            res[f"take_thr{int(thr*100)}c"] = {"bets": n, "profit_per_share_cents": round(float(pnl.mean() * 100), 2),
                                             "stderr_cents": round(float(pnl.std() / np.sqrt(n) * 100), 2)}
    out["by_horizon"][f"{H}h"] = res
    print(H, "h", json.dumps(res))
json.dump(out, open("results/exp_pinnacle.json", "w"), indent=1)
