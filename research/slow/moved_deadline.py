"""N109 moved deadlines (c51, 11-21). Rules fixed before looking.
Source: data/books/<day>/<HHMM>.json.gz (15-min snapshots of ~380 top markets with Gamma endDate, bestBid, bestAsk),
read one snapshot per hour in receive (ts) order. An EDIT = same market id, endDate later by >= 1 day than at its previous
appearance, with >= 3 d left on the OLD end at the snapshot that first shows the new end (rule from IDEAS N109); also count
all later-moves and earlier-moves for context.
Trade (receive-time): at the first snapshot showing the new end, buy YES at bestAsk (a 'by date' question gets a longer clock),
fee 0.07 p(1-p) per share; mark at bestBid 24 h later (exit fee too) and at the last seen bid; points per share.
Independent events = distinct event slugs (slug minus trailing date/number) - one per edit cluster.
DEAD by count if < 30 independent qualifying edits (scale: 22 days recorded vs 12 weeks -> needs >= 8 here to reach 30/12 wk)."""
import gzip, json, glob, os, re, datetime, collections
files = sorted(f for f in glob.glob('data/books/*/*.json.gz') if f.endswith('00.json.gz'))
last = {}          # id -> (ts, end, bid, ask, q, slug)
hist = collections.defaultdict(list)   # id -> [(ts,bid,ask)]
edits = []
def p_end(s):
    try: return datetime.datetime.fromisoformat(s.replace('Z', '+00:00')).timestamp()
    except Exception: return None
for f in files:
    try: d = json.load(gzip.open(f))
    except Exception: continue
    ts = d['ts']
    for m in d['markets']:
        e = p_end(m.get('endDate') or '')
        if e is None: continue
        i = m['id']; bid, ask = m.get('bestBid'), m.get('bestAsk')
        hist[i].append((ts, bid, ask))
        if i in last and last[i][1] != e:
            old = last[i][1]
            edits.append(dict(id=i, ts=ts, prev_ts=last[i][0], old=old, new=e, shift_d=(e - old) / 86400,
                              left_d=(old - ts) / 86400, bid0=last[i][2], ask0=last[i][3], bid=bid, ask=ask,
                              q=m['question'], slug=m['slug']))
        last[i] = (ts, e, bid, ask, m['question'], m['slug'])
def fee(p): return 0.07 * p * (1 - p)
def ev(slug): return re.sub(r'(-\d{4,})+$', '', re.sub(r'-(on|by|before|in)-[a-z]+-\d+.*$', '', slug))
later = [x for x in edits if x['shift_d'] >= 1]
earlier = [x for x in edits if x['shift_d'] <= -1]
qual = [x for x in later if x['left_d'] >= 3]
rows = []
for x in qual:
    a = x['ask']
    if not a or a <= 0 or a >= 1: continue
    h = [r for r in hist[x['id']] if r[0] >= x['ts'] + 86400 and r[1]]
    hl = [r for r in hist[x['id']] if r[0] > x['ts'] and r[1]]
    b24 = h[0][1] if h else None; bl = hl[-1][1] if hl else None
    pts24 = None if b24 is None else 100 * (b24 - fee(b24) - a - fee(a))
    ptsl = None if bl is None else 100 * (bl - fee(bl) - a - fee(a))
    rows.append(dict(q=x['q'][:90], ev=ev(x['slug']), shift_d=round(x['shift_d'], 1), left_d=round(x['left_d'], 1),
                     ask0=x['ask0'], ask=a, bid24=b24, pts24=None if pts24 is None else round(pts24, 2),
                     bid_last=bl, pts_last=None if ptsl is None else round(ptsl, 2),
                     when=datetime.datetime.utcfromtimestamp(x['ts']).strftime('%m-%d %H')))
evs = {r['ev'] for r in rows}
def avg(k):
    v = [r[k] for r in rows if r[k] is not None]
    return (round(sum(v) / len(v), 2), len(v)) if v else (None, 0)
out = dict(snapshots=len(files), markets_seen=len(hist), days=len({f.split('/')[2] for f in files}),
           edits_any=len(edits), later_ge1d=len(later), earlier_ge1d=len(earlier), qualifying=len(qual),
           qualifying_events=len(evs), events_later_any=len({ev(x['slug']) for x in later}),
           pts24=avg('pts24'), pts_last=avg('pts_last'), rows=rows,
           later_examples=[(x['q'][:70], round(x['shift_d'], 1), round(x['left_d'], 1)) for x in later[:40]])
json.dump(out, open('data/research/moved_deadline_report.json', 'w'), indent=1)
print(json.dumps({k: v for k, v in out.items() if k not in ('rows', 'later_examples')}, indent=1))
for r in rows: print(r)
print('--- later moves (q, shift d, left d on old end)')
for e in out['later_examples']: print(e)
