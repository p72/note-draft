# 改訂版：共通標本でのシフト推計、係数差のブロックブートストラップ、傾き変化モデル
import pandas as pd, numpy as np, statsmodels.api as sm
d=pd.read_csv('panel2.csv',index_col=0); d.index=pd.PeriodIndex(d.index,freq='Q')
D=['D_tax14','D_tax19','D_covid']; X={'DI':'cons_DI','GAP':'gap_lead2'}
HAC=dict(cov_type='HAC',cov_kwds={'maxlags':4})
def fit(t,x,inter=False):
    t=t.copy(); cols=[x,'imp_l24']+D+['D_shift']
    if inter: t['DX']=t['D_shift']*t[x]; cols=cols+['DX']
    return sm.OLS(t.core_exmob,sm.add_constant(t[cols])).fit(**HAC)
rows=[]; boot={}
rng=np.random.default_rng(0)
for a in ['2004Q1','2013Q1']:
    t=d.loc[a:,['core_exmob','cons_DI','gap_lead2','imp_l24']+D+['D_shift']].dropna()
    ms={k:fit(t,x) for k,x in X.items()}
    for k,m in ms.items():
        b,se=m.params.D_shift,m.bse.D_shift
        rows.append(dict(start=a,x=k,n=int(m.nobs),shift=b,se=se,lo=b-1.96*se,hi=b+1.96*se,p=m.pvalues.D_shift))
    # moving block bootstrap of the difference (block=4)
    n=len(t); L=4; diffs=[]
    for _ in range(2000):
        starts=rng.integers(0,n-L+1,size=int(np.ceil(n/L)))
        idx=np.concatenate([np.arange(s,s+L) for s in starts])[:n]
        tb=t.iloc[idx]
        if tb.D_shift.nunique()<2: continue
        try:
            Dv=[c for c in D if tb[c].nunique()>1]
            bd=[sm.OLS(tb.core_exmob,sm.add_constant(tb[[x,'imp_l24']+Dv+['D_shift']],has_constant='add')).fit().params['D_shift'] for x in X.values()]
            diffs.append(bd[1]-bd[0])
        except Exception: pass
    diffs=np.array(diffs); dpt=ms['GAP'].params.D_shift-ms['DI'].params.D_shift
    boot[a]=(dpt,np.percentile(diffs,2.5),np.percentile(diffs,97.5),len(diffs))
    # slope-change model: shift at post-period mean of x
    for k,x in X.items():
        m=fit(t,x,inter=True); xm=t.loc[t.D_shift==1,x].mean()
        g=np.zeros(len(m.params)); names=list(m.params.index); g[names.index('D_shift')]=1; g[names.index('DX')]=xm
        est=g@m.params.values; se=np.sqrt(g@m.cov_params().values@g)
        rows.append(dict(start=a,x=k+'_slope',n=int(m.nobs),shift=est,se=se,lo=est-1.96*se,hi=est+1.96*se,p=np.nan,theta=m.params.DX,theta_p=m.pvalues.DX,xmean=xm))
r=pd.DataFrame(rows); r.to_csv('shift_est_rev.csv',index=False); print(r.round(3).to_string())
print('difference GAP-DI (point, 95% block-bootstrap CI, reps):'); [print(k,np.round(v,3)) for k,v in boot.items()]
pd.DataFrame([dict(start=k,diff=v[0],lo=v[1],hi=v[2],reps=v[3]) for k,v in boot.items()]).to_csv('shift_diff_rev.csv',index=False)
# range overlap
pre=d.loc['2013Q1':'2019Q4']; post=d.loc['2022Q2':]
for x in X.values(): print(x,'pre',pre[x].min().round(2),pre[x].max().round(2),'post',post[x].min().round(2),post[x].max().round(2),'post share inside pre range',((post[x]>=pre[x].min())&(post[x]<=pre[x].max())).mean().round(2))
