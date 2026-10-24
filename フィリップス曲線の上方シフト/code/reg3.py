import pandas as pd, numpy as np, statsmodels.api as sm
d=pd.read_csv('panel2.csv',index_col=0); d.index=pd.PeriodIndex(d.index,freq='Q')
g=pd.read_csv('gsvc_q.csv',index_col=0); g.index=pd.PeriodIndex(g.index,freq='Q'); d=d.join(g)
q=d.index
d['D_covid2']=((q>=pd.Period('2020Q2'))&(q<=pd.Period('2022Q1'))).astype(int)
D=['D_tax14','D_tax19','D_covid2']
def fit(a,xs,y='gsvc',shift=True):
    cols=xs+D+(['D_shift'] if shift else [])
    t=d.loc[a:,[y]+cols].dropna()
    return sm.OLS(t[y],sm.add_constant(t[cols])).fit(cov_type='HAC',cov_kwds={'maxlags':4}), len(t)
rows=[]
for k in range(0,9):
    d[f'w{k}']=d.wage.shift(k)
    for a in ['2004Q1','2013Q1']:
        for di in [True,False]:
            m,n=fit(a,(['cons_DI'] if di else [])+[f'w{k}'])
            rows.append(dict(start=a,DI=di,lag=k,coef=m.params[f'w{k}'],se=m.bse[f'w{k}'],p=m.pvalues[f'w{k}'],shift=m.params['D_shift'],shp=m.pvalues['D_shift'],r2=m.rsquared,n=n))
r=pd.DataFrame(rows); r.to_csv('lagcoef.csv',index=False)
print(r.round(3).to_string())
# avg lag 4-7
d['w47']=d.wage.shift(4).rolling(4).mean()
for a in ['2004Q1','2013Q1']:
  for di in [True,False]:
    m,n=fit(a,(['cons_DI'] if di else [])+['w47'])
    print(a,'DI' if di else 'noDI','w47',round(m.params['w47'],3),round(m.pvalues['w47'],3),'DI' ,round(m.params.get('cons_DI',np.nan),3), 'shift',round(m.params['D_shift'],2),round(m.pvalues['D_shift'],2),'R2',round(m.rsquared,2))
print('corr gsvc w4 2004-:', d.loc['2004Q1':,['gsvc','w4']].corr().iloc[0,1].round(2), 'corr w4 DI', d.loc['2004Q1':,['cons_DI','w4']].corr().iloc[0,1].round(2))
d.to_csv('panel3.csv')
