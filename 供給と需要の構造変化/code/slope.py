import pandas as pd, numpy as np, statsmodels.api as sm, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
plt.rcParams["font.family"]="Noto Sans CJK JP"
d=pd.read_csv("merged.csv",index_col="q",parse_dates=["date"])
def segs(col,segments):
    out=[]
    for lab,a,b in segments:
        s=d.loc[a:b]; m=sm.OLS(s[col]*100,sm.add_constant(s.t)).fit(cov_type="HAC",cov_kwds={"maxlags":4})
        out.append(dict(lab=lab,a=a,b=b,slope=m.params.iloc[1]*4,ci=1.96*m.bse.iloc[1]*4,fit=np.exp(m.predict(sm.add_constant(s.t))/100),dates=s.date))
    return out
P=segs("lP",[("リーマン前\n94Q1–08Q3","1994Q1","2008Q3"),("リーマン〜震災\n08Q4–10Q4","2008Q4","2010Q4"),("震災後\n11Q1–19Q4","2011Q1","2019Q4")])
C=segs("lC",[("リーマン前\n02Q1–08Q3","2002Q1","2008Q3"),("リーマン〜震災\n08Q4–10Q4","2008Q4","2010Q4"),("震災〜増税前\n11Q2–13Q4","2011Q2","2013Q4"),("8%増税後\n14Q2–19Q3","2014Q2","2019Q3")])
for n,S in [("潜在GDP",P),("消費",C)]:
    for s in S: print(n,s["lab"].replace("\n"," "),f"{s['slope']:.2f}±{s['ci']:.2f}")
fig,ax=plt.subplots(2,2,figsize=(11,9),gridspec_kw={"width_ratios":[1.6,1]})
cols=["#4C72B0","#C44E52","#DD8452","#55A868"]
def panel(axl,axr,S,col,raw,title,start,events):
    x=d.loc[start:"2019Q4"]; axl.plot(x.date,x[col]/1000,color="lightgray",lw=1.5,label=raw)
    for i,s in enumerate(S):
        axl.plot(s["dates"],s["fit"]/1000,color=cols[i],lw=2.5)
        mid=s["dates"].iloc[len(s["dates"])//2]
        axl.annotate(f"{s['slope']:+.2f}%/年",(mid,s["fit"].iloc[len(s['fit'])//2]/1000),textcoords="offset points",xytext=(0,10),ha="center",color=cols[i],fontsize=10,fontweight="bold")
    for q,l in events: axl.axvline(d.loc[q,"date"],color="k",ls=":",lw=.8); axl.text(d.loc[q,"date"],axl.get_ylim()[0],l,fontsize=8,ha="right",va="bottom")
    axl.set_title(title); axl.set_ylabel("兆円（2020年連鎖価格・年率）"); axl.grid(alpha=.3); axl.legend(fontsize=8,loc="upper left")
    y=np.arange(len(S)); axr.barh(y,[s["slope"] for s in S],xerr=[s["ci"] for s in S],color=cols[:len(S)],capsize=4)
    axr.set_yticks(y,[s["lab"] for s in S],fontsize=8); axr.invert_yaxis(); axr.axvline(0,color="k",lw=.8)
    for i,s in enumerate(S): axr.text(s["slope"]+s["ci"]+0.05,i,f"{s['slope']:+.2f}",va="center",ha="left",fontsize=9)
    axr.set_xlim(right=max(s["slope"]+s["ci"] for s in S)*1.3); axr.set_xlabel("区間トレンドの傾き（%/年, 95%CI）"); axr.grid(axis="x",alpha=.3)
panel(ax[0,0],ax[0,1],P,"pot","潜在GDP（日銀ギャップから逆算）","供給側：潜在GDPの区間別トレンド","1994Q1",[("2008Q4","リーマン"),("2011Q1","震災")])
panel(ax[1,0],ax[1,1],C,"HouseholdConsumptionExImputedRent","実質家計消費（除く帰属家賃）","需要側：家計消費の区間別トレンド","2002Q1",[("2008Q4","リーマン"),("2011Q1","震災"),("2014Q2","8%増税")])
fig.text(0.01,0.005,"出典：日本銀行「需給ギャップと潜在成長率」、内閣府「四半期別GDP速報」2026年4-6月期2次速報。傾きは各区間の対数線形回帰（HAC標準誤差）。2014Q1駆け込み・2019Q4以降は除外",fontsize=7)
plt.tight_layout(rect=[0,0.015,1,1]); plt.savefig("../01_chart_slope.png",dpi=150)
