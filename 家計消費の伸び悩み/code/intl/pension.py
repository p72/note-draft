import pandas as pd, numpy as np
cf=pd.read_csv('cofog.csv'); p65=pd.read_csv('pop65.csv',index_col=0); p65.columns=p65.columns.astype(int)
P=pd.read_csv('panel.csv'); P['defl']=P.C/P.Cr
defl=P.pivot(index='TIME_PERIOD',columns='area',values='defl')
pen=cf[(cf.TRANSACTION=='D62')&(cf.EXPENDITURE=='GF1002')].pivot(index='TIME_PERIOD',columns='REF_AREA',values='OBS_VALUE')
us=pd.read_csv('us_socsec.csv',index_col=0).iloc[:,0]; pen['USA']=us*1e9/1e6  # to millions (UNIT_MULT 6)
print(cf[(cf.TRANSACTION=='D62')].UNIT_MULT.unique())
N={'JPN':'日本','USA':'米国','GBR':'英国','DEU':'ドイツ','FRA':'フランス','ITA':'イタリア','AUS':'豪州'}
L=np.log; rows=[]
for a in N:
    for b,e in [(2012,2019),(2019,2024),(2022,2024)]:
        pe=lambda y: pen.loc[y,a]/p65.loc[a,y]
        nom=100*L(pe(e)/pe(b)); pr=100*L(defl.loc[e,a]/defl.loc[b,a])
        rows.append(dict(area=a,period=f'{b}-{e}',nominal=nom,prices=pr,real=nom-pr,pop65=100*L(p65.loc[a,e]/p65.loc[a,b]),total_nom=100*L(pen.loc[e,a]/pen.loc[b,a])))
R=pd.DataFrame(rows); R.to_csv('pension_intl.csv',index=False); pd.set_option('display.width',200)
for per,g in R.groupby('period'): print('===',per); print(g.round(1).sort_values('real').to_string(index=False))
# level: old-age benefits per 65+ relative to disposable income per capita (2024)
t14=pd.read_csv('table14.csv'); pop=pd.read_csv('pop.csv').pivot(index='TIME_PERIOD',columns='REF_AREA',values='OBS_VALUE')
yd=t14[(t14.TRANSACTION=='B6G')&(t14.ACCOUNTING_ENTRY=='C')].pivot(index='TIME_PERIOD',columns='REF_AREA',values='OBS_VALUE')
for a in N:
    y=2024 if pd.notna(yd.loc[2024,a]) else 2023
    print(a, y, 'pension per65 / Yd per capita =', round((pen.loc[y,a]/p65.loc[a,y])/(yd.loc[y,a]/pop.loc[y,a]),2))
