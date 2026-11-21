"""N115 quote pull (outside the box, c53, 11-21). Rules fixed before looking.
Idea: in the ~380 top markets, when one side of a tight book jumps away while the other side stays (the ask jumps >= 3c
with the bid unchanged, or the mirror), a maker pulled that side or a taker swept it: either way the side that moved is where
informed flow is arriving (lesson 17: makers lose to the informed and the good ones pull first). FOLLOW: ask pull -> buy YES
at the new ask; bid pull -> buy NO at 1 - new bid. FADE = the other side at the same snapshot. PLACEBO = same markets, random
tight-book snapshots (spread <= 2c), buy YES at the ask (round-trip spread cost baseline).
Source: data/books/<day>/<HHMM>.json.gz (15-min Gamma snapshots: bestBid / bestAsk), read in receive-time (ts) order.
Trigger (snapshot t vs previous snapshot of the same market, gap <= 20 min): prev spread <= 0.02, prev mid 0.10-0.90;
ask pull: ask - prev_ask >= 0.03 and |bid - prev_bid| <= 0.005; bid pull: prev_bid - bid >= 0.03 and |ask - prev_ask| <= 0.005.
One trigger per market per 24 h. Entry at the trigger snapshot's executable price (the snapshot is what we could have seen),
fee 0.07 p(1-p); exit at the held side's bid 4 h and 24 h later (first snapshot at/after), exit fee too; also 'last' = last
seen bid of the held side (resolved markets end near 0/1). Points per share, independent events = event stem x UTC day.
PASS if FOLLOW 24 h >= +2 pts on >= 50 events, both halves > 0, and FOLLOW - PLACEBO >= +2. Else DEAD."""
import gzip, json, glob, re, random, collections, datetime
random.seed(7)
files = sorted(glob.glob('data/books/*/*.json.gz'))
prev = {}
hist = collections.defaultdict(list)     # id -> [(ts, bid, ask)]
slug = {}
trig, plc = [], []
lastfire = {}
for f in files:
    try: d = json.load(gzip.open(f))
    except Exception: continue
    ts = d['ts']
    for m in d['markets']:
        i = m['id']; b, a = m.get('bestBid'), m.get('bestAsk')
        if b is None or a is None or not (0 < b < a < 1): prev.pop(i, None); continue
        hist[i].append((ts, b, a)); slug[i] = m.get('slug', '')
        p = prev.get(i); prev[i] = (ts, b, a)
        if not p or ts - p[0] > 1200: continue
        pb, pa = p[1], p[2]
        if pa - pb > 0.02 or not (0.10 <= (pa + pb) / 2 <= 0.90): continue
        if random.random() < 0.01: plc.append((i, ts, 'yes', a))
        kind = None
        if a - pa >= 0.03 and abs(b - pb) <= 0.005: kind = 'ask'
        elif pb - b >= 0.03 and abs(a - pa) <= 0.005: kind = 'bid'
        if not kind or ts - lastfire.get(i, 0) < 86400: continue
        lastfire[i] = ts
        trig.append((i, ts, kind, b, a))
fee = lambda p: 0.07 * p * (1 - p)
def mark(i, ts, side, h):
    if h is None:
        t, b, a = hist[i][-1]
        return (b if side == 'yes' else 1 - a) if t > ts else None
    for t, b, a in hist[i]:
        if t >= ts + h * 3600 and t <= ts + h * 3600 + 7200:
            return b if side == 'yes' else 1 - a
    return None
def pts(entry, ex):
    return 100 * (ex - fee(ex) - entry - fee(entry))
def stem(i, ts):
    s = re.sub(r'-\d{6,}$', '', slug[i]); s = re.sub(r'-(yes|no|\d+)$', '', s)
    return s.rsplit('-', 1)[0] + '|' + datetime.datetime.utcfromtimestamp(ts).strftime('%m-%d')
def summ(rows):
    out = {}
    for h in (4, 24, None):
        ev = collections.defaultdict(list)
        for i, ts, side, entry in rows:
            ex = mark(i, ts, side, h)
            if ex is None: continue
            ev[stem(i, ts)].append(pts(entry, ex))
        vals = [sum(v) / len(v) for v in ev.values()]
        if not vals: out[str(h)] = {'events': 0}; continue
        bs = sorted(sum(random.choices(vals, k=len(vals))) / len(vals) for _ in range(2000))
        n = len(vals); keys = sorted(ev, key=lambda k: k.split('|')[1])
        half = lambda ks: round(sum(sum(ev[k]) / len(ev[k]) for k in ks) / max(1, len(ks)), 2)
        out[str(h) if h else 'last'] = {'events': n, 'pts': round(sum(vals) / n, 2), 'ci': [round(bs[50], 2), round(bs[1949], 2)],
                                       'halves': [half(keys[:n // 2]), half(keys[n // 2:])]}
    return out
follow = [(i, ts, 'yes', a) if k == 'ask' else (i, ts, 'no', 1 - b) for i, ts, k, b, a in trig]
fade = [(i, ts, 'no', 1 - b) if k == 'ask' else (i, ts, 'yes', a) for i, ts, k, b, a in trig]
rep = {'snapshots': len(files), 'markets': len(hist), 'triggers': len(trig),
       'ask_pulls': sum(t[2] == 'ask' for t in trig), 'bid_pulls': sum(t[2] == 'bid' for t in trig),
       'FOLLOW': summ(follow), 'FADE': summ(fade), 'PLACEBO': summ(plc)}
for k in ('ask', 'bid'):
    rep['FOLLOW_' + k] = summ([r for r, t in zip(follow, trig) if t[2] == k])
f24, p24 = rep['FOLLOW']['24'], rep['PLACEBO']['24']
ok = f24.get('events', 0) >= 50 and f24['pts'] >= 2 and min(f24['halves']) > 0 and f24['pts'] - p24.get('pts', 0) >= 2
rep['verdict'] = 'PASS' if ok else 'DEAD'
json.dump(rep, open('data/research/quote_pull_report.json', 'w'), indent=1)
print(json.dumps(rep, indent=1))
