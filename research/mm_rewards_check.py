"""Stability check of mm_rewards.py across the last 20 hourly snapshots, excluding live/near games and markets ending within 2 days."""
import glob, gzip, json, sys, numpy as np
from collections import defaultdict
sys.path.insert(0, 'research'); import collect, paper
src = open('research/mm_rewards.py').read()
exec(src[src.index('rw = {}'):src.index('snap = json.load')])
exec(src[src.index('def side_score'):src.index('rows = []')])
per = defaultdict(list)
files = sorted(glob.glob('data/live/2026-11-0*/*.json.gz'))[-20:]
for f in files:
    snap = json.load(gzip.open(f)); now = snap['ts']
    for mid_id, r in snap['markets'].items():
        m = meta.get(mid_id)
        if not m or m.get('conditionId') not in rw: continue
        gst = paper.ts(m.get('gameStartTime') or ''); end = paper.ts(m.get('endDate') or '')
        if (gst and gst - now < 6 * 3600) or (end and end - now < 2 * 86400): continue  # skip live/near games, ending soon
        rate, v, minsize, q = rw[m['conditionId']]
        b0 = snap['books'].get(f'{mid_id}:0')
        if not b0 or not b0[2] or not b0[3]: continue
        mid = (b0[2][0][0] + b0[3][0][0]) / 2
        if not (0.05 < mid < 0.95): continue
        sb = side_score(b0[2], mid, v, minsize, True); sa = side_score(b0[3], mid, v, minsize, False)
        comp = min(sb, sa) if min(sb, sa) > 0 else max(sb, sa) / 3
        qq = max(minsize, 200); ours = ((v - 1) / v) ** 2 * qq
        per[mid_id].append((rate * ours / (ours + comp), qq * 0.98, b0[3][0][0] - b0[2][0][0], q))
print(len(files), 'snapshots;', len(per), 'non-live reward markets')
avg = []
for k, v in per.items():
    if len(v) >= len(files) * 0.8:
        a = np.array([x[:3] for x in v]); avg.append((a[:, 0].mean() / a[0, 1], a[:, 0].mean(), a[0, 1], a[:, 0].std() / max(a[:, 0].mean(), 1e-9), np.median(a[:, 2]), v[0][3]))
y = np.array([x[0] for x in avg])
print(f'markets seen in >=80% of hours: {len(avg)}; reward yield/day median {100*np.median(y):.3f}%, mean {100*y.mean():.2f}%, top decile {100*np.percentile(y,90):.2f}%')
for x in sorted(avg, key=lambda x: -x[0])[:10]:
    print(f'  {100*x[0]:6.2f}%/day ${x[1]:7.2f}/day on ${x[2]:5.0f}  variability {x[3]:.2f}  spread {100*x[4]:.1f}c | {x[5][:60]}')
