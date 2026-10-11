"""G7の時間当たり労働生産性（OECD Productivity Database）を取得して作図する。

データ: OECD.SDD.TPS,DSD_PDB@DF_PDB,2.0
  MEASURE=GDPHRS（就業1時間当たりGDP）, ACTIVITY=_T, UNIT_MEASURE=USD_PPP_H, TRANSFORMATION=N
  PRICE_BASE=V  : 当年価格・当年購買力平価
  PRICE_BASE=LR : 固定価格・固定購買力平価（実質）
"""
from io import StringIO

import matplotlib
import pandas as pd
import requests

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib_fontja  # noqa: F401  日本語フォント

URL = (
    "https://sdmx.oecd.org/public/rest/data/OECD.SDD.TPS,DSD_PDB@DF_PDB,2.0/"
    "JPN+GBR+USA+DEU+FRA+ITA+CAN.A.GDPHRS._T.USD_PPP_H..N._Z."
    "?startPeriod=1990&format=csvfile&dimensionAtObservation=AllDimensions"
)
NAME = {"JPN": "日本", "GBR": "英国", "USA": "米国", "DEU": "ドイツ",
        "FRA": "フランス", "ITA": "イタリア", "CAN": "カナダ"}
COL = {"JPN": "#D62728", "GBR": "#1F4E9C"}
SRC = "出所：OECD Productivity Database（DSD_PDB@DF_PDB, GDP per hour worked）"

df = pd.read_csv(StringIO(requests.get(URL, timeout=120).text))
v = df[df.PRICE_BASE == "V"].pivot(index="TIME_PERIOD", columns="REF_AREA", values="OBS_VALUE")
r = df[df.PRICE_BASE == "LR"].pivot(index="TIME_PERIOD", columns="REF_AREA", values="OBS_VALUE")
ri = r / r.loc[1995] * 100

# 図1：G7の水準と実質の伸び
fig, ax = plt.subplots(1, 2, figsize=(14, 6))
for a, d, title in [(ax[0], v, "時間当たり労働生産性（名目・購買力平価換算, USドル）"),
                    (ax[1], ri, "実質の伸び（1995年=100）")]:
    ends = {}
    for c in ["USA", "DEU", "FRA", "ITA", "CAN", "GBR", "JPN"]:
        s = d[c].dropna()
        hl = c in COL
        a.plot(s.index, s.values, color=COL.get(c, "#AAAAAA"), lw=2.6 if hl else 1.3, zorder=3 if hl else 1)
        ends[c] = s.iloc[-1]
    ys = []
    for c in sorted(ends, key=lambda k: -ends[k]):  # ラベルの重なりを避ける
        y = ends[c]
        if ys and ys[-1] - y < 4.5:
            y = ys[-1] - 4.5
        ys.append(y)
        a.text(2025.6, y, f"{NAME[c]} {ends[c]:.0f}", va="center", fontsize=10, color=COL.get(c, "#666"))
    a.set_title(title, fontsize=12)
    a.grid(alpha=.3)
    a.set_xlim(1990, 2031)
    a.spines[["top", "right"]].set_visible(False)
ax[1].axhline(100, color="#999", lw=.8)
fig.suptitle("G7の時間当たり労働生産性の推移（1990〜2025年）", fontsize=15)
fig.text(.01, .01, SRC + "。左は当年価格・当年PPP、右は固定価格・固定PPPの実質系列を1995年=100で指数化。",
         fontsize=9, color="#555")
plt.tight_layout(rect=[0, .03, 1, .95])
plt.savefig("01_chart_g7.png", dpi=150)

# 図2：日本÷英国の比率（名目PPPと実質）
fig, a = plt.subplots(figsize=(10, 5.5))
nv = v.JPN / v.GBR
nr = r.JPN / r.GBR
a.plot(nv.index, nv.values, color="#D62728", lw=2.4)
a.plot(nr.index, nr.values, color="#1F4E9C", lw=2.4)
a.text(2025.5, nv.iloc[-1] - 0.012, f"当年価格・当年PPP {nv.iloc[-1]:.2f}", color="#D62728", fontsize=10, va="center")
a.text(2025.5, nr.iloc[-1] + 0.012, f"固定価格・固定PPP {nr.iloc[-1]:.2f}", color="#1F4E9C", fontsize=10, va="center")
for y in [1995]:
    a.annotate(f"{nv[y]:.2f}", (y, nv[y]), xytext=(0, 8), textcoords="offset points", ha="center", color="#D62728", fontsize=9)
    a.annotate(f"{nr[y]:.2f}", (y, nr[y]), xytext=(0, -14), textcoords="offset points", ha="center", color="#1F4E9C", fontsize=9)
a.set_title("日本の時間当たり労働生産性は英国の何倍か（日本÷英国）", fontsize=13)
a.set_xlim(1990, 2033)
a.grid(alpha=.3)
a.spines[["top", "right"]].set_visible(False)
fig.text(.01, .01, SRC + "。固定PPPは2020年の購買力平価。", fontsize=9, color="#555")
plt.tight_layout(rect=[0, .03, 1, 1])
plt.savefig("01_chart_ratio.png", dpi=150)
