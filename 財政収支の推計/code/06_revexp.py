"""一般政府の収入・支出・財政収支（対名目GDP比、1994〜2024年度）
データ: 内閣府「2024年度国民経済計算年次推計」付表6（一般政府の部門別勘定）・主要系列表(1)（名目GDP、年度）
ESRIデータ取得ヘルパー（esri-data スキルの scripts/esri_data.py）を ESRI_SKILL_DIR から読み込む。"""
import os, sys
sys.path.insert(0, os.environ.get("ESRI_SKILL_DIR", "."))
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..") + "/"
from scripts.esri_data import *
import pandas as pd, matplotlib.pyplot as plt
s6=get_kakuhou_table("s6")
T=lambda i: s6.iloc[i].xs("合計",level="sector").astype(float)
S=lambda i,sec: s6.iloc[i].xs(sec,level="sector").astype(float)
gdp=kakuhou_row(get_kakuhou_table("ffm1n","実数"),"国内総生産").astype(float)
# 一般政府内の移転（経常・資本）は受取・支払の両方から除いて連結する
rev = T(0)+T(7)+T(22)+T(25)+(T(30)-T(32))+(T(60)-T(61))
exp_ = T(6)+T(15)+T(36)+(T(40)-T(42))+(T(52)-T(21))+(T(65)-T(66))+T(70)+T(72)+T(73)
nl=T(74)
# 一時的な資本移転: 1998・2008年度は中央政府、2005年度は社会保障基金の「居住者に対する資本移転（支払）」の前年度からの増分
c=S(67,"中央政府"); ss=S(67,"社会保障基金")
one=pd.Series(0.0,index=nl.index)
one[1998]=c[1998]-c[1997]; one[2008]=c[2008]-c[2007]; one[2005]=ss[2005]-ss[2004]
print(one[one!=0])
d=pd.DataFrame({"収入":rev/gdp*100,"支出":exp_/gdp*100,"支出_調整後":(exp_-one)/gdp*100,
 "財政収支":nl/gdp*100,"財政収支_調整後":(nl+one)/gdp*100,"一時的資本移転_10億円":one}).loc[1994:]
d.round(2).to_csv(OUT+"06_data.csv",encoding="utf-8-sig"); print(d.loc[[1997,1998,1999,2004,2005,2006,2007,2008,2009]].round(2))
setup_japanese_font()
fig,ax=plt.subplots(3,1,figsize=(9,11),sharex=True)
ax[0].plot(d.index,d["財政収支_調整後"],"o-",ms=3,color="tab:red",label="調整後")
ax[0].plot(d.index,d["財政収支"],"--",color="tab:red",alpha=.45,label="公表値")
ax[0].axhline(0,color="k",lw=.8); ax[0].set_title("一般政府 財政収支（純貸出/純借入、対名目GDP比, %）")
ax[1].plot(d.index,d["収入"],"o-",ms=3,color="tab:blue",label="収入（調整なし）"); ax[1].set_title("一般政府 収入（対名目GDP比, %）")
ax[2].plot(d.index,d["支出_調整後"],"o-",ms=3,color="tab:green",label="調整後")
ax[2].plot(d.index,d["支出"],"--",color="tab:green",alpha=.45,label="公表値ベース")
ax[2].set_title("一般政府 支出（対名目GDP比, %）")
for y in [1998,2005,2008]:
    for a in (ax[0],ax[2]): a.axvline(y,color="gray",lw=.6,ls=":")
for a in ax: a.grid(alpha=.3); a.legend(loc="best",fontsize=9); a.set_ylabel("%")
ax[-1].set_xlabel("年度")
fig.text(.01,.005,"調整: 1998・2008年度の中央政府、2005年度の社会保障基金の「居住者に対する資本移転(支払)」の前年度からの増分を一時的要因として除外。\n出所: 内閣府「2024年度国民経済計算年次推計」付表6・主要系列表(1)より作成。",fontsize=8)
plt.tight_layout(rect=(0,.035,1,1)); plt.savefig(OUT+"06_chart_revexp.png",dpi=130)
