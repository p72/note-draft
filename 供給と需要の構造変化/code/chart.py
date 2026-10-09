import pandas as pd, numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
plt.rcParams["font.family"]="Noto Sans CJK JP"
d=pd.read_csv("merged.csv",index_col="q",parse_dates=["date"])
fig,ax=plt.subplots(2,1,figsize=(8,9))
# panel1 potential
pre=d.loc["1994Q1":"2008Q3"]; b=np.polyfit(pre.t,pre.lP,1)
x=d.loc["1994Q1":"2026Q2"]; ax[0].plot(x.date,x.pot/1000,label="潜在GDP（日銀ギャップから逆算）",color="C0",lw=2)
ax[0].plot(x.date,x.GDP/1000,label="実質GDP",color="gray",lw=1,alpha=.7)
ax[0].plot(x.date,np.exp(np.polyval(b,x.t))/1000,"--",color="C0",label="1994〜2008Q3トレンドの延長")
for q,l in [("2008Q4","リーマン"),("2011Q1","震災")]:
    ax[0].axvline(d.loc[q,"date"],color="C3",ls=":"); ax[0].text(d.loc[q,"date"],ax[0].get_ylim()[0] if False else 505,l,color="C3",ha="right",fontsize=9)
ax[0].set_title("供給側：潜在GDPはリーマンで水準が段差状に低下（−3.7%, p<0.001）"); ax[0].set_ylabel("兆円（2020年連鎖価格・年率）"); ax[0].legend(fontsize=8,loc="upper left"); ax[0].grid(alpha=.3)
# panel2 consumption
pre=d.loc["2002Q1":"2013Q4"]; b=np.polyfit(pre.t,pre.lC,1)
x=d.loc["2002Q1":"2026Q2"]; ax[1].plot(x.date,x.HouseholdConsumptionExImputedRent/1000,color="C1",lw=2,label="実質家計消費（除く帰属家賃）")
x2=d.loc["2002Q1":"2019Q3"]; ax[1].plot(x2.date,np.exp(np.polyval(b,x2.t))/1000,"--",color="C1",label="2002〜2013年トレンドの延長（保守的な反実仮想）")
for q,l in [("2014Q2","8%"),("2019Q4","10%")]:
    ax[1].axvline(d.loc[q,"date"],color="C3",ls=":"); ax[1].text(d.loc[q,"date"],ax[1].get_ylim()[1]*0.995,l+"増税",color="C3",ha="right",va="top",fontsize=9)
ax[1].set_title("需要側：消費は2014年増税で水準・傾きとも屈折（リーマン後の最大F点=2014Q2）"); ax[1].set_ylabel("兆円（2020年連鎖価格・年率）"); ax[1].legend(fontsize=8,loc="lower left"); ax[1].grid(alpha=.3)
fig.text(0.01,0.005,"出典：日本銀行「需給ギャップと潜在成長率」、内閣府「四半期別GDP速報」2026年4-6月期2次速報",fontsize=7)
plt.tight_layout(rect=[0,0.015,1,1]); plt.savefig("../01_chart_level.png",dpi=150)
