import sys, pandas as pd, numpy as np
sys.path.insert(0,'/root/.claude/skills/synced/42857046-7317-47fd-aa84-fb40ead701d4_f90ecdde-6477-4665-b7b2-90b3176d5903/estat-api')
from scripts.estat_api import read_stats_csv
df=read_stats_csv('kakei_w2.csv'); df['year']=df.time_name.str[:4].astype(int)
cpi=pd.read_csv('cpi_y.csv',index_col=0).iloc[:,0]
grp=['34歳以下','35～39歳','40～44歳','45～49歳','50～54歳','55～59歳','60～64歳','平均']
def v(code,g,y):
    s=df[(df.cat01_code==code)&(df.cat03_name==g)&(df.year==y)].value
    return float(s.iloc[0]) if len(s) else np.nan
rows=[]
for g in grp:
    for y in [2019,2022,2025]:
        Y=v('019',g,y); NC=v('193',g,y); Yd=v('233',g,y); C=v('059',g,y); S=v('234',g,y)
        rows.append(dict(age=g,year=y,実収入=Y,実質実収入=Y/cpi[y]*100,負担率=100*NC/Y,税率=100*v('194',g,y)/Y,社保率=100*v('198',g,y)/Y,
            消費性向=100*C/Yd,消費対実収入=100*C/Y,黒字率=100*S/Yd,預貯金=100*v('237',g,y)/Yd,保険=100*v('238',g,y)/Yd,
            有価証券=100*v('241',g,y)/Yd,住宅ローン返済=100*v('242',g,y)/Yd,他借金=100*v('243',g,y)/Yd,ローン世帯割合=v('013',g,y),
            実質消費=C/cpi[y]*100,実質可処分=Yd/cpi[y]*100,配偶者収入=v('027',g,y)/Y*100))
t=pd.DataFrame(rows); t.to_csv('burden.csv',index=False)
pd.set_option('display.width',250)
print(t.round(1).to_string())
# decomposition 2019->2025 of ln(C/Y)
print('\n分解 2019→2025 (log %pt): Δln(C/Y)=ΔlnAPC+Δln(1-τ)')
for g in grp:
    a=t[(t.age==g)&(t.year==2019)].iloc[0]; b=t[(t.age==g)&(t.year==2025)].iloc[0]
    d=lambda x,y:100*np.log(y/x)
    print(g, 'C/Y',round(d(a.消費対実収入,b.消費対実収入),1),'APC',round(d(a.消費性向,b.消費性向),1),'1-τ',round(d(100-a.負担率,100-b.負担率),1),
          '| 実質: 実収入',round(d(a.実質実収入,b.実質実収入),1),'可処分',round(d(a.実質可処分,b.実質可処分),1),'消費',round(d(a.実質消費,b.実質消費),1),
          '| 黒字率Δ',round(b.黒字率-a.黒字率,1),'内 預貯金',round(b.預貯金-a.預貯金,1),'住宅ローン',round(b.住宅ローン返済-a.住宅ローン返済,1),'有価証券',round(b.有価証券-a.有価証券,1),'保険',round(b.保険-a.保険,1))
