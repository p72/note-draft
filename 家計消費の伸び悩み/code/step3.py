import sys, pandas as pd, numpy as np
sys.path.insert(0,'/mnt/skills/plugins/esri-data')
from scripts.esri_data import get_consumer_sentiment
k=pd.read_csv('levels.csv',index_col=0); k.index=pd.PeriodIndex(k.index,freq='Q')
ff=pd.read_csv('ff.csv',index_col=0,parse_dates=True); ff.index=ff.index.to_period('Q')
ff.columns=['FA','NW','DEP']
csi=get_consumer_sentiment(); csi['q']=pd.to_datetime(csi.date).dt.to_period('Q')
cq=csi.groupby('q').CSI.mean()
k=k.join(ff).join(cq.rename('CSI'))
k['yd_q']=k.yd/4  # quarterly flow (10億円)
k['nw_y']=k.NW/10/k.yd   # 億円→10億円 / annualized Yd
k['dep_y']=k.DEP/10/k.yd
k['pi']=100*(np.log(k.P)-np.log(k.P.shift(4)))
# excess saving vs 2015-2019 avg rate
base=k.loc['2015Q1':'2019Q4','sr'].mean()
k['exc']=(k.s - base/100*(k.yd+k.adj))/4
k['cum_exc']=k.loc['2020Q1':,'exc'].cumsum()
print('baseline sr',round(base,2))
print(k.loc['2019Q4':,['sr','exc','cum_exc','nw_y','dep_y','CSI','pi']].round(2).to_string())
k.to_csv('levels3.csv')
