import sys; sys.path.insert(0,'/mnt/skills/plugins/estat-api')
import pandas as pd, numpy as np
from scripts.estat_api import read_stats_csv, keep_monthly
df=read_stats_csv('cpi_idx.csv')
p={}
for c in ['0001','0168','7430']:
    s=keep_monthly(df[df.cat01_code==c])['value']; p[c]=s
C=p['0168']; M=p['7430']
yC=C/C.shift(12)-1; yM=M/M.shift(12)-1
W_C, W_M = 6609, 181
s=W_M/W_C
r=(M.shift(12)/C.shift(12))*s          # effective share of mobile in core at t-12
yEx=(yC - r*yM)/(1-r)
yEx=yEx.fillna(yC)  # before mobile series (2000) -> plain core
m=pd.DataFrame({'core':yC*100,'core_exmob':yEx*100})
q=m.groupby(m.index.asfreq('Q')).mean()
q=q[q.index.map(lambda x: True)]
# tankan
t=pd.read_csv('tankan.csv',index_col=0,parse_dates=True); t.index=t.index.to_period('Q')
w={'小売':2152,'対個人サービス':2704,'宿泊飲食':626}
t['cons_DI']=sum(t[k]*v for k,v in w.items())/sum(w.values())
# gap
g=pd.read_excel('gap.xlsx',sheet_name='data1',header=None).iloc[5:,[0,1]]
g.columns=['q','gap']; g=g.dropna()
g.index=pd.PeriodIndex([x.split('.')[0]+'Q'+x.split('.')[1][0] for x in g.q.astype(str)],freq='Q')
g=g['gap'].astype(float)
out=q.join(t['cons_DI']).join(pd.Series(g.values,index=g.index+2,name='gap_lead2'))
out=out[(out.index>=pd.Period('2004Q1'))]
out.to_csv('panel.csv')
print(out.loc['2012Q4':].round(2).to_string())
