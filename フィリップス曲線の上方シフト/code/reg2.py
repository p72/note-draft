import pandas as pd, numpy as np, statsmodels.api as sm
d=pd.read_csv('panel2.csv',index_col=0); d.index=pd.PeriodIndex(d.index,freq='Q')
D=['D_tax14','D_tax19','D_covid']
# robustness: shift start
for st in ['2021Q1','2022Q2','2023Q1','2024Q1']:
    d['S']=(d.index>=pd.Period(st)).astype(int)
    for a in ['2004Q1','2013Q1']:
        s=d.loc[a:,['core_exmob','cons_DI','wage_l1','imp_l24','S']+D].dropna()
        m=sm.OLS(s.core_exmob,sm.add_constant(s.drop(columns='core_exmob'))).fit(cov_type='HAC',cov_kwds={'maxlags':4})
        print(st,a,f"shift={m.params['S']:.2f} p={m.pvalues['S']:.2f}")
# rolling: curve position at DI=-15, imp=0, wage=1 ; window 40Q
out=[]
idx=d.dropna(subset=['core_exmob','cons_DI','imp_l24','wage_l1']).index
for i in range(40,len(idx)+1):
    w=idx[i-40:i]; s=d.loc[w]
    cols=['cons_DI','imp_l24']+[c for c in D if s[c].nunique()>1]
    m=sm.OLS(s.core_exmob,sm.add_constant(s[cols])).fit()
    pos=m.params['const']+m.params['cons_DI']*(-15)
    se=np.sqrt(np.array([1,-15])@m.cov_params().loc[['const','cons_DI'],['const','cons_DI']].values@np.array([1,-15]))
    out.append((w[-1],pos,se,m.params['cons_DI']))
r=pd.DataFrame(out,columns=['end','pos','se','slope']).set_index('end'); r.to_csv('rolling.csv')
print(r.iloc[::4].round(3).to_string()); print(r.tail(3).round(3))
