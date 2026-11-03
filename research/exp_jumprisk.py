"""Jump risk by question type: how often does a market move > 15c within a day while it is
still > 7 days from its end and priced 10-90c? That tail, not the average drift, is what
costs a market maker. Grouped by (a) kind, (b) 'news-event' wording, (c) question template
(top 40 by market-days). Output: results/jumprisk.json"""
import glob, gzip, json, os, re, sys
from collections import defaultdict
from datetime import datetime
import numpy as np
sys.path.insert(0, "research")
exec(open("research/costs.py").read().split("meta = {}")[0].split("def main")[0])  # kind()
tsrc = open("research/template_scan.py").read(); exec(tsrc[tsrc.index("def template"):tsrc.index("ids = set(")])
NEWS = re.compile(r"\b(meet|meeting|speak|talk|call|ceasefire|truce|strike|attack|invade|capture|announce|release|launch|sign|resign|out as|ipo|deal|agreement|sanction|arrest|indict|pardon|fire|fired|visit|summit)\b", re.I)
mk = {}
for f in glob.glob("data/listing/*.gz"):
    for l in gzip.open(f, "rt"):
        m = json.loads(l)
        try:
            end = datetime.fromisoformat(m["endDate"].replace("Z", "+00:00")).timestamp()
        except (KeyError, ValueError, AttributeError, TypeError):
            continue
        q = m.get("question") or ""
        mk[m["id"]] = (end, kind(q.lower()), bool(re.search(r"\b(by|before)\s+(january|february|march|april|may|june|july|august|september|october|november|december)", q, re.I)), bool(NEWS.search(q)), template(q))
acc = defaultdict(lambda: [0, 0, 0.0])  # market-days, jump-days(>15c), sum of |max daily move|
for f in sorted(glob.glob("data/prices/parts/*.jsonl.gz"))[::3]:  # every third file: plenty
    for l in gzip.open(f, "rt"):
        r = json.loads(l); mid = r["market_id"]
        if mid not in mk or not r["tokens"] or len(r["tokens"][0]["history"]) < 48:
            continue
        end, k, dead, news, tpl = mk[mid]
        a = np.array(r["tokens"][0]["history"], float); t, p = a[:, 0], a[:, 1]
        ok = (t < end - 7 * 86400) & (p > 0.10) & (p < 0.90)
        if ok.sum() < 24:
            continue
        t, p = t[ok], p[ok]
        # daily windows: max |p(t+24h) - p(t)|
        days = ((t - t[0]) // 86400).astype(int)
        for d in np.unique(days):
            seg = p[days == d]; nxt = p[days == d + 1]
            if len(seg) < 6 or len(nxt) < 6:
                continue
            mv = abs(nxt.mean() - seg.mean()); big = abs(nxt.max() - seg.min()) > 0.15 or abs(seg.max() - nxt.min()) > 0.15
            for g in (("kind", k), ("deadline", "by <date>" if dead else "other"), ("news words", "news-event" if news else "other"),
                      ("deadline+news", f"{'by-date' if dead else 'nodate'}/{'news' if news else 'nonews'}"), ("template", tpl[:60])):
                x = acc[g]; x[0] += 1; x[1] += int(big); x[2] += mv
out = {}
for (g, v), (n, j, s) in acc.items():
    if n >= 300:
        out[f"{g} | {v}"] = {"market_days": n, "share_days_with_15c_jump": round(j / n, 4), "mean_abs_daily_move_c": round(100 * s / n, 2)}
json.dump(out, open("results/jumprisk.json", "w"), indent=1)
for g in ("kind", "deadline", "news words", "deadline+news"):
    print(f"-- {g}")
    for k_, v in sorted(out.items(), key=lambda x: -x[1]["share_days_with_15c_jump"]):
        if k_.startswith(g + " |"):
            print(f"   {k_[len(g)+3:]:28} days={v['market_days']:7}  >15c jump on {100*v['share_days_with_15c_jump']:5.2f}% of days  mean daily move {v['mean_abs_daily_move_c']:.2f}c")
print("-- safest / riskiest templates (>=2000 market-days)")
tp = [(k_, v) for k_, v in out.items() if k_.startswith("template |") and v["market_days"] >= 2000]
for k_, v in sorted(tp, key=lambda x: x[1]["share_days_with_15c_jump"])[:8] + [("...", None)] + sorted(tp, key=lambda x: -x[1]["share_days_with_15c_jump"])[:8]:
    print("   " + (f"{100*v['share_days_with_15c_jump']:5.2f}%  {k_[11:]}" if v else k_))
