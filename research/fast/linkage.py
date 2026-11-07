"""Are Up/Down windows that END at the same second linked? (Read-only study.)

The 15-minute window [st, st+900] and the third 5-minute window [st+600, st+900] both resolve off the SAME
end-of-window Chainlink value, compared with different start references (K15 at st, K5 at st+600).
If K15 < K5: "15m Down & 5m Up" is impossible (final < K15 < K5 would make 5m Down too).
If K15 > K5: "15m Up & 5m Down" is impossible.
So one share of 15m-Up + one share of 5m-Down (when K15 < K5) always pays >= $1, and pays $2 when the final
lands between the two references. If the two asks sum to < $1 that is a riskless profit.

This script: fetches every window's actual result (Gamma), saves data/fast/results.json, re-scores the
resolution rules, and counts linkage violations on the pairs we have.
"""
import json, os, time
import requests

D = "data/fast"
S = requests.Session(); S.headers["User-Agent"] = "polymarket-lab-research/0.1"
W = [json.loads(l) for l in open(f"{D}/windows.jsonl")]
try:
    res = json.load(open(f"{D}/results.json"))
except OSError:
    res = {}
for w in W:
    if w["slug"] in res:
        continue
    try:
        m = S.get("https://gamma-api.polymarket.com/events", params={"slug": w["slug"]}, timeout=10).json()[0]["markets"][0]
        pr = [float(x) for x in json.loads(m["outcomePrices"])]
        if max(pr) >= 0.99:
            res[w["slug"]] = bool(pr[0] > pr[1])   # True = Up
    except Exception:  # noqa: BLE001
        pass
    time.sleep(0.05)
json.dump(res, open(f"{D}/results.json", "w"))
print("windows", len(W), "with result", len(res))

rules = {
    "spot_end >= spot_start": lambda w: w["spot_end"] >= w["spot_start"],
    "mean_window >= spot_start": lambda w: w["mean_window"] >= w["spot_start"],
    "mean_last60 >= mean_pre60": lambda w: w["mean_last60"] >= w["mean_pre60"],
    "mean_last60 >= spot_start": lambda w: w["mean_last60"] >= w["spot_start"],
    "mean_window >= mean_pre60": lambda w: w["mean_window"] >= w["mean_pre60"],
}
keys = ("spot_end", "spot_start", "mean_window", "mean_last60", "mean_pre60")
n = {k: [0, 0] for k in rules}
for w in W:
    if w["slug"] not in res or any(w.get(k) is None for k in keys):
        continue
    for k, f in rules.items():
        n[k][0] += f(w) == res[w["slug"]]; n[k][1] += 1
for k, (a, b) in sorted(n.items(), key=lambda x: -x[1][0]):
    print(f"{k:32} agrees {a}/{b}")

by = {w["slug"]: w for w in W}
pairs = viol = middle = 0; close = 0
for w in W:
    if w["window"] != 900:
        continue
    s5 = f"{w['asset']}-updown-5m-{w['start'] + 600}"
    w5 = by.get(s5)
    if not w5 or w["slug"] not in res or s5 not in res or w.get("mean_pre60") is None or w5.get("mean_pre60") is None:
        continue
    k15, k5 = w["mean_pre60"], w5["mean_pre60"]
    u15, u5 = res[w["slug"]], res[s5]
    pairs += 1
    gap = abs(k15 - k5) / k15
    if gap < 0.0001:
        close += 1
    if k15 < k5 and (not u15 and u5):
        viol += 1; print("VIOLATION", w["slug"], "K15<K5 but 15m Down & 5m Up", k15, k5)
    if k15 > k5 and (u15 and not u5):
        viol += 1; print("VIOLATION", w["slug"], "K15>K5 but 15m Up & 5m Down", k15, k5)
    if (k15 < k5 and u15 and not u5) or (k15 > k5 and not u15 and u5):
        middle += 1
print(f"pairs {pairs} violations {viol} middle(pays $2) {middle} references within 0.01% {close}")

# other markets that end at the same second? hourly "Bitcoin Up or Down" markets
for slug in ("btc-updown-1h-1794038400", "btc-updown-60m-1794038400", "bitcoin-up-or-down-november-7-3am-et"):
    try:
        ev = S.get("https://gamma-api.polymarket.com/events", params={"slug": slug}, timeout=10).json()
        print(slug, "->", ev[0]["markets"][0]["question"] if ev else "none")
        if ev:
            print(ev[0]["markets"][0]["description"][:600])
    except Exception as e:  # noqa: BLE001
        print(slug, "err", str(e)[:80])
try:
    ev = S.get("https://gamma-api.polymarket.com/events", params={"tag_slug": "crypto", "active": "true", "closed": "false", "limit": 200, "order": "startDate", "ascending": "false"}, timeout=15).json()
    seen = set()
    for e in ev:
        sl = e.get("slug", "")
        key = "-".join(x for x in sl.split("-") if not x.isdigit())
        if "up" in sl and "down" in sl and key not in seen:
            seen.add(key); print("pattern", sl, "|", (e.get("title") or "")[:70])
except Exception as e:  # noqa: BLE001
    print("list err", str(e)[:80])
