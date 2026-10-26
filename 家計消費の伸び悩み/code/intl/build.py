import pandas as pd, numpy as np
A=['JPN','USA','GBR','DEU','FRA','ITA','CAN','KOR','AUS']
t14=pd.read_csv('table14.csv'); t1=pd.read_csv('table1_p3.csv'); pop=pd.read_csv('pop.csv')
def s14(tr,ent):
    d=t14[(t14.TRANSACTION==tr)&(t14.ACCOUNTING_ENTRY==ent)]
    return d.pivot(index='TIME_PERIOD',columns='REF_AREA',values='OBS_VALUE')
B6G=s14('B6G','C'); B6Gd=s14('B6G','D')
print('B6G C vs D max reldiff', ((B6G-B6Gd).abs()/B6G).max().round(4).to_dict())
P3n14=s14('P3','D')
P3n=t1[(t1.SECTOR=='S1M')&(t1.PRICE_BASE=='V')].pivot(index='TIME_PERIOD',columns='REF_AREA',values='OBS_VALUE')
P3r=t1[(t1.SECTOR=='S1M')&(t1.PRICE_BASE=='LR')].pivot(index='TIME_PERIOD',columns='REF_AREA',values='OBS_VALUE')
print('P3 T14 vs T1 reldiff', ((P3n14-P3n).abs()/P3n).max().round(4).to_dict())
# unit multipliers check
print(t14.groupby('REF_AREA').UNIT_MULT.unique().to_dict(), t1.groupby('REF_AREA').UNIT_MULT.unique().to_dict())
POP=pop.pivot(index='TIME_PERIOD',columns='REF_AREA',values='OBS_VALUE')
P=P3n/P3r
D8=s14('D8','C').reindex_like(B6G).fillna(0)
B8G=s14('B8G','C')
sr=100*B8G/(B6G+D8)
panel={}
for c in A:
    d=pd.DataFrame({'Yd':B6G[c],'C':P3n[c],'Cr':P3r[c],'P':P[c],'pop':POP[c],'sr':sr[c]})
    d['APC']=d.C/d.Yd
    panel[c]=d
pd.concat(panel,names=['area']).to_csv('panel.csv')
L=np.log
def dec(c,a,b):
    d=panel[c]
    if b not in d.index or pd.isna(d.loc[b,'Yd']): return None
    cr=100*(L(d.Cr[b]/d['pop'][b])-L(d.Cr[a]/d['pop'][a]))
    yn=100*(L(d.Yd[b]/d['pop'][b])-L(d.Yd[a]/d['pop'][a]))
    p=100*(L(d.P[b])-L(d.P[a])); apc=100*(L(d.APC[b])-L(d.APC[a]))
    return dict(area=c,period=f'{a}-{b}',years=b-a,real_C_pc=cr,nomYd_pc=yn,prices=p,realYd_pc=yn-p,APC=apc,resid=cr-(yn-p+apc),sr_a=d.sr[a],sr_b=d.sr[b])
rows=[]
for a,b in [(2000,2019),(2019,2024),(2021,2024),(2000,2024)]:
    for c in A:
        r=dec(c,a,b)
        if r: rows.append(r)
R=pd.DataFrame(rows); R.to_csv('decomp_intl.csv',index=False)
pd.set_option('display.width',200)
for per,g in R.groupby('period',sort=False):
    g=g.copy(); n=g.years.iloc[0]
    print('=====',per, '(cumulative log%)')
    print(g[['area','real_C_pc','nomYd_pc','prices','realYd_pc','APC','resid','sr_a','sr_b']].round(1).to_string(index=False))
