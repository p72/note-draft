import pandas as pd, numpy as np
d=pd.read_excel('kakei.xlsx','季調系列 Seasonally adjusted series',header=None)
d=d[d[0].astype(str).str.contains(r'\d- *\d|^\s*\d+- \d',regex=True)&d[1].apply(lambda v:isinstance(v,(int,float)))].copy()
d=d[pd.to_numeric(d[1],errors='coerce').notna()]
idx=pd.period_range('1994Q1',periods=len(d),freq='Q'); d.index=idx
print(d.index[-1], d.iloc[-1,0])
nom_disp=d[8].astype(float); real_disp=d[15].astype(float); defl=nom_disp/real_disp
A=d[1]+d[2]+d[3]; B=A-d[5]
pop=pd.read_csv('pop_jp.csv',index_col=0).iloc[:,0]; pop.index=pd.PeriodIndex(pop.index,freq='M')
pop.loc['2026-06':]=pop.loc['2026-06':]*10
popq=pop.groupby(pop.index.asfreq('Q')).mean()*1000  # persons
out=pd.DataFrame({'A':A.astype(float)/defl*1e9/popq,'B':B.astype(float)/defl*1e9/popq}).dropna()
out.to_csv('jp_pc.csv')
for col in 'AB':
    s=out[col]; w=s.loc['2009Q2':'2019Q4']; i0=s.index.get_loc(w.index[0])
    b,a=np.polyfit(np.arange(len(w)),np.log(w.values),1); t=np.arange(len(s))-i0
    tr=np.exp(a+b*t); g=s/tr-1
    print(col,'trend %.2f%%/yr'%((np.exp(4*b)-1)*100),'latest %.0f'%s.iloc[-1],'gap %.2f'%(g.iloc[-1]*100), 'gap 2019Q4 %.2f'%(g.loc['2019Q4']*100))
print(popq.tail(3))
