import sys; sys.path.insert(0,'/mnt/skills/plugins/estat-api')
import pandas as pd, numpy as np
from scripts.estat_api import read_stats_csv, keep_monthly
def ser(f,c): df=read_stats_csv(f); return keep_monthly(df[df.cat01_code==c])['value']
E=ser('cpi_svc.csv','0229'); O=ser('cpi_svc.csv','0232'); M=ser('cpi_idx.csv','7430'); H=ser('cpi_hotel.csv','9300')
idx=E.index; M=M.reindex(idx); H=H.reindex(idx)
def term(w,I):  # weighted level at t-12 and weighted change
    L=w*I.shift(12); return L.fillna(0), (w*(I-I.shift(12))).fillna(0)
parts=[(508,E,1),(1450,O,1),(181,M,-1),(118,H,-1)]
num=sum(sg*term(w,I)[1] for w,I,sg in parts); den=sum(sg*term(w,I)[0] for w,I,sg in parts)
y=(num/den*100).where(E.shift(12).notna())
q=y.groupby(y.index.asfreq('Q')).mean().rename('gsvc')
q.to_csv('gsvc_q.csv'); print(q.loc['2012Q1':].iloc[::2].round(2).to_string())
