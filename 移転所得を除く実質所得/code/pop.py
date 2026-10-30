import sys; sys.path.insert(0,'/root/.claude/skills/synced/42857046-7317-47fd-aa84-fb40ead701d4_f90ecdde-6477-4665-b7b2-90b3176d5903/estat-api')
from scripts.estat_api import *
import pandas as pd
def s(df):
    d=keep_monthly(df); return d["value"]
a=s(get_stats_df('0004029362',cdCat01='000',cdCat02='001'))
b=s(get_stats_df('0003446819',cdCat02='000',cdCat03='01000',cdCat04='001'))
c=s(get_stats_df('0003443840',cdCat02='000',cdCat03='01000',cdCat04='001'))
d=s(get_stats_df('0003443838',cdCat02='000',cdCat03='01000'))
for n,x in zip('abcd',[a,b,c,d]): print(n,x.index[0],x.index[-1],x.iloc[0],x.iloc[-1])
print('overlap 2015-10',a.get(pd.Period('2015-10','M')),b.get(pd.Period('2015-10','M')))
print('overlap 2020-10',b.get(pd.Period('2020-10','M')),c.get(pd.Period('2020-10','M')))
print('overlap 2026-05',c.get(pd.Period('2026-05','M')),d.get(pd.Period('2026-05','M')))
p=pd.concat([a.loc[:'2015-09'],b.loc[:'2020-09'],c,d.loc[c.index[-1]+1:]])
p.to_csv('pop_jp.csv'); print(p.tail(3))
