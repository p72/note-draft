import sys, pandas as pd, numpy as np, re
sys.path.insert(0,'/mnt/skills/plugins/esri-data')
from scripts.esri_data import get_qe_df
F='/tmp/claude-0/-home-claude/e8065db3-0636-5980-947f-2cabd18139ba/scratchpad/dl/kakei_26q2.xlsx'
raw=pd.read_excel(F,sheet_name='季調系列 Seasonally adjusted series',header=None)
cols=['op','comp','prop','tax','soc','ben','oth','yd','adj','c','s','_','sr','__','yd_real']
rows=[]; yr=None
for i in range(8,len(raw)):
    lab=str(raw.iloc[i,0]); m=re.match(r'\s*(\d{4})/',lab)
    if m: yr=int(m.group(1))
    q=re.search(r'(\d+)-\s*(\d+)\.',lab)
    if not q or pd.isna(pd.to_numeric(raw.iloc[i,1],errors='coerce')): continue
    qq={1:1,4:2,7:3,10:4}[int(q.group(1))]
    rows.append([yr,qq]+[pd.to_numeric(v,errors='coerce') for v in raw.iloc[i,1:16]])
k=pd.DataFrame(rows,columns=['year','q']+cols).drop(columns=['_','__'])
k['date']=pd.PeriodIndex.from_fields(year=k.year,quarter=k.q,freq='Q')
k=k.set_index('date')
r=get_qe_df('gaku-jk'); n=get_qe_df('gaku-mk')
print(r.columns.tolist()[:6]); print(r.tail(2))
