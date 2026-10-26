import pandas as pd, numpy as np, re
D='/tmp/claude-0/-home-claude/e8065db3-0636-5980-947f-2cabd18139ba/scratchpad/dl2/'
raw=pd.read_excel(D+'csi_age_2p.xlsx',sheet_name=0,header=None)
ages=raw.iloc[3,3:].ffill(); items=raw.iloc[4,3:]
def short(s):
    s=str(s); 
    for k in ['暮らし向き','収入の増え方','雇用環境','買い時判断','資産価値']:
        if k in s: return k
    return '消費者態度指数'
cols=[(a,short(i)) for a,i in zip(ages,items)]
rows=[]; y=None
for r in range(5,len(raw)):
    m=re.search(r'(平成|令和)(\d+|元)年',str(raw.iloc[r,1]))
    if m: y=(1988 if m.group(1)=='平成' else 2018)+(1 if m.group(2)=='元' else int(m.group(2)))
    mo=re.search(r'(\d+)月',str(raw.iloc[r,2]))
    if not mo or y is None: continue
    vals=pd.to_numeric(raw.iloc[r,3:],errors='coerce').values
    rows.append([y,int(mo.group(1))]+list(vals))
df=pd.DataFrame(rows,columns=['year','month']+[f'{a}|{i}' for a,i in cols])
print(df.year.min(),df.year.max(), df.tail(1)[['year','month']].values)
ann=df.groupby('year').mean().drop(columns='month')
A=sorted(set(ages),key=lambda s:list(ages).index(s)); print(A)
res=[]
for a in A:
    for it in ['消費者態度指数','暮らし向き','収入の増え方','雇用環境','買い時判断']:
        c=f'{a}|{it}'
        if c in ann: res.append([a,it,ann.loc[2019,c],ann.loc[2022,c],ann.loc[2025,c],df[df.year==2026][c].mean()])
t=pd.DataFrame(res,columns=['age','item','2019','2022','2025','2026(1-9月)']); t['Δ19→25']=t['2025']-t['2019']; t['Δ19→26']=t['2026(1-9月)']-t['2019']
pd.set_option('display.width',200); print(t.round(1).to_string()); t.to_csv('csi_age.csv',index=False); ann.to_csv('csi_age_ann.csv')
# price expectations: share >=5%
pr=pd.read_excel(D+'price_age_2p.xlsx',sheet_name=0,header=None)
pa=pr.iloc[2,3:].ffill(); pi=pr.iloc[3,3:]
rows=[]; y=None
for r in range(5,len(pr)):
    m=re.search(r'(平成|令和)(\d+|元)年',str(pr.iloc[r,1]))
    if m: y=(1988 if m.group(1)=='平成' else 2018)+(1 if m.group(2)=='元' else int(m.group(2)))
    if not re.search(r'月',str(pr.iloc[r,2])) or y is None: continue
    v=pd.to_numeric(pr.iloc[r,3:],errors='coerce').values; rows.append([y]+list(v))
P=pd.DataFrame(rows,columns=['year']+[f'{a}|{i}' for a,i in zip(pa,pi)])
out=[]
for a in A:
    c5=[f'{a}|上がる_５％以上～10％未満',f'{a}|上がる_10％以上']
    if all(c in P for c in c5):
        s=P[c5].fillna(0).sum(axis=1); g=s.groupby(P.year).mean(); out.append([a,g.get(2019),g.get(2025),g.get(2026)])
print(pd.DataFrame(out,columns=['age','5%以上上昇予想 2019','2025','2026']).round(1).to_string())
