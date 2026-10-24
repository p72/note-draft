import sys; sys.path.insert(0,'/mnt/skills/plugins/estat-api')
import pandas as pd, numpy as np
from scipy.optimize import nnls
from scripts.estat_api import read_stats_csv, keep_monthly
def series(df,c): return keep_monthly(df[df.cat01_code==c])['value']
sv=read_stats_csv('cpi_svc.csv'); co=read_stats_csv('cpi_idx.csv')
S={c:series(sv,c) for c in ['0220','0221','0222','0229','0230','0231','0232']}
M=series(co,'7430')
H=series(read_stats_csv('cpi_hotel.csv'),'9300')
# NNLS weights within services on 2025-01..
P=pd.DataFrame(S).loc['2025-01':]
w,_=nnls(P[['0221','0229','0230','0231','0232']].values,P['0220'].values)
sh=dict(zip(['0221','0229','0230','0231','0232'],w)); print({k:round(v,4) for k,v in sh.items()}, sum(w))
# 公営家賃 share within 公共サービス: estimate weight from known? use NNLS can't; use relative: assume share 0.08 of public svc? -> estimate via total weights
W_S=4964
wR=(sh['0230']+sh['0231'])*W_S; print('民営+帰属 weight', wR)
# public rent weight: rough from 2020 base ~ 公営・UR家賃 ≈ 50
wP=50; wM=181
Sx=S['0220']
comps={'0230':sh['0230']*W_S,'0231':sh['0231']*W_S,'0222':wP,'7430':wM,'9300':118}
idx={'0230':S['0230'],'0231':S['0231'],'0222':S['0222'],'7430':M,'9300':H}
y=Sx/Sx.shift(12)-1
num=y.copy(); den=pd.Series(1.0,index=y.index)
for k,wk in comps.items():
    I=idx[k].reindex(y.index); r=(wk/W_S)*(I.shift(12)/Sx.shift(12)); yi=I/I.shift(12)-1
    r=r.fillna(0); yi=yi.fillna(0)
    num=num-r*yi; den=den-r
yex=(num/den)*100
out=pd.DataFrame({'svc':y*100,'svc_ex':yex})
q=out.groupby(out.index.asfreq('Q')).mean()
q.to_csv('svc_q.csv'); print(q.loc['2012Q1':].iloc[::2].round(2).T.to_string())
