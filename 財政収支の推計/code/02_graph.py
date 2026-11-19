#!/usr/bin/env python3
"""財政は過去30年で最もいい：作図コード
データ: IMF World Economic Outlook (Oct 2026) DataMapper API
  GGXCNL_NGDP 一般政府 純貸出/純借入 (%GDP, SNA/GFSベース)
  GGXWDG_NGDP 一般政府 総債務 (%GDP)
  日銀 資金循環統計 (DLRI 星野レポート経由の公表値, 時価ベース)
出力: SVG (note-draft 掲載用) + PNG (確認用, work内のみ)
"""
import json, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

FONT = os.path.expanduser("~/workspace/tools/fonts/NotoSansCJKjp-Regular.otf")
fm.fontManager.addfont(FONT)
plt.style.use("default")
plt.rcParams["font.family"] = "Noto Sans CJK JP"
plt.rcParams["axes.facecolor"] = "white"
plt.rcParams["figure.facecolor"] = "white"
plt.rcParams["svg.fonttype"] = "path"

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "staging", "財政収支の推計")
os.makedirs(OUT, exist_ok=True)

def load(ind):
    d = json.load(open(os.path.join(HERE, f"imf_{ind}.json")))
    v = {int(k): x for k, x in d["values"][ind]["JPN"].items()}
    return v

nl = load("GGXCNL_NGDP")   # 財政収支
wd = load("GGXWDG_NGDP")   # 総債務

# ---------- Chart 1: SNA 財政収支 ----------
yrs = [y for y in range(1990, 2026)]
fig, ax = plt.subplots(figsize=(9.2, 5.0), dpi=150)
ax.plot(yrs, [nl[y] for y in yrs], color="#1f4e79", lw=2.2, zorder=3)
ax.axhline(0, color="#333333", lw=1.0)
ax.fill_between(yrs, [nl[y] for y in yrs], 0, where=[nl[y] < 0 for y in yrs],
                color="#c00000", alpha=0.12, interpolate=True)
ax.plot([2025], [0.2], marker="D", color="#ed7d31", ms=8, zorder=4)
ax.annotate("内閣府試算（2025年度）+0.2%\n一般政府ISバランス、1991年度以来の黒字",
            xy=(2025, 0.2), xytext=(2008.5, 1.6),
            fontsize=10.5, color="#7b3f00",
            arrowprops=dict(arrowstyle="->", color="#ed7d31"))
ax.annotate("2025年 -0.7%\n1993年以降で最良", xy=(2025, -0.7), xytext=(2015.5, -3.4),
            fontsize=11, color="#1f4e79", fontweight="bold",
            arrowprops=dict(arrowstyle="->", color="#1f4e79"))
ax.annotate("2020年 -9.0%", xy=(2020, -9.0), xytext=(2010.5, -8.6),
            fontsize=10.5, color="#555555",
            arrowprops=dict(arrowstyle="->", color="#888888"))
ax.set_xlim(1990, 2025.6); ax.set_ylim(-11, 3.2)
ax.set_ylabel("対GDP比（%）")
ax.set_title("一般政府の財政収支（SNA・純貸出／純借入、対GDP比）", fontsize=13.5, fontweight="bold")
ax.grid(axis="y", color="#dddddd", lw=0.7); ax.set_axisbelow(True)
fig.text(0.01, -0.01, "出所：IMF World Economic Outlook（2026年10月）GGXCNL_NGDP（暦年）、内閣府「中長期の経済財政に関する試算」（2026年7月、年度）",
         fontsize=8, color="#666666")
fig.tight_layout()
fig.savefig(os.path.join(OUT, "02_chart_sna_balance.svg"), bbox_inches="tight")
fig.savefig(os.path.join(HERE, "preview1.png"), bbox_inches="tight")
plt.close(fig)

# ---------- Chart 2: 総債務/GDP (IMF) ----------
fig, ax = plt.subplots(figsize=(9.2, 5.0), dpi=150)
ax.plot(yrs, [wd[y] for y in yrs], color="#1f4e79", lw=2.2, zorder=3)
ax.fill_between(yrs, [wd[y] for y in yrs], 0, color="#1f4e79", alpha=0.08)
ax.annotate("2020年 228.8%（ピーク）", xy=(2020, 228.8), xytext=(2004.5, 232),
            fontsize=10.5, color="#555555",
            arrowprops=dict(arrowstyle="->", color="#888888"))
ax.annotate("2025年 204.8%\n2010年代半ば並みまで低下", xy=(2025, 204.8), xytext=(2013.5, 176),
            fontsize=11, color="#1f4e79", fontweight="bold",
            arrowprops=dict(arrowstyle="->", color="#1f4e79"))
ax.set_xlim(1990, 2025.6); ax.set_ylim(0, 250)
ax.set_ylabel("対GDP比（%）")
ax.set_title("一般政府総債務残高（対GDP比）", fontsize=13.5, fontweight="bold")
ax.grid(axis="y", color="#dddddd", lw=0.7); ax.set_axisbelow(True)
fig.text(0.01, -0.01, "出所：IMF World Economic Outlook（2026年10月）GGXWDG_NGDP",
         fontsize=8, color="#666666")
fig.tight_layout()
fig.savefig(os.path.join(OUT, "02_chart_gross_debt.svg"), bbox_inches="tight")
fig.savefig(os.path.join(HERE, "preview2.png"), bbox_inches="tight")
plt.close(fig)

# ---------- Chart 3: FoF 債務/GDP (時価, 直近4四半期) ----------
labels = ["2025年9月末", "2025年12月末", "2026年3月末", "2026年6月末"]
total = [210.4, 207.3, 202.3, 199.3]
net = [73.8, 66.0, 60.9, 55.3]
x = range(4)
fig, ax = plt.subplots(figsize=(9.2, 5.0), dpi=150)
ax.plot(x, total, marker="o", color="#1f4e79", lw=2.2, label="総債務")
ax.plot(x, net, marker="s", color="#c00000", lw=2.2, label="純債務（債務－金融資産）")
for xi, v in zip(x, total):
    ax.annotate(f"{v:.1f}", (xi, v), textcoords="offset points", xytext=(0, 9),
                ha="center", fontsize=11, color="#1f4e79", fontweight="bold")
for xi, v in zip(x, net):
    ax.annotate(f"{v:.1f}", (xi, v), textcoords="offset points", xytext=(0, 9),
                ha="center", fontsize=11, color="#c00000", fontweight="bold")
ax.set_xticks(list(x)); ax.set_xticklabels(labels, fontsize=10.5)
ax.set_ylim(0, 235)
ax.set_ylabel("対GDP比（%）")
ax.set_title("資金循環統計の一般政府債務残高（対GDP比、時価ベース）", fontsize=13.5, fontweight="bold")
ax.legend(fontsize=10.5, frameon=False, loc="lower left")
ax.grid(axis="y", color="#dddddd", lw=0.7); ax.set_axisbelow(True)
fig.text(0.01, -0.01, "出所：日本銀行「資金循環統計」（第一生命経済研究所 星野卓也レポート 2026年3月18日・9月17日より転記）",
         fontsize=8, color="#666666")
fig.tight_layout()
fig.savefig(os.path.join(OUT, "02_chart_fof_debt.svg"), bbox_inches="tight")
fig.savefig(os.path.join(HERE, "preview3.png"), bbox_inches="tight")
plt.close(fig)

# ---------- data csv ----------
import csv
with open(os.path.join(OUT, "02_data.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["year", "sna_net_lending_pct_gdp_imf_weo_oct2026", "gross_debt_pct_gdp_imf_weo_oct2026"])
    for y in range(1980, 2026):
        w.writerow([y, nl.get(y, ""), wd.get(y, "")])
    w.writerow([])
    w.writerow(["fof_quarter_end", "total_debt_pct_gdp_boj_fof_market_value", "net_debt_pct_gdp_boj_fof_market_value"])
    for lab, t, n in zip(["2025-09", "2025-12", "2026-03", "2026-06"], total, net):
        w.writerow([lab, t, n])
    w.writerow([])
    w.writerow(["cabinet_office_trial_jul2026_fy2025_general_government_is_balance_pct_gdp", 0.2])
    w.writerow(["cabinet_office_trial_jan2026_central_local_pb_fy2025_trillion_yen", -7.0])
    w.writerow(["cabinet_office_trial_jul2026_central_local_pb_fy2025_trillion_yen", -0.2])
print("done")
