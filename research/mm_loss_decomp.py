import json,glob,gzip,os,re,sys,bisect,collections
sys.path.insert(0,'research'); import collect
STATE=sys.argv[1] if len(sys.argv)>1 else "data/replay_mm/state_2c_sizevol"
meta={}
for f in sorted(glob.glob("data/live/meta/*.jsonl.gz")):
    for m in collect.read_jsonl_gz(f): meta[m["id"]]=m
cid2q={m["conditionId"]:m.get("question","") for m in meta.values() if m.get("conditionId")}
rw={}
for f in sorted(glob.glob("data/live/rewards/*.jsonl.gz")):
    for m in collect.read_jsonl_gz(f):
        rw[m["condition_id"]]=[t for t in (collect.as_list(m.get("tags")) or []) if isinstance(t,str)]
mids={}
for f in sorted(glob.glob("data/live/20*/*.json.gz")):
    d=json.load(gzip.open(f))
    if "market_columns" not in d: continue
    for mid,r in d["markets"].items():
        m=meta.get(mid); b=d["books"].get(f"{mid}:0")
        if m and m.get("conditionId") in rw and b and b[2] and b[3]:
            mids.setdefault(m["conditionId"],[]).append((d["ts"],(b[2][0][0]+b[3][0][0])/2))
T={c:[x[0] for x in v] for c,v in mids.items()}
def mid_at(cid,t):
    v=mids.get(cid)
    if not v: return None
    i=bisect.bisect_right(T[cid],t)-1
    return v[i][1] if i>=0 else None
fills=[]
for f in sorted(glob.glob(f"{STATE}/2026-*/*.jsonl")):
    for line in open(f):
        if not line.strip(): continue
        d=json.loads(line)
        for cid,side,px,sz in d["fills"]:
            m0=mid_at(cid,d["ts"]-3600); m1=mid_at(cid,d["ts"]); m24=mid_at(cid,d["ts"]+23*3600)
            if m1 is None: continue
            sgn=1 if side=="buy" else -1
            fills.append(dict(cid=cid,ts=d["ts"],side=side,px=px,sz=sz,pnl1=sgn*(m1-px)*sz, pnl24=sgn*(m24-px)*sz if m24 else None,
                              usd=px*sz, move=abs(m1-m0) if m0 else None))
print(len(fills),"fills")
print("pnl marked at next snapshot: %.0f"%sum(f["pnl1"] for f in fills))
p24=[f for f in fills if f["pnl24"] is not None]; print("pnl marked 24h later: %.0f over %d fills"%(sum(f["pnl24"] for f in p24),len(p24)))
bym=collections.defaultdict(float)
for f in fills: bym[f["cid"]]+=f["pnl1"]
for c,v in sorted(bym.items(), key=lambda x:x[1])[:10]: print("%8.0f  %s"%(v,cid2q.get(c,"")[:75]))
print("...best:")
for c,v in sorted(bym.items(), key=lambda x:-x[1])[:5]: print("%8.0f  %s"%(v,cid2q.get(c,"")[:75]))
print("markets with fills:",len(bym),"losers:",sum(1 for v in bym.values() if v<0))
for lo,hi in [(0,50),(50,100),(100,200),(200,1e9)]:
    s=[f for f in fills if lo<=f["usd"]<hi]
    if s: print(f"fill usd {lo}-{hi}: n={len(s)} pnl1={sum(f['pnl1'] for f in s):.0f} per$={sum(f['pnl1'] for f in s)/sum(f['usd'] for f in s):+.3f}")
for lo,hi in [(0,0.01),(0.01,0.02),(0.02,0.05),(0.05,1)]:
    s=[f for f in fills if f["move"] is not None and lo<=f["move"]<hi]
    if s: print(f"hour move {lo}-{hi}: n={len(s)} pnl1={sum(f['pnl1'] for f in s):.0f}")
cat=collections.defaultdict(lambda:[0,0.0,0.0])
for f in fills:
    tags=rw.get(f["cid"],[]); c=next((t for t in ("Politics","Sports","Crypto","Geopolitics","Business","Finance","Economy","Tech","Science","Pop Culture") if t in tags),"Other")
    cat[c][0]+=1; cat[c][1]+=f["pnl1"]; cat[c][2]+=f["usd"]
for c,(n,p,u) in sorted(cat.items(), key=lambda x:x[1][1]): print(f"{c:12} n={n:4d} pnl1={p:7.0f} per$={p/u:+.3f}")
# by hour of day
byh=collections.defaultdict(float)
for f in fills: byh[(f["ts"]//3600)%24]+=f["pnl1"]
print("by UTC hour:", {h:round(v) for h,v in sorted(byh.items())})
