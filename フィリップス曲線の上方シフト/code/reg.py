import pandas as pd, numpy as np, statsmodels.api as sm
d=pd.read_csv('panel2.csv',index_col=0); d.index=pd.PeriodIndex(d.index,freq='Q')
D=['D_tax14','D_tax19','D_covid']
specs={
 'A: DIのみ':['cons_DI'],
 'B: DI+賃金+輸入':['cons_DI','wage_l1','imp_l24'],
 'C: B+物価見通し':['cons_DI','wage_l1','imp_l24','exp_l1'],
}
res={}
for samp,(a,b) in {'2004-':('2004Q1','2026Q3'),'2013-':('2013Q1','2026Q3')}.items():
    for name,xs in specs.items():
        if 'exp_l1' in xs and samp=='2004-': continue
        cols=xs+D+['D_shift']
        s=d.loc[a:b,['core_exmob']+cols].dropna()
        X=sm.add_constant(s[cols]); m=sm.OLS(s.core_exmob,X).fit(cov_type='HAC',cov_kwds={'maxlags':4})
        res[(samp,name)]=m
        print(f'== {samp} {name} n={int(m.nobs)} R2={m.rsquared:.2f}')
        for v in ['const']+xs+['D_shift']:
            print(f'   {v:10s} {m.params[v]:7.3f}  (t={m.tvalues[v]:5.2f}, p={m.pvalues[v]:.3f})')
import pickle; pickle.dump({k:(v.params,v.bse,v.pvalues,v.rsquared,int(v.nobs)) for k,v in res.items()},open('res.pkl','wb'))
