import pandas as pd, numpy as np
A=['JPN','USA','GBR','DEU','FRA','ITA','CAN','KOR','AUS']
t14=pd.read_csv('table14.csv'); pop=pd.read_csv('pop.csv').pivot(index='TIME_PERIOD',columns='REF_AREA',values='OBS_VALUE')
def s(tr,ent):
    d=t14[(t14.TRANSACTION==tr)&(t14.ACCOUNTING_ENTRY==ent)].pivot(index='TIME_PERIOD',columns='REF_AREA',values='OBS_VALUE')
    return d.reindex(columns=A)
Yd=s('B6G','C')
comp={'雇用者報酬':s('D1','C'),'営業余剰・混合所得':s('B2A3G','C'),'財産所得（純）':s('D4','C').sub(s('D4','D'),fill_value=0),
      '社会給付':s('D62','C'),'所得税等':-s('D5','D'),'社会負担':-s('D61','D')}
rows=[]
for a,b in [(2000,2024),(2019,2024)]:
    for c in A:
        y0=Yd.loc[a,c]/pop.loc[a,c]; y1=Yd.loc[b,c]/pop.loc[b,c]
        r=dict(area=c,period=f'{a}-{b}',Yd_pc_pct=100*(y1/y0-1))
        tot=0
        for k,v in comp.items():
            x0,x1=v.loc[a,c]/pop.loc[a,c],v.loc[b,c]/pop.loc[b,c]
            val=100*(x1-x0)/y0 if pd.notna(x0) and pd.notna(x1) else np.nan
            r[k]=val; tot+=0 if pd.isna(val) else val
        r['その他']=r['Yd_pc_pct']-tot
        rows.append(r)
R=pd.DataFrame(rows); R.to_csv('income_decomp.csv',index=False)
pd.set_option('display.width',220); print(R.round(1).to_string(index=False))
