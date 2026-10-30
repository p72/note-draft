import sys; sys.path.insert(0,'/mnt/skills/plugins/fred-data')
from scripts.fred_data import *
import numpy as np, pandas as pd
inc=get_fred("W875RX1",start="2009-01-01"); pop=get_fred("POPTHM",start="2009-01-01")
pc=(inc*1e9/(pop*1e3)).dropna()
pc.to_csv("us_pc.csv")
w=pc.loc["2009-06":"2020-02"]; t=np.arange(len(pc)); tw=t[:len(w)]
# regression
b,a=np.polyfit(tw[:len(w)]+0, np.log(w.values),1)
i0=pc.index.get_loc(w.index[0]); tt=t-i0
tr=np.exp(a+b*tt); print("reg growth",np.exp(12*b)-1, "gap",(pc.iloc[-1]/tr[-1]-1)*100)
# endpoint
g=(w.iloc[-1]/w.iloc[0])**(1/((len(w)-1)))
tr2=w.iloc[0]*g**tt; print("endpt growth",g**12-1,"gap",(pc.iloc[-1]/tr2[-1]-1)*100)
print(pc.tail(3)); print(source_note(inc,pop))
