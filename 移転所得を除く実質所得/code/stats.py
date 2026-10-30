import pandas as pd, numpy as np
d=pd.read_excel('kakei.xlsx','季調系列 Seasonally adjusted series',header=None)
d=d[pd.to_numeric(d[1],errors='coerce').notna()&d[0].notna()].iloc[:]
d=d[d[0].astype(str).str.contains('-')]
d.index=pd.period_range('1994Q1',periods=len(d),freq='Q'); d=d.iloc[:,1:16].astype(float)
defl=d[8]/d[15]
pop=pd.read_csv('pop_jp.csv',index_col=0).iloc[:,0]; pop.index=pd.PeriodIndex(pop.index,freq='M'); pop.loc['2026-06':]*=10
popq=pop.groupby(pop.index.asfreq('Q')).mean()*1000
pc=lambda s:(s/defl*1e9/popq).dropna()/1e4
comp={'営業余剰':pc(d[1]),'雇用者報酬':pc(d[2]),'財産所得':pc(d[3]),'純社会負担':pc(d[5]),'社会給付':pc(d[6])}
for k,v in comp.items(): print(k, round(v['2019Q4'],1), round(v['2023Q4'],1), round(v['2026Q2'],1))
A=comp['営業余剰']+comp['雇用者報酬']+comp['財産所得']; B=A-comp['純社会負担']
print('A',A['2019Q4'],A['2023Q4'],A['2026Q2']); print('defl yoy',(defl/defl.shift(4)-1).loc['2022Q1':].round(3).tolist())
def gap(s,a,b):
    w=s.loc[a:b]; i0=s.index.get_loc(w.index[0]); bb,aa=np.polyfit(np.arange(len(w)),np.log(w.values),1)
    tr=np.exp(aa+bb*(np.arange(len(s))-i0)); g=s/tr-1; return (np.exp(4*bb)-1)*100, g.iloc[-1]*100, g.loc['2023Q4']*100 if '2023Q4' in g.index else None
for a,b in [('2009Q2','2019Q4'),('2009Q2','2020Q1'),('2012Q4','2019Q4'),('2013Q1','2018Q3')]:
    print(a,b,'A',np.round(gap(A,a,b),2),'B',np.round(gap(B,a,b),2))
# real comp per worker? per capita comp growth
print('popq',popq['2009Q2'],popq['2019Q4'],popq['2026Q2'])
