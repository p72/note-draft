"""経済財政モデル（2026年度版）とESRI短期モデル（2022年版）の乗数比較図。

数値は両モデルの公表資料の乗数表（実質GDP、標準ケースからの乖離率、％）から転記。
ESRI短期モデルの所得税・法人税は減税ケースの符号を反転して増税に読み替えた概算。
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams["font.family"] = "Noto Sans JP"

C_EF, C_SR = "#2a78d6", "#eb6834"  # 経済財政モデル, ESRI短期モデル
INK, MUTED, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"

cases = [
    ("政府支出の拡大\n（実質GDPの1％、継続）", [1.08, 0.96, 0.75], [1.08, 1.11, 1.04]),
    ("個人所得税の増税\n（名目GDPの1％）", [-0.64, -0.56, -0.43], [-0.21, -0.33, -0.32]),
    ("法人税の増税\n（名目GDPの1％）", [-0.24, -0.38, -0.45], [-0.35, -0.59, -0.52]),
    ("消費税率の引き上げ\n（1％ポイント）", [-0.27, -0.21, -0.17], [-0.22, -0.21, -0.19]),
    ("短期金利の引き上げ\n（1％ポイント、継続）", [-0.26, -0.35, -0.36], [-0.33, -1.01, -1.20]),
    ("原油価格の上昇\n（20％）", [-0.23, -0.21, -0.20], [-0.08, -0.13, -0.16]),
]

fig, axes = plt.subplots(3, 2, figsize=(8, 10.5), sharey=True, facecolor=SURF)
x = np.arange(3)
w = 0.36
for ax, (title, ef, sr) in zip(axes.flat, cases):
    ax.set_facecolor(SURF)
    for off, vals, col in [(-w / 2 - 0.01, ef, C_EF), (w / 2 + 0.01, sr, C_SR)]:
        ax.bar(x + off, vals, w, color=col, edgecolor=SURF, linewidth=1)
        for xi, v in zip(x + off, vals):
            ax.text(xi, v + (0.04 if v >= 0 else -0.04), f"{v:+.2f}", ha="center",
                    va="bottom" if v >= 0 else "top", fontsize=8, color=INK)
    ax.axhline(0, color=MUTED, lw=0.8)
    ax.set_title(title, fontsize=10.5, color=INK, loc="left")
    ax.set_xticks(x, ["1年目", "2年目", "3年目"], fontsize=9, color=MUTED)
    ax.tick_params(axis="y", labelsize=8.5, colors=MUTED, length=0)
    ax.tick_params(axis="x", length=0)
    ax.grid(axis="y", color=GRID, lw=0.6)
    ax.set_axisbelow(True)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_ylim(-1.45, 1.45)
for ax in axes[:, 0]:
    ax.set_ylabel("実質GDPの変化（％）", fontsize=9, color=MUTED)

handles = [plt.Rectangle((0, 0), 1, 1, color=C_EF), plt.Rectangle((0, 0), 1, 1, color=C_SR)]
fig.legend(handles, ["経済財政モデル（2026年度版）", "ESRI短期モデル（2022年版）"],
           loc="upper center", ncol=2, frameon=False, fontsize=10, bbox_to_anchor=(0.5, 0.965))
fig.suptitle("同じショックに対する実質GDPの反応（標準ケースからの乖離率）",
             fontsize=13, color=INK, y=0.995)
fig.text(0.01, 0.012,
         "注：ESRI短期モデルの所得税・法人税は減税ケースの符号を反転した概算。政府支出はESRI短期モデルでは公共投資。\n"
         "出典：内閣府「経済財政モデル（2026年度版）資料集」、酒巻他（2022）ESRI Research Note No.72",
         fontsize=7.5, color=MUTED)
plt.tight_layout(rect=[0, 0.035, 1, 0.94], h_pad=2.2)
plt.savefig("../01_chart_multipliers.png", dpi=150, facecolor=SURF)
