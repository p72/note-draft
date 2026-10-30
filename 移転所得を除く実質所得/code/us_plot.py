import sys; sys.path.insert(0,'/mnt/skills/plugins/fred-data')
from scripts.fred_data import setup_japanese_font
import numpy as np, pandas as pd, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, matplotlib.dates as md
setup_japanese_font()
pc=pd.read_csv("us_pc.csv",index_col=0,parse_dates=True).iloc[:,0]
w=pc.loc["2009-06":"2020-02"]; i0=pc.index.get_loc(w.index[0])
b,a=np.polyfit(np.arange(len(w)),np.log(w.values),1)
t=np.arange(len(pc))-i0
tr=pd.Series(np.exp(a+b*t),pc.index).loc["2009-06":]
gap=(pc.loc["2009-06":]/tr-1)*100
fig,(ax1,ax2)=plt.subplots(1,2,figsize=(14,6.2))
C="#1aa6c9"; O="#e8572a"
def rec(ax):
    ax.axvspan(pd.Timestamp("2009-01-01"),pd.Timestamp("2009-06-30"),color="lightgray",alpha=.6)
    ax.axvspan(pd.Timestamp("2020-02-01"),pd.Timestamp("2020-04-30"),color="lightgray",alpha=.6)
    ax.grid(alpha=.3); ax.xaxis.set_major_locator(md.YearLocator(2)); ax.xaxis.set_major_formatter(md.DateFormatter("%Y"))
ax1.plot(pc.index,pc,color=C,lw=2,label="移転所得を除く1人当たり実質個人所得（2017年ドル）")
ax1.plot(tr.index,tr,"--",color=O,lw=2,label=f"2009–2020年トレンド（年率{(np.exp(12*b)-1)*100:.1f}%）")
ax1.annotate(f"{pc.iloc[-1]:,.0f}",(pc.index[-1],pc.iloc[-1]),xytext=(8,0),textcoords="offset points",color=C,va="center",bbox=dict(fc="white",ec=C))
ax1.set_ylim(34000,52000); ax1.yaxis.set_major_formatter(matplotlib.ticker.StrMethodFormatter("{x:,.0f}"))
ax1.legend(loc="upper left",fontsize=9,frameon=False); rec(ax1)
ax2.plot(gap.index,gap,color=C,lw=2,label="2009–2020年トレンドからの乖離（%）")
ax2.axhline(0,color="gray",lw=1)
ax2.annotate(f"{gap.iloc[-1]:.1f}",(gap.index[-1],gap.iloc[-1]),xytext=(8,0),textcoords="offset points",color=C,va="center",bbox=dict(fc="white",ec=C))
ax2.set_ylim(-8,6); ax2.legend(loc="upper left",fontsize=9,frameon=False); rec(ax2)
for ax in (ax1,ax2): ax.set_xlim(pd.Timestamp("2009-01-01"),pd.Timestamp("2027-01-01"))
fig.suptitle(f"米国：移転所得を除く1人当たり実質個人所得はコロナ前トレンドを{abs(gap.iloc[-1]):.1f}%下回る",fontsize=15,fontweight="bold",x=0.02,ha="left")
fig.text(0.02,0.905,"移転所得を除く実質個人所得÷人口（2017年連鎖ドル、月次、2026年9月まで）。トレンドは2009年6月〜2020年2月の対数線形回帰。灰色は景気後退期（NBER）。",fontsize=9.5)
fig.text(0.99,0.01,"出所：BEA（FRED: W875RX1, POPTHM）、NBER　再現：Claude",ha="right",fontsize=9,color="gray")
fig.tight_layout(rect=[0,0.03,1,0.89]); fig.savefig("../01_chart_us.png",dpi=150)
