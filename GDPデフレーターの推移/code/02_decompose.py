"""02_交易条件と単位労働コスト・単位利潤：GDPデフレーターの分解

データ：内閣府ESRI
- 四半期別GDP速報 2026年7-9月期1次速報（gaku-mg, gaku-jg, def-qg, def-qk, gaku-jk, kshotoku-q）
- 2024年度国民経済計算年次推計（2024a1_jp.xlsx, 2024ffm1rn_jp.xlsx）
ヘルパーは Claude の esri-data スキル（scripts/esri_data.py）を使う。
使い方：python3 02_decompose.py <esri-data スキルのディレクトリ> <出力ディレクトリ>
"""
import sys, os
sys.path.insert(0, sys.argv[1] if len(sys.argv) > 1 else ".")
OUT = sys.argv[2] if len(sys.argv) > 2 else ".."
from scripts.esri_data import (get_qe_raw, parse_qe_column, get_kakuhou_table, kakuhou_row,
                               setup_japanese_font)
import pandas as pd, matplotlib.pyplot as plt, matplotlib.dates as mdates

def col(series, c):
    return parse_qe_column(get_qe_raw(series=series), c).set_index("date")["value"]

# ---- 四半期（原系列）----
q = pd.DataFrame(dict(
    N=col("gaku-mg", "GDP"), R=col("gaku-jg", "GDP"),
    ND=col("gaku-mg", "国内需要"), NX=col("gaku-mg", "輸出"), NM=col("gaku-mg", "輸入"),
    PD=col("def-qg", "国内需要"), PX=col("def-qg", "輸出"), PM=col("def-qg", "輸入"),
    PG=col("def-qg", "GDP"),
    W=parse_qe_column(get_qe_raw(series="kshotoku-q"), 1).set_index("date")["value"],  # 雇用者報酬 名目 原系列
)).dropna()
L = q.shift(4)
q["g_PG"] = (q.PG / L.PG - 1) * 100
# 支出面：前年同期の名目シェアで加重
q["c_D"] = L.ND / L.N * (q.PD / L.PD - 1) * 100
q["c_X"] = L.NX / L.N * (q.PX / L.PX - 1) * 100
q["c_M"] = -L.NM / L.N * (q.PM / L.PM - 1) * 100
q["c_res"] = q.g_PG - q.c_D - q.c_X - q.c_M
# 分配面：P = W/R + (N-W)/R
P0 = L.N / L.R
q["g_P"] = (q.N / q.R / P0 - 1) * 100
q["c_ULC"] = (q.W / q.R - L.W / L.R) / P0 * 100
q["c_OTH"] = ((q.N - q.W) / q.R - (L.N - L.W) / L.R) / P0 * 100
q["ULC_g"] = (q.W / q.R / (L.W / L.R) - 1) * 100
q["W_g"] = (q.W / L.W - 1) * 100
q["R_g"] = (q.R / L.R - 1) * 100
# 交易条件（季調）と交易利得
PXk, PMk = col("def-qk", "輸出"), col("def-qk", "輸入")
q["PXk"], q["PMk"] = PXk, PMk
q["TOT"] = PXk / PMk * 100
q["TG_pct"] = col("gaku-jk", "交易利得") / col("gaku-jk", "GDP") * 100
q.to_csv("decomp_quarterly.csv")

# ---- 年度（確報）----
a = get_kakuhou_table("a1", "年度"); r = get_kakuhou_table("ffm1rn", "実数")
d = pd.DataFrame({k: kakuhou_row(a, v) for k, v in {
    "W": "雇用者報酬", "OS": "営業余剰・混合所得", "D": "固定資本減耗",
    "T": "生産・輸入品に課される税", "S": "補助金", "SD": "統計上の不突合"}.items()})
d["N"] = kakuhou_row(a, "国内総生産"); d["R"] = kakuhou_row(r, "国内総生産")
d["TS"] = d["T"] - d["S"]
d0 = d.shift(1); P0a = d0.N / d0.R
fy = pd.DataFrame({"GDPデフレーター": (d.N / d.R / P0a - 1) * 100})
names = {"W": "雇用者報酬（単位労働コスト）", "OS": "営業余剰・混合所得（単位利潤）",
         "D": "固定資本減耗", "TS": "純間接税（税−補助金）", "SD": "統計上の不突合"}
for k, v in names.items():
    fy[v] = (d[k] / d.R - d0[k] / d0.R) / P0a * 100
fy.to_csv("decomp_fiscalyear.csv")

# ---- 作図 ----
setup_japanese_font()
s = q[q.index >= "2018-01-01"]; W = 70
src = "出所：内閣府「2026年7-9月期四半期別GDP速報（1次速報）」より作成"

def stack(ax, df, cols, colors, labels):
    pos = 0 * df[cols[0]]; neg = 0 * df[cols[0]]
    for c, co, lb in zip(cols, colors, labels):
        v = df[c]; b = v.where(v > 0, 0); n = v.where(v < 0, 0)
        ax.bar(df.index, b, W, bottom=pos, color=co, label=lb); pos = pos + b
        ax.bar(df.index, n, W, bottom=neg, color=co); neg = neg + n

# 図1 交易条件
fig, ax = plt.subplots(2, 1, figsize=(9, 8), sharex=True, gridspec_kw={"height_ratios": [3, 2]})
ax[0].plot(s.index, s.PXk, lw=2, label="輸出デフレーター")
ax[0].plot(s.index, s.PMk, lw=2, c="C3", label="輸入デフレーター")
a2 = ax[0].twinx(); a2.plot(s.index, s.TOT, c="k", lw=2.2, ls="--", label="交易条件（右軸）")
ax[0].set_title("輸出・輸入デフレーターと交易条件（季節調整系列、2020年=100）")
h1, l1 = ax[0].get_legend_handles_labels(); h2, l2 = a2.get_legend_handles_labels()
ax[0].legend(h1 + h2, l1 + l2, loc="upper left", fontsize=9); ax[0].grid(alpha=.3)
a2.set_ylim(75, 110)
ax[1].bar(s.index, s.TG_pct, W, color=["C2" if v > 0 else "C3" for v in s.TG_pct])
ax[1].axhline(0, c="k", lw=.8); ax[1].set_title("交易利得・損失（実質GDP比、%）"); ax[1].grid(alpha=.3)
fig.text(0.01, 0.005, src + "。交易条件＝輸出デフレーター÷輸入デフレーター×100", fontsize=8)
plt.tight_layout(rect=[0, 0.02, 1, 1]); plt.savefig(f"{OUT}/02_chart_tot.png", dpi=130); plt.close()

# 図2 支出面の分解
fig, ax = plt.subplots(figsize=(9, 5.2))
stack(ax, s, ["c_D", "c_X", "c_M", "c_res"], ["C1", "C0", "C3", "lightgray"],
      ["国内需要デフレーター", "輸出デフレーター", "輸入デフレーター（控除）", "その他（連鎖の誤差）"])
ax.plot(s.index, s.g_PG, "ko-", ms=3, lw=1.6, label="GDPデフレーター")
ax.axhline(0, c="k", lw=.8); ax.grid(alpha=.3); ax.legend(fontsize=9, ncol=2, loc="upper left")
ax.set_title("GDPデフレーター前年同期比の支出面からの寄与度分解（%ポイント、原系列）")
fig.text(0.01, 0.005, src, fontsize=8)
plt.tight_layout(rect=[0, 0.02, 1, 1]); plt.savefig(f"{OUT}/02_chart_expenditure.png", dpi=130); plt.close()

# 図3 分配面の分解（四半期）
fig, ax = plt.subplots(figsize=(9, 5.2))
stack(ax, s, ["c_ULC", "c_OTH"], ["C0", "C1"],
      ["単位労働コスト（雇用者報酬÷実質GDP）", "雇用者報酬以外（単位利潤など）"])
ax.plot(s.index, s.g_P, "ko-", ms=3, lw=1.6, label="GDPデフレーター")
ax.axhline(0, c="k", lw=.8); ax.grid(alpha=.3); ax.legend(fontsize=9, loc="upper left")
ax.set_title("GDPデフレーター前年同期比の分配面からの寄与度分解（%ポイント、原系列）"); ax.set_ylim(-3.3, 6.8)
fig.text(0.01, 0.005, src, fontsize=8)
plt.tight_layout(rect=[0, 0.02, 1, 1]); plt.savefig(f"{OUT}/02_chart_income_q.png", dpi=130); plt.close()

# 図4 分配面の分解（年度、確報）
f = fy.loc[2018:2024]
fig, ax = plt.subplots(figsize=(9, 5.2))
x = f.index.astype(str) + "年度"
cols = list(names.values()); colors = ["C0", "C1", "C7", "C8", "lightgray"]
pos = 0 * f[cols[0]]; neg = 0 * f[cols[0]]
for c, co in zip(cols, colors):
    v = f[c]; b = v.where(v > 0, 0); n = v.where(v < 0, 0)
    ax.bar(x, b, .6, bottom=pos, color=co, label=c); pos = pos + b
    ax.bar(x, n, .6, bottom=neg, color=co); neg = neg + n
ax.plot(x, f["GDPデフレーター"], "ko-", lw=1.6, label="GDPデフレーター")
for xi, v in zip(x, f["GDPデフレーター"]):
    ax.annotate(f"{v:.1f}", (xi, v), textcoords="offset points", xytext=(0, 7), ha="center", fontsize=9)
ax.axhline(0, c="k", lw=.8); ax.grid(alpha=.3, axis="y"); ax.legend(fontsize=8.5, loc="upper left")
ax.set_title("GDPデフレーター変化率の分配面からの寄与度分解（年度、%ポイント）"); ax.set_ylim(-3.0, 5.4)
fig.text(0.01, 0.005, "出所：内閣府「2024年度国民経済計算年次推計」より作成", fontsize=8)
plt.tight_layout(rect=[0, 0.02, 1, 1]); plt.savefig(f"{OUT}/02_chart_income_fy.png", dpi=130); plt.close()
print(fy.loc[2018:2024].round(2).to_string())
