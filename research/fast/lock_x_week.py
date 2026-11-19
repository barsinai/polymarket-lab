"""lock_x week read (11-19): total, by entry price, by asset class, by day, bootstrap clustered by end-time."""
import json, collections, random, datetime
rows = [json.loads(l) for l in open('data/fast/trades.jsonl')]
X = [r for r in rows if r['strat'] == 'lock_x' and r['result'] is not None]
def pnl(r): return (r['shares'] if r['result'] == 1 else 0) - r['price'] * r['shares'] - r['fee']
def cost(r): return r['price'] * r['shares'] + r['fee']
def pts(r): return 100 * ((1 if r['result'] == 1 else 0) - r['price'] - r['fee'] / r['shares'])
def summ(name, rs, B=4000):
    if not rs: print(name, 'n 0'); return
    by = collections.defaultdict(list)
    for r in rs: by[r['end']].append(r)
    keys = list(by); random.seed(1)
    ret = sum(map(pnl, rs)) / sum(map(cost, rs)) * 100
    p = sum(map(pts, rs)) / len(rs)
    bs = []
    for _ in range(B):
        s = [r for k in random.choices(keys, k=len(keys)) for r in by[k]]
        bs.append(sum(map(pts, s)) / len(s))
    bs.sort()
    print(f"{name}: {len(rs)} trades / {len(keys)} end-times, won {sum(r['result']==1 for r in rs)}, "
          f"{ret:+.1f}%/$, {p:+.2f} pts/share [{bs[int(.025*B)]:+.2f}, {bs[int(.975*B)]:+.2f}], P&L ${sum(map(pnl, rs)):+.2f}")
summ('lock_x all', X)
summ('price >= 0.80', [r for r in X if r['price'] >= 0.80])
summ('price < 0.80', [r for r in X if r['price'] < 0.80])
summ('btc/eth', [r for r in X if r['asset'] in ('btc', 'eth')])
summ('alts', [r for r in X if r['asset'] not in ('btc', 'eth')])
summ('btc/eth >= 0.80', [r for r in X if r['asset'] in ('btc', 'eth') and r['price'] >= 0.80])
summ('first half (<= 11-14)', [r for r in X if r['ts'] < 1794700800])
summ('second half (>= 11-15)', [r for r in X if r['ts'] >= 1794700800])
d = collections.defaultdict(list)
for r in X: d[datetime.datetime.fromtimestamp(r['ts'], datetime.timezone.utc).strftime('%m-%d')].append(r)
print('by day:', {k: round(sum(map(pnl, v)), 2) for k, v in sorted(d.items())})
