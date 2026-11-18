"""01_2018年以降のGDPデフレーター：データ取得と作図

内閣府ESRI「四半期別GDP速報」（2026年7-9月期1次速報）のCSVを直接取得する。
- rdef-qg2631.csv : デフレーター前年同期比（原系列）
- def-qk2631.csv  : デフレーター水準（季節調整系列、2020年=100）
- rdef-fy2631.csv : デフレーター年度変化率
ヘルパーは Claude の esri-data スキル（scripts/esri_data.py）を使う。
"""
import sys
sys.path.insert(0, sys.argv[1] if len(sys.argv) > 1 else ".")  # esri-data スキルのディレクトリ
from scripts.esri_data import get_qe_df, get_qe_raw, parse_qe_column, setup_japanese_font
import matplotlib.pyplot as plt

cols = {"GDP": "GDP", "消費": "家計最終消費支出", "設備": "民間企業設備", "政府": "政府最終消費支出",
        "輸出": "輸出", "輸入": "輸入", "内需": "国内需要"}
y = get_qe_df("rdef-qg", cols=cols)
k = get_qe_df("def-qk", cols=cols)
y.to_csv("deflator_yoy.csv"); k.to_csv("deflator_level.csv")
for c in ["GDP", "国内需要"]:
    print(c, parse_qe_column(get_qe_raw(series="rdef-fy"), c).tail(9), sep="\n")

setup_japanese_font()
y = y[y.date >= "2018-01-01"]; k = k[k.date >= "2018-01-01"]
fig, ax = plt.subplots(2, 1, figsize=(9, 8), sharex=True)
ax[0].plot(k.date, k.GDP, lw=2.2, label="GDPデフレーター")
ax[0].plot(k.date, k["内需"], lw=2, label="国内需要デフレーター")
ax[0].axhline(100, c="gray", lw=.8); ax[0].set_title("水準（季節調整系列、2020年=100）")
ax[0].legend(); ax[0].grid(alpha=.3)
ax[1].bar(y.date, y.GDP, width=70, color="C0", alpha=.8, label="GDPデフレーター")
ax[1].plot(y.date, y["内需"], c="C1", lw=2, marker="o", ms=3, label="国内需要デフレーター")
ax[1].plot(y.date, y["輸入"], c="C3", lw=1.2, ls="--", label="輸入デフレーター（参考）")
ax[1].axhline(0, c="k", lw=.8); ax[1].set_title("前年同期比（%、原系列）")
ax[1].legend(fontsize=9); ax[1].grid(alpha=.3)
fig.suptitle("GDPデフレーターの推移（2018年1-3月期〜2026年7-9月期）", fontsize=13)
fig.text(0.01, 0.005, "出所：内閣府「2026年7-9月期四半期別GDP速報（1次速報）」", fontsize=8)
plt.tight_layout(rect=[0, 0.02, 1, 1]); plt.savefig("../01_chart_deflator.png", dpi=130)
