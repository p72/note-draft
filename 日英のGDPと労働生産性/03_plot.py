import json, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.family"]="Noto Sans CJK JP"; plt.rcParams["axes.unicode_minus"]=False
def load(s):
    # FRED API（環境変数 FRED_API_KEY）から年平均を取得する
    import os, urllib.request
    u=("https://api.stlouisfed.org/fred/series/observations?series_id=%s&api_key=%s"
       "&file_type=json&frequency=a&observation_start=1994-01-01")%(s,os.environ["FRED_API_KEY"])
    o=json.load(urllib.request.urlopen(u))["observations"]
    return {int(x["date"][:4]):float(x["value"]) for x in o if x["value"]!="." and int(x["date"][:4])<=2025}
r,n=load("RBJPBIS"),load("NBJPBIS")
yrs=[y for y in sorted(r) if 2000<=y<=2025]
lr=np.array([np.log(r[y]/r[2000]) for y in yrs]); ln=np.array([np.log(n[y]/n[2000]) for y in yrs])
print("2019 REER %.3f NEER %.3f diff %.3f"%(lr[19],ln[19],lr[19]-ln[19]), "2025", lr[-1], ln[-1], "idx2019", 100*np.exp(lr[19]))
SRC="出所：BIS「Effective exchange rate indices」（広義、年平均、FRED経由）。"
# 図1
fig,ax=plt.subplots(figsize=(9,5))
ax.axvspan(2000,2019,color="#f2f2f2",zorder=0)
ax.plot(yrs,100*np.exp(lr),color="black",lw=2.5)
ax.axhline(100,color="gray",lw=0.8)
ax.annotate("2019年 %.0f"%(100*np.exp(lr[19])),(2019,100*np.exp(lr[19])),xytext=(2014.3,48),arrowprops=dict(arrowstyle="-",color="gray"))
ax.annotate("2025年 %.0f"%(100*np.exp(lr[-1])),(2025,100*np.exp(lr[-1])),xytext=(2022.3,38))
ax.set_ylim(30,110); ax.set_xlim(2000,2026); ax.set_ylabel("2000年＝100")
ax.set_title("日本の実質実効為替レート（2000年＝100）")
ax.grid(alpha=0.3); ax.text(2000.3,33,"網掛けは2000〜2019年",color="gray",fontsize=9)
fig.text(0.01,0.01,SRC,fontsize=8,color="gray"); fig.tight_layout(rect=(0,0.03,1,1)); fig.savefig("03_chart_reer.png",dpi=150)
# 図2
fig,ax=plt.subplots(figsize=(9,5))
ax.axvspan(2000,2019,color="#f2f2f2",zorder=0)
ax.fill_between(yrs,ln,lr,color="#1f77b4",alpha=0.2,label="両者の差＝日本と貿易相手国の物価上昇率の差")
ax.plot(yrs,lr,color="black",lw=2.5,label="実質実効為替レート")
ax.plot(yrs,ln,color="gray",lw=2,ls="--",label="名目実効為替レート")
ax.axhline(0,color="black",lw=0.8)
ax.annotate("名目 %.2f"%ln[19],(2019,ln[19]),xytext=(2017.2,0.07))
ax.annotate("実質 %.2f"%lr[19],(2019,lr[19]),xytext=(2016.2,-0.66))
ax.set_xlim(2000,2026); ax.set_ylabel("2000年からの対数変化")
ax.set_title("実質実効為替レートと名目実効為替レート（2000年＝0）")
ax.grid(alpha=0.3); ax.legend(loc="lower left",fontsize=9)
fig.text(0.01,0.01,SRC,fontsize=8,color="gray"); fig.tight_layout(rect=(0,0.03,1,1)); fig.savefig("03_chart_reer_neer.png",dpi=150)
