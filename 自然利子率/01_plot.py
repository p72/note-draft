import pandas as pd, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm

for f in fm.findSystemFonts():
    if "NotoSansCJK-Regular" in f:
        fm.fontManager.addfont(f); plt.rcParams["font.family"] = fm.FontProperties(fname=f).get_name(); break
plt.rcParams["axes.unicode_minus"] = False

BLUE, ORANGE, GRAY = "#2a78d6", "#eb6834", "#8a8a85"
out = pd.read_pickle("results.pkl"); data = pd.read_pickle("data.pkl")
base = out[(0.06, 0.10)]
sm = base["smooth"]; t = sm.index.to_timestamp()
lo = pd.concat([v["smooth"].rstar for v in out.values()], axis=1).min(axis=1)
hi = pd.concat([v["smooth"].rstar for v in out.values()], axis=1).max(axis=1)

fig, axes = plt.subplots(3, 1, figsize=(10, 11), sharex=True,
                         gridspec_kw={"height_ratios": [3, 1.6, 1.6]})

ax = axes[0]
ax.fill_between(t, sm.rstar - 1.645 * sm.rstar_se, sm.rstar + 1.645 * sm.rstar_se, color=BLUE, alpha=0.10, lw=0,
                label="90%信頼区間")
ax.fill_between(t, lo, hi, color=BLUE, alpha=0.30, lw=0, label="パラメータ設定の違いによる幅")
ax.plot(t, sm.rstar, color=BLUE, lw=2, label="自然利子率 r*（本推計・両側）")
ax.plot(data.index.to_timestamp(), data.r, color=GRAY, lw=1.2, label="実質コールレート（事前）")
bq = pd.Period("2025Q3").to_timestamp()
ax.errorbar([bq], [-0.2], yerr=[[0.7], [0.7]], fmt="none", ecolor=ORANGE, elinewidth=4, capsize=6)
ax.annotate("日銀推計レンジ\n(-0.9〜+0.5%,\n2025年7-9月期)", (bq, 0.5), xytext=(pd.Timestamp("2019-01-01"), 4.6),
            color="#333", fontsize=9, arrowprops=dict(arrowstyle="-", color=ORANGE))
ax.axhline(0, color="#bbb", lw=0.8)
ax.set_ylim(-5, 6); ax.set_ylabel("%（年率）")
ax.set_title("自然利子率（r*）の推移：HLW型モデルの簡易推計", loc="left", fontsize=13)
ax.legend(loc="lower left", fontsize=9, frameon=False, ncol=2)
ax.text(sm.index[-1].to_timestamp(), sm.rstar.iloc[-1] + 0.3, f"{sm.rstar.iloc[-1]:.1f}%", color=BLUE, fontsize=10)

ax = axes[1]
ax.plot(t, sm.g, color=BLUE, lw=2)
ax.set_ylabel("%（年率）"); ax.set_ylim(0, 1.5)
ax.set_title("潜在成長率 g（本推計・両側）", loc="left", fontsize=11)
ax.text(t[-1], sm.g.iloc[-1] + 0.08, f"{sm.g.iloc[-1]:.1f}%", color=BLUE, fontsize=10)

ax = axes[2]
gap = base["gap"]; tg = gap.index.to_timestamp()
ax.bar(tg, gap, width=70, color=np.where(gap >= 0, BLUE, ORANGE))
ax.axhline(0, color="#bbb", lw=0.8)
ax.set_ylabel("%"); ax.set_ylim(-9, 5)
ax.set_title("需給ギャップ（本推計・両側、2020年4-6月期は-8%前後）", loc="left", fontsize=11)

for a in axes:
    a.grid(axis="y", color="#e6e6e3", lw=0.8); a.spines[["top", "right"]].set_visible(False)
fig.text(0.01, 0.005, "出所：内閣府ESRI（QE 2026年4-6月期2次速報 実質GDP）、総務省（e-Stat CPI 生鮮食品を除く総合）、"
         "日本銀行（無担保コールO/N 月平均）より推計。\n注：r* = 潜在成長率 + その他要因 z。消費税率引き上げの影響を近似除去。"
         "IS・PC曲線の傾き等に緩い事前分布を置いたMAP推定。", fontsize=8, color="#555")
plt.tight_layout(rect=[0, 0.04, 1, 1])
plt.savefig("01_chart_rstar.png", dpi=150, facecolor="white")
