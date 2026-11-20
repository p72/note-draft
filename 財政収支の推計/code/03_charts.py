# -*- coding: utf-8 -*-
"""
記事の図1・図2 (SVG) を生成する。数値は 03_gamble.py の simulate をそのまま使う。
実行: python3 03_charts.py   (numpy, matplotlib)
"""
import os, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.patches import Patch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from importlib import import_module
g = import_module("03_gamble")

plt.style.use("default")
FONT = "/home/hatch/workspace/tools/fonts/NotoSansCJKjp-Regular.otf"
if os.path.exists(FONT):
    fm.fontManager.addfont(FONT)
    plt.rcParams["font.family"] = "Noto Sans CJK JP"

COUNTRIES = ["ドイツ", "日本", "英国", "米国"]
KEYS = ["Germany", "Japan", "UK", "US"]
LABELS = ["20年で1.5倍", "30年で2倍", "10年で300%超", "50年で400%超"]
ORIG = np.array([g.ORIGINAL[k] for k in KEYS])
REP = np.array([g.simulate(*g.INIT["A_2016_原図公表値"][k]) for k in KEYS])
UPD = np.array([g.simulate(*g.INIT["C_2025_WEO最新"][k]) for k in KEYS])


def chart(vals_a, vals_b, la, lb, ca, cb, title, fname):
    fig, ax = plt.subplots(figsize=(11, 5.6))
    x = np.arange(4); w = 0.09
    for i in range(4):
        xo = x + (i * 2 - 3.5) * w; xr = x + (i * 2 - 2.5) * w
        ax.bar(xo, vals_a[:, i], width=w, color=ca[0], edgecolor=ca[1], linewidth=0.6)
        ax.bar(xr, vals_b[:, i], width=w, color=cb[0], edgecolor=cb[1], linewidth=0.6)
        for xi, v in zip(xo, vals_a[:, i]):
            if v > 0: ax.text(xi, v + 0.018, f"{v:.3g}", ha="center", fontsize=7.5, color=ca[1], rotation=90)
        for xi, v in zip(xr, vals_b[:, i]):
            if v > 0: ax.text(xi, v + 0.018, f"{v:.3g}", ha="center", fontsize=7.5, color=cb[1], rotation=90)
    ax.set_xticks(x); ax.set_xticklabels(COUNTRIES, fontsize=12)
    ax.set_ylim(0, 0.85); ax.set_ylabel("確率", fontsize=11)
    ax.set_title(title, fontsize=12.5, loc="left")
    ax.legend(handles=[Patch(facecolor=ca[0], edgecolor=ca[1], label=la),
                       Patch(facecolor=cb[0], edgecolor=cb[1], label=lb)],
              fontsize=9, loc="upper center", bbox_to_anchor=(0.47, 1.02), frameon=False)
    ax.text(0.99, 0.96, "棒の組（左→右）: " + " / ".join(LABELS),
            transform=ax.transAxes, ha="right", fontsize=8.5, color="#333333")
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", color="#e5e5e5", linewidth=0.6); ax.set_axisbelow(True)
    fig.tight_layout(); fig.savefig(fname); plt.close(fig)


if __name__ == "__main__":
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
    chart(ORIG, REP, "原図（2016年、転記）", "近似再現（共通過程、5000本）",
          ("#c9c9c9", "#666666"), ("#2e5f8a", "#1f4464"),
          "図1 小黒ほか『財政破綻後』図2-1の近似再現 ― 灰＝原図、青＝再現",
          os.path.join(out, "03_chart_replication.svg"))
    chart(ORIG, UPD, "2016年版（原図の転記）", "2025年版（WEO 2026年10月号、5000本）",
          ("#c9c9c9", "#666666"), ("#b03a2e", "#7b241c"),
          "図2 図2-1の現在版アップデート ― 灰＝2016年版（原図）、赤＝2025年版",
          os.path.join(out, "03_chart_update.svg"))
    print("charts written")
