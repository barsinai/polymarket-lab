"""Where does model_v1's apparent profit come from, and were those prices tradeable? (ad-hoc check)"""
import numpy as np, json
from datetime import datetime, timezone
from sklearn.ensemble import HistGradientBoostingRegressor
d=np.load('derived/rows.npz'); X,y,info,feats=d['X'],d['y'],d['info'],list(d['feats'])
mid,ev,t,days,vol=info.T
s=datetime(2026,5,1,tzinfo=timezone.utc).timestamp()
tr=t<s; te=(t>=s+30*86400)&~np.isin(ev,np.unique(ev[tr]))
gb=HistGradientBoostingRegressor(max_iter=300,learning_rate=0.05,max_leaf_nodes=31,min_samples_leaf=500,l2_regularization=1.0,random_state=0).fit(X[tr],y[tr])
pr=gb.predict(X[te]); yt=y[te]; pt=X[te,feats.index('p')]; out=yt+pt
buy=pr>0; price=np.where(buy,pt,1-pt); won=np.where(buy,out,1-out); sel=np.abs(pr)>0.05
cost=0.02; ret=won/np.clip(price+cost,0,0.999)-1
def show(name,mask):
    m=sel&mask
    if m.sum()<30: return
    print(f'{name:28} bets={m.sum():6} price={price[m].mean():.3f} win={won[m].mean():.3f} profit/$ (2c cost)={ret[m].mean():+.3f}  median-return={np.median(ret[m]):+.2f}')
show('all',np.ones_like(sel))
for lo,hi in [(0,.1),(.1,.2),(.2,.4),(.4,.6),(.6,.8),(.8,1)]: show(f'bought side {lo:.1f}-{hi:.1f}',(price>=lo)&(price<hi))
for dd in [1,2,3,5,7,14,30]: show(f'{dd} days before end',days[te]==dd)
for c in ['Sports','Crypto','Politics','Geopolitics','Economy','Culture','Other']: show(c,X[te,feats.index('cat_'+c)]==1)
show('deadline q',X[te,feats.index('deadline')]==1); show('not deadline',X[te,feats.index('deadline')]==0)
for vlo,vhi in [(0,2e4),(2e4,1e5),(1e5,1e6),(1e6,1e13)]: show(f'lifetime vol {vlo:.0e}-{vhi:.0e}',(vol[te]>=vlo)&(vol[te]<vhi))
show('price flat 7d (range<1c)',X[te,feats.index('range_7d')]<0.01)
show('price moved 7d',X[te,feats.index('range_7d')]>=0.01)

# ---- were these prices actually tradeable? use real trades where we have them
import gzip, glob, os
trades={}
for f in glob.glob('data/trades/parts/*.jsonl.gz'):
    for l in gzip.open(f,'rt'):
        r=json.loads(l)
        if r['trades']: trades[int(r['market_id'])]=np.array([x[:5] for x in r['trades']],dtype=float)
mte=mid[te]; tte=t[te]
res=[]
for i in np.where(sel)[0]:
    tr_=trades.get(int(mte[i]))
    if tr_ is None: continue
    oc=0 if buy[i] else 1
    w=tr_[(tr_[:,0]>tte[i])&(tr_[:,0]<=tte[i]+6*3600)&(tr_[:,2]==oc)]
    fill=w[0,3] if len(w) else np.nan
    res.append((price[i],fill,won[i],len(w)))
r=np.array(res); print('\nbets with trade data:',len(r))
has=~np.isnan(r[:,1]); print('share with ANY trade on that side in next 6h:',has.mean().round(3))
print('profit at history price +2c, all:', (r[:,2]/np.clip(r[:,0]+.02,0,.999)-1).mean().round(3))
print('profit at history price +2c, only fillable:', (r[has,2]/np.clip(r[has,0]+.02,0,.999)-1).mean().round(3))
print('profit at the ACTUAL next trade price, fillable:', (r[has,2]/np.clip(r[has,1],0.001,.999)-1).mean().round(3))
print('median (actual fill - history price):', np.median(r[has,1]-r[has,0]).round(3))
for lo,hi in [(0,.2),(.2,.4),(.4,.6),(.6,1)]:
    m=has&(r[:,0]>=lo)&(r[:,0]<hi)
    if m.sum()>20: print(f' side {lo}-{hi}: n={m.sum()} hist->{(r[m,2]/np.clip(r[m,0]+.02,0,.999)-1).mean():+.3f} actual fill->{(r[m,2]/np.clip(r[m,1],0.001,.999)-1).mean():+.3f}')
