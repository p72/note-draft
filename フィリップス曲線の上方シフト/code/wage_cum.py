# 賃金ラグ（0〜7期）を一括投入した累積効果と、賃金とDIのVIF
import pandas as pd, numpy as np, statsmodels.api as sm
from statsmodels.stats.outliers_influence import variance_inflation_factor as vif
d=pd.read_csv('panel3.csv',index_col=0); d.index=pd.PeriodIndex(d.index,freq='Q')
for k in range(8): d[f'w{k}']=d.wage.shift(k)
W=[f'w{k}' for k in range(8)]
out=[]
for y,D in [('core_exmob',['D_tax14','D_tax19','D_covid','D_shift']),('gsvc',['D_tax14','D_tax19','D_covid2','D_shift'])]:
    for a in ['2004Q1','2013Q1']:
        for di in [True,False]:
            cols=(['cons_DI'] if di else [])+W+(['imp_l24'] if y=='core_exmob' else [])+D
            t=d.loc[a:,[y]+cols].dropna(); m=sm.OLS(t[y],sm.add_constant(t[cols])).fit(cov_type='HAC',cov_kwds={'maxlags':4})
            g=np.array([1.0 if c in W else 0.0 for c in m.params.index]); s=g@m.params.values; se=np.sqrt(g@m.cov_params().values@g)
            out.append(dict(y=y,start=a,DI=di,n=int(m.nobs),cum=s,lo=s-1.96*se,hi=s+1.96*se))
r=pd.DataFrame(out); r.to_csv('wage_cum.csv',index=False); print(r.round(3).to_string())
t=d.loc['2004Q1':,['cons_DI','w4']].dropna(); X=sm.add_constant(t)
print('VIF DI,wage(lag4):',[round(vif(X.values,i),2) for i in (1,2)], 'corr',round(t.corr().iloc[0,1],2))
