"""図1〜図3の作図。"""
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
plt.rcParams["font.family"] = "Noto Sans CJK JP"
w = pd.read_csv("weekly.csv", index_col=0, parse_dates=True)
x = pd.read_csv("monthly.csv", index_col=0, parse_dates=True)
dec = pd.read_csv("decomposition.csv"); dec = dec[dec.spec == "基本"].reset_index(drop=True)
TAKAICHI = pd.Timestamp("2025-10-21")

# 図1
fig, ax = plt.subplots(2, 1, figsize=(9, 8), sharex=True)
ax[0].plot(w.index, w.usdjpy, label="ドル円（実績）", color="tab:blue")
ax[0].plot(w.index, np.exp(w.fit / 100), label="日米2年金利差モデルの当てはめ値・予測値", color="tab:orange", ls="--")
ax[0].axvspan(pd.Timestamp("2022-01-01"), pd.Timestamp("2025-04-30"), color="gray", alpha=.1, label="推計期間")
ax[0].axvline(TAKAICHI, color="k", lw=.8); ax[0].text(TAKAICHI + pd.Timedelta(days=7), 115, "高市政権発足", fontsize=9)
ax[0].set_ylabel("円/ドル"); ax[0].legend(loc="upper left"); ax[0].set_title("ドル円の実績と金利差モデル（週次）")
ax[1].plot(w.index, w.gap, color="tab:red", label="乖離（実績−予測値、対数ポイント）")
a2 = ax[1].twinx(); a2.plot(w.index, w.slope, color="tab:green", label="超長期カーブの傾き：国債30年−2年（右、%pt）")
ax[1].set_ylabel("対数ポイント"); a2.set_ylabel("%pt")
h1, l1 = ax[1].get_legend_handles_labels(); h2, l2 = a2.get_legend_handles_labels()
ax[1].legend(h1 + h2, l1 + l2, loc="upper left", fontsize=9); ax[1].set_title("金利差で説明できない円安と超長期カーブの傾き")
fig.text(.01, .005, "出典：FRED（DGS2）、財務省「国債金利情報」、Yahoo Finance（JPY=X）より作成。金曜終値", fontsize=8)
fig.tight_layout(rect=(0, .02, 1, 1)); fig.savefig("../01_chart_gap.png", dpi=140)

# 図2
lab = ["物価調整後\n2年金利差", "超長期カーブ\nの傾き", "デジタル\n関連収支", "直接投資\n（再投資除く）", "原油価格", "残差"]
key = ["rsp2", "slope", "dig", "fdi", "oil", "resid"]
col = ["tab:gray", "tab:green", "tab:purple", "tab:gray", "k", "tab:red"]
def bars(ax, r, title):
    v = [r[k] for k in key]; ax.bar(lab, v, color=col); ax.axhline(0, color="k", lw=.6)
    lo, hi = min(v + [0]), max(v + [0]); pad = (hi - lo) * .06
    for i, t in enumerate(v): ax.text(i, t + (pad * .3 if t >= 0 else -pad), f"{t:+.1f}", ha="center", fontsize=9)
    ax.set_ylim(lo - pad * 2, hi + pad * 2); ax.set_ylabel("円安への寄与（対数ポイント）"); ax.set_title(title); ax.tick_params(axis="x", labelsize=8)
fig, ax = plt.subplots(1, 2, figsize=(13, 5), gridspec_kw={"width_ratios": [1.4, 1]})
ax[0].plot(x.index, x.fx, label="ドル円（月平均）", color="tab:blue")
ax[0].plot(x.index, np.exp(x.fit / 100), label="モデルの当てはめ値", color="tab:orange", ls="--")
ax[0].axvline(TAKAICHI, color="k", lw=.8); ax[0].text(TAKAICHI - pd.Timedelta(days=400), 102, "高市政権発足→", fontsize=9)
ax[0].set_ylabel("円/ドル"); ax[0].legend(loc="upper left", fontsize=9); ax[0].set_title("ドル円とモデルの当てはめ値（2015年1月〜2026年9月）")
r = dec.iloc[0]; bars(ax[1], r, f"2021年12月→2026年9月　円安{r.actual_logpt:.1f}対数ポイントの分解")
fig.text(.01, .005, "出典：日本銀行「国際収支統計」、財務省「国債金利情報」、総務省「消費者物価指数」、FRED（EXJPUS、DGS2、CPILFESL、DCOILBRENTEU）より作成", fontsize=8)
fig.tight_layout(rect=(0, .03, 1, 1)); fig.savefig("../01_chart_decomp.png", dpi=140)

# 図3
xs = x.loc["2024-01":]
fig, ax = plt.subplots(1, 2, figsize=(13, 5), gridspec_kw={"width_ratios": [1.3, 1]})
ax[0].plot(xs.index, xs.fx, color="tab:blue", label="ドル円（左、円/ドル）")
a2 = ax[0].twinx(); a2.plot(xs.index, xs.brent, color="k", ls="--", label="ブレント原油（右、ドル/バレル）")
for d, t, yy in [(pd.Timestamp("2025-10-01"), "高市政権", 161.8), (pd.Timestamp("2026-03-01"), "イラン戦争", 143)]:
    ax[0].axvline(d, color="gray", lw=.8); ax[0].text(d + pd.Timedelta(days=10), yy, t, fontsize=9)
h1, l1 = ax[0].get_legend_handles_labels(); h2, l2 = a2.get_legend_handles_labels()
ax[0].legend(h1 + h2, l1 + l2, loc="upper left", fontsize=9); ax[0].set_title("ドル円と原油価格（月平均）")
r = dec.iloc[1]; bars(ax[1], r, f"2025年9月→2026年9月　円安{r.actual_logpt:.1f}対数ポイントの分解")
fig.text(.01, .005, "出典：図2と同じ", fontsize=8)
fig.tight_layout(rect=(0, .03, 1, 1)); fig.savefig("../01_chart_oil.png", dpi=140)

# 図4：イベントスタディ（米金利で説明できない円の動きの累積と、国債30年金利）
dd = pd.read_csv("daily.csv", index_col=0, parse_dates=True).loc["2025-07-01":]
ev = pd.read_csv("events.csv", parse_dates=["date"])
fig, ax = plt.subplots(figsize=(11, 6.2))
ax.plot(dd.index, dd.ab.cumsum(), color="tab:red", label="米金利で説明できない円の動きの累積（左、対数ポイント、上が円安）")
a2 = ax.twinx(); a2.plot(dd.index, dd.jp30.cumsum() * 100, color="tab:green", label="国債30年金利の累積変化（右、bp）")
for _, e in ev.iterrows():
    c = "tab:orange" if e.kind == "拡張" else "tab:blue"; ls = ":" if e.intervention else "--"
    ax.axvline(e.date, color=c, ls=ls, lw=1)
ax.axvspan(pd.Timestamp("2026-06-30"), pd.Timestamp("2026-07-09"), color="tab:orange", alpha=.12)
ax.text(pd.Timestamp("2026-06-08"), ax.get_ylim()[1] - .6, "骨太ショック", fontsize=9)
for dday in pd.to_datetime(["2026-07-30", "2026-07-31", "2026-08-03"]):
    ax.axvspan(dday, dday + pd.Timedelta(days=1), color="gray", alpha=.3)
ax.axvline(pd.Timestamp("2026-02-27"), color="k", lw=.6); ax.text(pd.Timestamp("2026-03-03"), ax.get_ylim()[0] + .3, "イラン戦争", fontsize=9)
ax.set_ylabel("対数ポイント"); a2.set_ylabel("bp")
h1, l1 = ax.get_legend_handles_labels(); h2, l2 = a2.get_legend_handles_labels()
from matplotlib.lines import Line2D
h3 = [Line2D([0], [0], color="tab:orange", ls="--"), Line2D([0], [0], color="tab:blue", ls="--"), plt.Rectangle((0, 0), 1, 1, color="gray", alpha=.3)]
ax.legend(h1 + h2 + h3, l1 + l2 + ["財政拡張のニュース", "財政規律のニュース", "為替介入"], loc="upper center",
          bbox_to_anchor=(0.5, -0.08), ncol=3, fontsize=8, frameon=False)
ax.set_title("財政ニュースの日の円と超長期国債（2025年7月〜、東京17時・東京終値）")
fig.text(.01, .005, "出典：日本銀行「外国為替市況」（東京17時）、財務省「国債金利情報」、FRED（DGS2、DGS10）より作成。2025年7月1日を0とした累積", fontsize=8)
fig.tight_layout(rect=(0, .03, 1, 1)); fig.savefig("../01_chart_event.png", dpi=140)
