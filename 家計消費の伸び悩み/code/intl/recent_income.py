import pandas as pd, numpy as np
A=['JPN','USA','GBR','DEU','FRA','ITA','CAN','AUS']
q=pd.read_csv('qsa.csv'); p=pd.read_csv('qpop.csv')
POP=p[p.ADJUSTMENT=='N'].pivot(index='TIME_PERIOD',columns='REF_AREA',values='OBS_VALUE').ffill()
def s(tr,ent): return q[(q.TRANSACTION==tr)&(q.ACCOUNTING_ENTRY==ent)].pivot(index='TIME_PERIOD',columns='REF_AREA',values='OBS_VALUE')
comp={'雇用者報酬':s('D1','C'),'営業余剰・混合所得':s('B2A3G','C'),'財産所得（純）':s('D4','C').sub(s('D4','D'),fill_value=0),
      '社会給付':s('D62','C'),'所得税等':-s('D5','D'),'社会負担':-s('D61','D')}
Yd=s('B6G','C')
k=pd.read_csv('../levels3.csv',index_col=0); k.index=[f"{i[:4]}-Q{i[-1]}" for i in k.index]
Yd['JPN']=k.yd
jp={'雇用者報酬':k.comp,'営業余剰・混合所得':k.op,'財産所得（純）':k.prop,'社会給付':k.ben,'所得税等':-k.tax,'社会負担':-k.soc}
rows=[]
for a in A:
    last=sorted(Yd[a].dropna().index)[-4:]; bq=[f'2022-Q{i}' for i in range(1,5)]
    m=lambda x,qs: x.reindex(qs).mean()
    y0=m(Yd[a],bq)/m(POP[a],bq); y1=m(Yd[a],last)/m(POP[a],last)
    r=dict(area=a,Yd_pc_pct=100*(y1/y0-1)); tot=0
    src=jp if a=='JPN' else {kk:v[a] if a in v else pd.Series(dtype=float) for kk,v in comp.items()}
    for kk,v in src.items():
        x0=m(v,bq)/m(POP[a],bq); x1=m(v,last)/m(POP[a],last)
        val=100*(x1-x0)/y0 if pd.notna(x0) and pd.notna(x1) else np.nan
        r[kk]=val; tot+=0 if pd.isna(val) else val
    r['その他']=r['Yd_pc_pct']-tot; rows.append(r)
R=pd.DataFrame(rows); R.to_csv('income_recent_q.csv',index=False); pd.set_option('display.width',220)
print(R.round(1).sort_values('Yd_pc_pct').to_string(index=False))
