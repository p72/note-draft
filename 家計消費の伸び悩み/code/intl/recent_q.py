import pandas as pd, numpy as np
A=['JPN','USA','GBR','DEU','FRA','ITA','CAN','KOR','AUS']
q=pd.read_csv('qsa.csv'); c=pd.read_csv('qna_p3.csv'); cl=pd.read_csv('qna_p3_L.csv'); p=pd.read_csv('qpop.csv')
def piv(d): return d.pivot(index='TIME_PERIOD',columns='REF_AREA',values='OBS_VALUE')
Yd=piv(q[(q.TRANSACTION=='B6G')&(q.ACCOUNTING_ENTRY=='C')])
D1=piv(q[(q.TRANSACTION=='D1')&(q.ACCOUNTING_ENTRY=='C')])
Cn=piv(c); Cr=piv(cl); POP=piv(p[p.ADJUSTMENT=='N']).ffill()
# Japan from ESRI (households incl. unincorporated, excl. NPISH)
k=pd.read_csv('../levels3.csv',index_col=0)
k.index=[f"{i[:4]}-Q{i[-1]}" for i in k.index]
Yd['JPN']=k.yd; Cn['JPN']=k.c; Cr['JPN']=k.cr; D1['JPN']=k.comp
L=np.log; rows=[]
for a in A:
    if a=='KOR': continue
    ok=Yd[a].dropna().index
    last=sorted(ok)[-4:]
    for base,bq in [('2019',[f'2019-Q{i}' for i in range(1,5)]),('2022',[f'2022-Q{i}' for i in range(1,5)])]:
        m=lambda s,qs: s.reindex(qs).mean()
        y0,y1=m(Yd[a],bq)/m(POP[a],bq), m(Yd[a],last)/m(POP[a],last)
        c0,c1=m(Cn[a],bq),m(Cn[a],last); r0,r1=m(Cr[a],bq),m(Cr[a],last)
        P0,P1=c0/r0,c1/r1; apc0,apc1=c0/m(Yd[a],bq),c1/m(Yd[a],last)
        crpc=100*(L(r1/m(POP[a],last))-L(r0/m(POP[a],bq)))
        w0,w1=m(D1[a],bq)/m(POP[a],bq), m(D1[a],last)/m(POP[a],last)
        rows.append(dict(area=a,base=base,end=f'{last[0]}〜{last[-1]}',real_C_pc=crpc,nomYd_pc=100*L(y1/y0),prices=100*L(P1/P0),
                         realYd_pc=100*L(y1/y0)-100*L(P1/P0),APC=100*L(apc1/apc0),nomComp_pc=100*L(w1/w0),realComp_pc=100*L(w1/w0)-100*L(P1/P0)))
# Korea annual 2022->2025 (and 2019->2025)
t14=pd.read_csv('table14.csv'); t1=pd.read_csv('table1_p3.csv'); pa=pd.read_csv('pop.csv')
kY=t14[(t14.REF_AREA=='KOR')&(t14.TRANSACTION=='B6G')&(t14.ACCOUNTING_ENTRY=='C')].set_index('TIME_PERIOD').OBS_VALUE
kW=t14[(t14.REF_AREA=='KOR')&(t14.TRANSACTION=='D1')&(t14.ACCOUNTING_ENTRY=='C')].set_index('TIME_PERIOD').OBS_VALUE
kC=t1[(t1.REF_AREA=='KOR')&(t1.SECTOR=='S1M')&(t1.PRICE_BASE=='V')].set_index('TIME_PERIOD').OBS_VALUE
kR=t1[(t1.REF_AREA=='KOR')&(t1.SECTOR=='S1M')&(t1.PRICE_BASE=='LR')].set_index('TIME_PERIOD').OBS_VALUE
kP=pa[pa.REF_AREA=='KOR'].set_index('TIME_PERIOD').OBS_VALUE
for b in [2019,2022]:
    e=2025; P0,P1=kC[b]/kR[b],kC[e]/kR[e]
    rows.append(dict(area='KOR',base=str(b),end='2025年（年次）',real_C_pc=100*L((kR[e]/kP[e])/(kR[b]/kP[b])),nomYd_pc=100*L((kY[e]/kP[e])/(kY[b]/kP[b])),
        prices=100*L(P1/P0),realYd_pc=100*L((kY[e]/kP[e])/(kY[b]/kP[b]))-100*L(P1/P0),APC=100*L((kC[e]/kY[e])/(kC[b]/kY[b])),
        nomComp_pc=100*L((kW[e]/kP[e])/(kW[b]/kP[b])),realComp_pc=100*L((kW[e]/kP[e])/(kW[b]/kP[b]))-100*L(P1/P0)))
R=pd.DataFrame(rows); R['resid']=R.real_C_pc-(R.realYd_pc+R.APC); R.to_csv('decomp_recent_q.csv',index=False)
pd.set_option('display.width',250)
for b,g in R.groupby('base'): print('=== base',b); print(g.drop(columns='base').round(1).sort_values('real_C_pc').to_string(index=False))
