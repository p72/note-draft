import sys, pandas as pd, numpy as np
sys.path.insert(0,'<estat-api スキルのディレクトリ>')
from scripts.estat_api import read_stats_csv
d=read_stats_csv('detail.csv')
d['q']=[pd.Period(f"{c[:4]}Q{c[4]}",'Q') for c in d.time_code]
names=d.drop_duplicates('cat02_code').set_index('cat02_code').cat02_name.to_dict()
p=d.pivot_table(index='q',columns=['cat02_code','cat03_code','cat01_code'],values='value')
res={}
for (ind,sz) in sorted({k[:2] for k in p.columns}):
    s=p[ind][sz]; r=s.rolling(4).sum()
    debt=s[[c for c in ['015','016','019','020','021'] if c in s]].sum(axis=1,min_count=1).rolling(4).mean()
    res[(ind,sz)]=pd.DataFrame({'gross':r['084']/r['086']*100,'op':r['084']/r['081']*100,
        'eff':r['084']/debt*100,'net':(r['084']-r['082'])/r['086']*100,
        'icr':(r['081']+r['082'])/r['084'],'debt_ebit':debt/r['081'], 'start':s['084'].first_valid_index()})
out=pd.concat(res,axis=1); out.to_pickle('detail.pkl')
pd.set_option('display.width',250)
rows=[]
for (ind,sz),df in res.items():
    g=df.dropna(subset=['gross'])
    lo=df.loc['2020Q1':,'eff'].idxmin()
    rows.append([names[ind],sz,df.start.iloc[0],round(df.gross.loc['1991Q4'],1) if '1991Q4' in df.index else None,
      round(df.gross.loc['2022Q4'],1),round(df.gross.iloc[-1],1),round(df.op.iloc[-1],1),round(df.net.iloc[-1],1),
      round(df.eff.loc[lo],2),str(lo),round(df.eff.iloc[-1],2),round(df.icr.iloc[-1],1),round(df.debt_ebit.iloc[-1],1)])
t=pd.DataFrame(rows,columns=['name','sz','start','g91','g22','g26','op26','net26','effmin','minq','eff26','icr26','debt/ebit'])
print(t.to_string())
