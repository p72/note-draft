import sys; sys.path.insert(0,'/mnt/skills/plugins/fred-data')
from scripts.fred_data import setup_japanese_font
import numpy as np, pandas as pd, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, matplotlib.dates as md
setup_japanese_font()
df=pd.read_csv('jp_pc.csv',index_col=0); df.index=pd.PeriodIndex(df.index,freq='Q')
df=df.loc['2008Q1':]/1e4  # 万円
x=df.index.to_timestamp(how='start')+pd.Timedelta(days=45)
res={}
for c in 'AB':
    s=df[c]; w=s.loc['2009Q2':'2019Q4']; i0=s.index.get_loc(w.index[0])
    b,a=np.polyfit(np.arange(len(w)),np.log(w.values),1); t=np.arange(len(s))-i0
    tr=pd.Series(np.exp(a+b*t),s.index); res[c]=(tr,(s/tr-1)*100,(np.exp(4*b)-1)*100)
C={'B':"#1aa6c9",'A':"#2b4c7e"}; O={'B':"#e8572a",'A':"#f2a33a"}
lab={'B':'米国定義（第1次所得−純社会負担）','A':'第1次所得（営業余剰・混合所得＋雇用者報酬＋財産所得）'}
fig,(ax1,ax2)=plt.subplots(1,2,figsize=(14,6.6))
def rec(ax):
    for a_,b_ in [("2008-02","2009-03"),("2012-03","2012-11"),("2018-10","2020-05")]:
        ax.axvspan(pd.Timestamp(a_),pd.Timestamp(b_),color="lightgray",alpha=.6)
    ax.grid(alpha=.3); ax.xaxis.set_major_locator(md.YearLocator(2)); ax.xaxis.set_major_formatter(md.DateFormatter("%Y"))
    ax.set_xlim(pd.Timestamp("2008-01-01"),pd.Timestamp("2027-06-01"))
m=x>=pd.Timestamp("2009-04-01")
for c in 'AB':
    tr,g,gr=res[c]
    ax1.plot(x,df[c],color=C[c],lw=2,label=lab[c])
    ax1.plot(x[m],tr[m],"--",color=O[c],lw=1.8,label=f"2009–2019年トレンド（年率{gr:.2f}%）")
    ax1.annotate(f"{df[c].iloc[-1]:.1f}",(x[-1],df[c].iloc[-1]),xytext=(8,0),textcoords="offset points",color=C[c],va="center",bbox=dict(fc="white",ec=C[c]))
    ax2.plot(x[m],g[m],color=C[c],lw=2,label=lab[c].split('（')[0]+'：トレンドからの乖離（%）')
    ax2.annotate(f"{g.iloc[-1]+0.0001:+.1f}",(x[-1],g.iloc[-1]),xytext=(8,0),textcoords="offset points",color=C[c],va="center",bbox=dict(fc="white",ec=C[c]))
ax1.set_ylabel("万円／人（2020年連鎖価格、年率）"); ax1.legend(loc="upper left",fontsize=8.5,frameon=False); rec(ax1)
ax1.set_ylim(180,320)
ax2.axhline(0,color="gray",lw=1); ax2.legend(loc="upper left",fontsize=9,frameon=False); rec(ax2)
gB=res['B'][1].iloc[-1]; gA=res['A'][1].iloc[-1]
fig.suptitle(f"日本：移転所得を除く1人当たり実質家計所得、コロナ前トレンド比 {gB:+.1f}%（米国定義）／{gA+0.0001:+.1f}%（第1次所得）",fontsize=14.5,fontweight="bold",x=0.02,ha="left")
fig.text(0.02,0.905,"家計の所得（社会給付・その他経常移転を除く）÷総人口、家計最終消費支出デフレーターで実質化。季調・四半期、2026年4-6月期まで。\nトレンドは2009年4-6月期〜2019年10-12月期の対数線形回帰。灰色は景気後退期（内閣府景気基準日付）。",fontsize=9.5,va="top")
fig.text(0.99,0.01,"出所：内閣府「家計可処分所得・家計貯蓄率四半期別速報（参考系列）」、総務省「人口推計」　作成：Claude",ha="right",fontsize=9,color="gray")
fig.tight_layout(rect=[0,0.03,1,0.85]); fig.savefig("../01_chart_jp.png",dpi=150)
print(df.tail(3)); print({c:res[c][1].loc['2020Q1':].round(1).tolist() for c in 'AB'})
