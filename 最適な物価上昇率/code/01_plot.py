import sys, pandas as pd, numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
sys.path.insert(0,"/root/.claude/skills/synced/42857046-7317-47fd-aa84-fb40ead701d4_f90ecdde-6477-4665-b7b2-90b3176d5903/esri-data")
from scripts.esri_data import setup_japanese_font
print(setup_japanese_font())
e=pd.read_csv("esri.csv",index_col=0); c=pd.read_csv("cpi.csv",index_col=0)
d=e.join(c).loc[1995:2025]
zero=d[d.CPI.abs()<=0.5]
print(zero); print(zero.mean().round(2)); print(d.loc[1995:2012].mean().round(2), d.loc[2022:2025].mean().round(2))
fig,ax=plt.subplots(2,1,figsize=(11,10),gridspec_kw={"height_ratios":[1.2,1]})
a=ax[0]
for y in zero.index: a.axvspan(y-0.5,y+0.5,color="#ffe9a8",alpha=0.6,lw=0)
a.bar(d.index,d["名目"],color="#1f77b4",alpha=0.8,label="名目GDP成長率")
a.plot(d.index,d["実質"],"o-",color="#2ca02c",label="実質GDP成長率",ms=4)
a.plot(d.index,d["デフレーター"],"s--",color="#d62728",label="GDPデフレーター",ms=4)
a.plot(d.index,d["CPI"],"^-",color="#ff7f0e",label="CPI（総合）",ms=4)
a.axhline(0,color="k",lw=0.8); a.grid(alpha=0.3)
a.set_title("日本の名目成長・実質成長・物価（暦年、前年比%）\n黄色の帯＝CPIがほぼゼロ（±0.5%以内）の年",fontsize=13)
a.set_ylabel("%"); a.legend(loc="lower left",ncol=2,fontsize=9)
b=ax[1]
col=np.where(d.index>=2022,"#d62728",np.where(d.index>=2013,"#9467bd","#1f77b4"))
b.scatter(d.CPI,d["名目"],c=col,s=50,zorder=3)
for y,r in d.iterrows(): b.annotate(str(y),(r.CPI,r["名目"]),fontsize=7,xytext=(3,3),textcoords="offset points")
b.axvspan(-0.5,0.5,color="#ffe9a8",alpha=0.6,zorder=0)
b.axhline(0,color="k",lw=0.8); b.axvline(0,color="k",lw=0.8); b.grid(alpha=0.3)
from matplotlib.lines import Line2D
b.legend(handles=[Line2D([],[],marker="o",ls="",color=k,label=l) for k,l in [("#1f77b4","1995–2012"),("#9467bd","2013–2021"),("#d62728","2022–2025")]],fontsize=9,loc="upper left")
b.set_xlabel("CPI上昇率（%）"); b.set_ylabel("名目GDP成長率（%）")
b.set_title("CPI上昇率 × 名目GDP成長率",fontsize=12)
fig.text(0.01,0.005,"出所：内閣府「四半期別GDP速報」2026年7-9月期1次速報（暦年）、総務省「消費者物価指数」2020年基準（月次指数の年平均から算出）",fontsize=8)
plt.tight_layout(rect=[0,0.02,1,1]); plt.savefig("jp_nominal_cpi.png",dpi=150)
