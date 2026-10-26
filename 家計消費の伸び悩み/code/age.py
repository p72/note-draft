import sys, pandas as pd, numpy as np
sys.path.insert(0,'/root/.claude/skills/synced/42857046-7317-47fd-aa84-fb40ead701d4_f90ecdde-6477-4665-b7b2-90b3176d5903/estat-api')
from scripts.estat_api import read_stats_csv
df=read_stats_csv('kakei_age.csv'); df['year']=df.time_name.str[:4].astype(int)
G=['34歳以下','35～39歳','40～44歳','45～49歳','50～54歳','55～59歳','60～64歳','65～69歳']
SUB70=['70～74歳','75～79歳','80～84歳','85歳以上']
def panel(hh, item):
    w=df[(df.cat02_code==hh)&(df.cat01_code=='001')].pivot(index='year',columns='cat03_name',values='value')
    x=df[(df.cat02_code==hh)&(df.cat01_code==item)].pivot(index='year',columns='cat03_name',values='value')
    Y=['24歳以下','25～29歳','30～34歳']
    wy=w[Y].sum(axis=1,min_count=3); xy=(x[Y]*w[Y]).sum(axis=1,min_count=3)/wy
    w['34歳以下']=w['34歳以下'].where(w['34歳以下'].notna(),wy); x['34歳以下']=x['34歳以下'].where(x['34歳以下'].notna(),xy)
    W=w[G].copy(); X=x[G].copy()
    has70='70歳以上' in w and True
    w70=w.get('70歳以上'); x70=x.get('70歳以上')
    ws=w[SUB70].sum(axis=1,min_count=4) if all(c in w for c in SUB70) else None
    xs=(x[SUB70]*w[SUB70]).sum(axis=1,min_count=4)/ws if ws is not None else None
    W['70歳以上']=w70.where(w70.notna(), ws) if w70 is not None else ws
    X['70歳以上']=x70.where(x70.notna(), xs) if x70 is not None else xs
    return W, X, x['平均']
W,C,Cavg=panel('03','059')
ok=W.notna().all(axis=1)&C.notna().all(axis=1)
W,C,Cavg=W[ok],C[ok],Cavg[ok]
print('years',W.index.min(),W.index.max(),'share sum check',(W.sum(axis=1)-10000).abs().max())
Wn=W.div(W.sum(axis=1),axis=0)
rec=(Wn*C).sum(axis=1); print('recon vs avg max % diff',((rec/Cavg-1)*100).abs().max().round(3))
def ss(a,b):
    dw=Wn.loc[b]-Wn.loc[a]; dc=C.loc[b]-C.loc[a]; wb=(Wn.loc[a]+Wn.loc[b])/2; cb=(C.loc[a]+C.loc[b])/2
    base=rec[a]; comp=(dw*cb).sum()/base*100; within=(wb*dc).sum()/base*100
    return round((rec[b]/rec[a]-1)*100,2), round(comp,2), round(within,2)
out=[]
for a,b in [(2000,2025),(2010,2025),(2019,2025),(2022,2025)]:
    t,cp,wi=ss(a,b); out.append([f'{a}→{b}',t,cp,wi]); 
o=pd.DataFrame(out,columns=['期間','平均消費支出変化%','年齢構成要因','年齢内要因']); print(o.to_string()); o.to_csv('shiftshare.csv',index=False)
# annualized composition drag per year
for a,b in [(2000,2025),(2019,2025)]:
    print(a,b,'composition per year',round(ss(a,b)[1]/(b-a),2))
# share 65+ ,70+
print(Wn[['65～69歳','70歳以上']].sum(axis=1).loc[[2000,2010,2019,2022,2025]].round(3))
print(C.loc[2025].round(0)); 
Wn.to_csv('age_w.csv'); C.to_csv('age_c.csv')
# workers APC by age
Ww,Aw,Aavg=panel('04','249')
print('workers APC avg',Aavg.loc[[2000,2010,2019,2022,2023,2024,2025]].round(1).to_dict())
print(Aw.loc[[2019,2025]].round(1).T)
Aw.to_csv('age_apc_w.csv'); Aavg.to_csv('apc_w_avg.csv')
# workers: composition vs within for APC
Ww,Cw,_=panel('04','059'); _,Yw,_=panel('04','233')
Wwn=Ww.div(Ww.sum(axis=1),axis=0)
def apc(w,c,y): return 100*(w*c).sum()/(w*y).sum()
for a,b in [(2019,2025),(2022,2025)]:
    act_a=apc(Wwn.loc[a],Cw.loc[a],Yw.loc[a]); act_b=apc(Wwn.loc[b],Cw.loc[b],Yw.loc[b])
    fixw=apc(Wwn.loc[a],Cw.loc[b],Yw.loc[b])
    print(f'workers APC {a}->{b}: {act_a:.1f}->{act_b:.1f}; with {a} weights {fixw:.1f} => within {fixw-act_a:.2f}, composition {act_b-fixw:.2f}')
print('worker 65+ share', Wwn[['65～69歳','70歳以上']].sum(axis=1).loc[[2019,2025]].round(3).to_dict())
from scripts.estat_api import get_stats_df
cpi=get_stats_df("0003427113",cdCat01="0001",cdArea="00000",cdTab="1")
cpi=cpi[cpi.time_name.str.fullmatch(r'\d{4}年')]; cpi['y']=cpi.time_name.str[:4].astype(int)
cpi=cpi.set_index('y').value; print('CPI 2019,2022,2025',cpi.loc[[2019,2022,2025]].to_dict()); cpi.to_csv('cpi_y.csv')
