import pandas as pd, numpy as np, statsmodels.api as sm
k=pd.read_csv('levels3.csv',index_col=0); k.index=pd.PeriodIndex(k.index,freq='Q')
k['d14']=((k.index>=pd.Period('2014Q1','Q'))&(k.index<=pd.Period('2014Q2','Q'))).astype(int)  # 駆け込み/反動
k['d14']=0; k.loc['2014Q1','d14']=1; k.loc['2014Q2','d14']=-1
k['d19']=0; k.loc['2019Q3','d19']=1; k.loc['2019Q4','d19']=-1
k['d24']=0; k.loc['2024Q2','d24']=1   # 定額減税
k['t']=np.arange(len(k))/4
s=k.loc['1997Q4':].drop(pd.period_range('2020Q1','2021Q4',freq='Q')).dropna(subset=['sr','nw_y','CSI','pi'])
res={}
for nm,X in {'A: 資産/所得＋CSI＋物価':['nw_y','CSI','pi','d14','d19','d24'],
             'B: Aに時間トレンド':['nw_y','CSI','pi','d14','d19','d24','t']}.items():
    m=sm.OLS(s.sr,sm.add_constant(s[X])).fit(cov_type='HAC',cov_kwds={'maxlags':4}); res[nm]=m
    print('====',nm,'N=',int(m.nobs),'R2=',round(m.rsquared,3))
    print(pd.DataFrame({'coef':m.params,'t':m.tvalues}).round(3))
# contribution of variables to change in sr, model B
m=res['B: Aに時間トレンド']
for a,b in [('2021Q4','2025Q3'),('2025Q3','2026Q2'),('2019Q4','2025Q3')]:
    print(f'--- {a}->{b}: actual Δsr={k.sr[b]-k.sr[a]:.2f}')
    for v in ['nw_y','CSI','pi','t']: print('  ',v, round(m.params[v]*(k[v][b]-k[v][a]),2))
k.assign(fitB=m.predict(sm.add_constant(k[['nw_y','CSI','pi','d14','d19','d24','t']],has_constant='add'))).to_csv('levels3.csv')
mA=res['A: 資産/所得＋CSI＋物価']
XA=['nw_y','CSI','pi','d14','d19','d24']
k['fitA']=mA.predict(sm.add_constant(k[XA],has_constant='add'))
for a,b in [('2021Q4','2025Q3'),('2025Q3','2026Q2')]:
    tot=k.sr[b]-k.sr[a]; ex=sum(mA.params[v]*(k[v][b]-k[v][a]) for v in XA)
    print(f'A {a}->{b}: actual {tot:.2f}', {v:round(mA.params[v]*(k[v][b]-k[v][a]),2) for v in ['nw_y','CSI','pi','d24']}, 'resid',round(tot-ex,2))
print(k.loc['2021Q4':,['sr','fitA']].round(2).T.to_string())
# 1-diff robustness
s2=k.loc['1997Q4':].copy(); dd=s2[['sr','nw_y','CSI','pi']].diff(); dd[['d14','d19','d24']]=s2[['d14','d19','d24']]
dd=dd.drop(pd.period_range('2020Q1','2022Q1',freq='Q')).dropna()
m=sm.OLS(dd.sr,sm.add_constant(dd[XA])).fit(cov_type='HAC',cov_kwds={'maxlags':4})
print('diff model R2',round(m.rsquared,3)); print(pd.DataFrame({'coef':m.params,'t':m.tvalues}).round(3))
k.to_csv('levels3.csv')
