import sys, pandas as pd, numpy as np
from statsmodels.tsa.seasonal import STL
sys.path.insert(0,'ESTAT_API_SKILL_DIR')
from scripts.estat_api import read_stats_csv
df=read_stats_csv('kakei_m_age.csv')
df['ym']=df.time_name.str.replace('年','-').str.replace('月','').pipe(pd.to_datetime,format='%Y-%m').dt.to_period('M')
C=df[df.cat01_code=='059'].pivot(index='ym',columns='cat03_name',values='value')
H=df[df.cat01_code=='003'].pivot(index='ym',columns='cat03_name',values='value')
cpi=pd.read_csv('cpi_ex_rent_m.csv'); cpi['ym']=pd.PeriodIndex(cpi.period,freq='M'); cpi=cpi.set_index('ym').value
bands=['34歳以下','35～39歳','40～44歳','45～49歳','50～54歳','55～59歳','60～64歳','65～69歳','70～74歳','75～79歳','80～84歳','85歳以上']
print('missing per band:',C[bands].isna().sum().to_dict())
pp=(C[bands]/H[bands]).div(cpi.reindex(C.index),axis=0)*100   # real per-person, monthly
G={'平均':bands,'39歳以下':bands[:2],'40～49歳':bands[2:4],'50～59歳':bands[4:6],'60～69歳':bands[6:8],'70歳以上':bands[8:]}
m=pd.DataFrame({g:pp[b].mean(axis=1) for g,b in G.items()})
q=m.groupby(m.index.asfreq('Q')).mean()
q=q.loc[:'2026Q3']
out={}
for g in q:
    s=np.log(q[g].loc['2015Q1':'2026Q3'])
    res=STL(s.values,period=4,robust=True).fit()
    sa=np.exp(s.values-res.seasonal)
    out[g]=pd.Series(sa,index=s.index)
SA=pd.DataFrame(out); idx=100*SA/SA.loc[pd.Period('2021Q1','Q')]
idx.loc['2021Q1':].to_csv('age_real_idx.csv')
print(idx.loc['2021Q1':].round(1).to_string())
