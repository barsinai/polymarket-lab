"""N111 (outside the box, c51 11-21): attention-spike overreaction. Rules fixed BEFORE looking.
Why the crowd could be wrong: when a market's 24 h volume jumps >= 5x (front page / news wave), the new flow is mostly small takers,
the losing side on Polymarket (lesson 17); if they push the price past the news, fading the 24 h move should pay. Exposed to 2, 3, 5/6,
12 (placebo = same-size moves without a volume spike), 24 (halves), 1 is not a factor (24 h horizon).
Data: data/books/<day>/HH00.json.gz (hourly, receive ts), ~600 top markets/day, 22 days. Excluded: game/sports markets (' vs', 'win on',
'O/U', 'Spread', 'Exact Score', 'draw', esports), crypto 'Up or Down', markets ending < 3 d after the signal.
Signal at snapshot t (first per market id): mid from bestBid/bestAsk with spread <= 5c, the snapshot 23-25 h earlier exists with spread
<= 5c, |mid move| >= 5c. SPIKE arm: volume24hr >= 5x the earlier value and >= $50k. PLACEBO arm: volume24hr < 2x the earlier value.
Trade FADE: move up -> buy NO at 1 - bestBid; move down -> buy YES at bestAsk; exit at the executable bid 24 h later (and 72 h);
fee 0.07 p(1-p) on each leg; points per share. FOLLOW printed (the opposite side, same fills logic).
Unit = event (slug stem); bootstrap 1,000. DECISION: paper tracker only if SPIKE FADE @24h >= +2 pts, CI low > 0, >= 30 events,
FADE - PLACEBO FADE >= +1.5 and both halves (by signal date) > 0. Else DEAD."""
import gzip, json, glob, re, collections, random, datetime as dt
random.seed(111)
files = sorted(f for f in glob.glob('data/books/*/*.json.gz') if f.endswith('00.json.gz'))
SPORT = re.compile(r' vs\.? | vs$|win on|o/u|spread|exact score|draw|both teams|game \d|map \d|bo\d|up or down|kills|total|handicap', re.I)
H = collections.defaultdict(list)  # id -> [(ts, bid, ask, vol24, end, q, slug)]
for f in files:
    try: d = json.load(gzip.open(f))
    except Exception: continue
    ts = d['ts']
    for m in d['markets']:
        q = m.get('question') or ''
        if SPORT.search(q): continue
        try: e = dt.datetime.fromisoformat(m['endDate'].replace('Z', '+00:00')).timestamp()
        except Exception: continue
        b, a, v = m.get('bestBid'), m.get('bestAsk'), m.get('volume24hr')
        if b is None or a is None or v is None: continue
        H[m['id']].append((ts, float(b), float(a), float(v), e, q, m['slug']))
def fee(p): return 0.07 * p * (1 - p)
def stem(s): return re.sub(r'(-\d{2,})+$', '', re.sub(r'-(on|by|before|in|above|below|reach|hit)-.*$', '', s))
def at(h, t, tol=3600):
    c = [r for r in h if abs(r[0] - t) <= tol]
    return min(c, key=lambda r: abs(r[0] - t)) if c else None
R = []
for i, h in H.items():
    h.sort(); done = set()
    for r in h:
        ts, b, a, v, e, q, slug = r
        if a - b > 0.05 or e - ts < 3 * 86400 or b <= 0 or a >= 1: continue
        p = at(h, ts - 86400)
        if not p or p[2] - p[1] > 0.05: continue
        dm = (a + b) / 2 - (p[1] + p[2]) / 2
        if abs(dm) < 0.05: continue
        arm = 'SPIKE' if (p[3] > 0 and v >= 5 * p[3] and v >= 5e4) else 'PLACEBO' if v < 2 * p[3] else None
        if not arm or arm in done: continue
        done.add(arm)
        for hz in (24, 72):
            x = at(h, ts + hz * 3600, 5400)
            if not x: continue
            for way in ('FADE', 'FOLLOW'):
                buy_no = (dm > 0) == (way == 'FADE')
                ent = 1 - b if buy_no else a
                ex = 1 - x[2] if buy_no else x[1]
                R.append(dict(arm=arm, way=way, hz=hz, e=stem(slug), t=ts, dm=dm, q=q[:80],
                              pts=100 * (ex - fee(ex) - ent - fee(ent))))
def stat(rr):
    ev = collections.defaultdict(lambda: [0.0, 0])
    for r in rr: ev[r['e']][0] += r['pts']; ev[r['e']][1] += 1
    E = list(ev.values())
    if len(E) < 3: return dict(n=len(rr), events=len(E))
    tot = lambda S: sum(s for s, _ in S) / sum(n for _, n in S)
    bs = sorted(tot([random.choice(E) for _ in E]) for _ in range(1000))
    return dict(n=len(rr), events=len(E), pts=round(tot(E), 2), ci=[round(bs[25], 2), round(bs[975], 2)])
out = {}
for arm in ('SPIKE', 'PLACEBO'):
    for way in ('FADE', 'FOLLOW'):
        for hz in (24, 72):
            rr = [r for r in R if r['arm'] == arm and r['way'] == way and r['hz'] == hz]
            if not rr: continue
            med = sorted(r['t'] for r in rr)[len(rr) // 2]
            out[f'{arm} {way} {hz}h'] = dict(all=stat(rr), older=stat([r for r in rr if r['t'] < med]),
                                            newer=stat([r for r in rr if r['t'] >= med]))
S, P = out.get('SPIKE FADE 24h', {}), out.get('PLACEBO FADE 24h', {})
ok = bool(S) and S['all'].get('events', 0) >= 30 and S['all']['pts'] >= 2 and S['all']['ci'][0] > 0 and \
     S['all']['pts'] - P['all'].get('pts', 0) >= 1.5 and S['older'].get('pts', -1) > 0 and S['newer'].get('pts', -1) > 0
out['verdict'] = 'PAPER' if ok else 'DEAD'
out['markets_kept'] = len(H); out['snapshots'] = len(files)
out['spike_examples'] = sorted({(r['q'], round(r['dm'], 2)) for r in R if r['arm'] == 'SPIKE' and r['hz'] == 24 and r['way'] == 'FADE'})[:25]
json.dump(out, open('data/research/attention_spike_report.json', 'w'), indent=1)
print(json.dumps(out, indent=1))
