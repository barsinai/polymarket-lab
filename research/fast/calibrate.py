"""Which resolution rule matches Polymarket's actual Up/Down results? Uses data/fast/windows.jsonl (our 1 s
exchange prices around each window) and fetches each window's result from Gamma."""
import json, sys, time
import requests
S = requests.Session()
W = [json.loads(l) for l in open("data/fast/windows.jsonl")]
res = {}
for w in W:
    try:
        m = S.get("https://gamma-api.polymarket.com/events", params={"slug": w["slug"]}, timeout=10).json()[0]["markets"][0]
        pr = [float(x) for x in json.loads(m["outcomePrices"])]
        if max(pr) >= 0.99:
            res[w["slug"]] = pr[0] > pr[1]
    except Exception:
        pass
    time.sleep(0.1)
rules = {
    "spot_end >= spot_start": lambda w: w["spot_end"] >= w["spot_start"],
    "mean_window >= spot_start": lambda w: w["mean_window"] >= w["spot_start"],
    "mean_last60 >= mean_pre60": lambda w: w["mean_last60"] >= w["mean_pre60"],
    "mean_last60 >= spot_start": lambda w: w["mean_last60"] >= w["spot_start"],
    "mean_last60 >= mean_first60": lambda w: w["mean_last60"] >= w["mean_first60"],
    "mean_window >= mean_pre60": lambda w: w["mean_window"] >= w["mean_pre60"],
}
n = {k: [0, 0] for k in rules}
for w in W:
    if w["slug"] not in res or any(w.get(k) is None for k in ("spot_end", "spot_start", "mean_window", "mean_last60", "mean_pre60", "mean_first60")):
        continue
    for k, f in rules.items():
        n[k][0] += f(w) == res[w["slug"]]; n[k][1] += 1
for k, (a, b) in sorted(n.items(), key=lambda x: -x[1][0]):
    print(f"{k:32} agrees {a}/{b}")
