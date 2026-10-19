import sys, pandas as pd, numpy as np
sys.path.insert(0,'<estat-api スキルのディレクトリ>')
from scripts.estat_api import read_stats_csv
def piv(f):
    d=read_stats_csv(f)
    d['q']=[pd.Period(f"{c[:4]}Q{c[4]}",'Q') for c in d.time_code]
    return d.pivot_table(index='q',columns=['cat03_code','cat01_code'],values='value')
p=pd.concat([piv('mof.csv'),piv('debt.csv')],axis=1)
out={}
for sz in ['26','25']:
    s=p[sz]; r=s.rolling(4).sum()
    debt=s[['015','016','019','020','021']].sum(axis=1)
    out[f'gross_{sz}']=r['084']/r['086']*100
    out[f'net_{sz}']=(r['084']-r['082'])/r['086']*100
    out[f'op_{sz}']=r['084']/r['081']*100
    out[f'eff_{sz}']=r['084']/debt.rolling(4).mean()*100
o=pd.DataFrame(out)
c=pd.read_csv('call.csv',index_col=0,parse_dates=True)
call=c.STRACLUCON.fillna(c.STRACLCOON)
call.index=call.index.to_period('Q'); callq=call.groupby(level=0).mean()
o['call']=callq
o.to_csv('ratio.csv')
pd.set_option('display.width',200)
print(o.loc[['1970Q4','1974Q4','1980Q4','1985Q4','1990Q4','1991Q4','1995Q4','2000Q4','2008Q4','2015Q4','2019Q4','2022Q4','2023Q4','2024Q4','2025Q4','2026Q1','2026Q2']].round(2))
print(o[['gross_26','net_26']].idxmax(), o[['gross_26','net_26']].max())
print(o.gross_26.idxmin(), o.gross_26.min())
