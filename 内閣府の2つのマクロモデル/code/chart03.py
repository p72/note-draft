"""経済財政モデル（2026年度版）の Python 再現と公表乗数表の比較図（03 の記事用）.

数値は p72/cao-economic-fiscal-model の output/multipliers_port.csv（財政ブロック移植版、calibrated）を
03_multipliers_port.csv として同じフォルダに置いたもの。8ケース×1〜5年目の、標準ケースからの乖離。
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

plt.rcParams["font.family"] = "Noto Sans JP"
INK, MUTED, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "03_chart_multipliers.png"

CASES = {1: "公共投資（1年）", 2: "公共投資（継続）", 3: "法人税", 4: "所得税", 5: "消費税",
         6: "ＴＦＰ", 7: "原油", 8: "金利"}
COLORS = ["#2a78d6", "#7aa9e6", "#eb6834", "#f2a07a", "#1baf7a", "#8a5cc2", "#b8892d", "#52514e"]
PANELS = [("M_GDP", "実質ＧＤＰ（％）"), ("M_CPIG", "消費者物価（％）"),
          ("M_PBGAGDPV", "基礎的財政収支（対ＧＤＰ比、％pt）"), ("Z_DEBTAGDP", "公債等残高（対ＧＤＰ比、％pt）")]

df = pd.read_csv(HERE / "03_multipliers_port.csv")
fig, axes = plt.subplots(2, 2, figsize=(8.6, 8.4), facecolor=SURF)
for ax, (v, title) in zip(axes.flat, PANELS):
    ax.set_facecolor(SURF)
    x = df[df["var"] == v]
    lo = min(x["model"].min(), x["published"].min())
    hi = max(x["model"].max(), x["published"].max())
    pad = (hi - lo) * 0.08
    ax.plot([lo - pad, hi + pad], [lo - pad, hi + pad], color=MUTED, lw=0.8, ls="--")
    for (c, g), col in zip(x.groupby("case"), COLORS):
        ax.scatter(g["published"], g["model"], s=22, color=col, label=CASES[c], zorder=3)
    ax.set_title(title, fontsize=10.5, color=INK, loc="left")
    ax.set_xlabel("公表乗数表", fontsize=9, color=MUTED)
    ax.set_ylabel("再現モデル", fontsize=9, color=MUTED)
    ax.grid(color=GRID, lw=0.6)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.tick_params(colors=MUTED, labelsize=8.5)
axes[0, 0].legend(fontsize=7.5, frameon=False, loc="upper left", ncol=2)
fig.suptitle("公表乗数表と再現モデルの比較（8ケース×1〜5年目、標準ケースからの乖離）",
             fontsize=11.5, color=INK, x=0.02, ha="left")
fig.text(0.02, 0.012, "資料: 内閣府「経済財政モデル（2026年度版）資料集」の主要乗数表。再現モデルは財政ブロック移植版（calibrated）。\n"
         "点線の上にあれば公表値と一致。", fontsize=7.5, color=MUTED)
fig.tight_layout(rect=(0, 0.04, 1, 0.95))
fig.savefig(OUT, dpi=150, facecolor=SURF)
print(OUT)
