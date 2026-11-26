"""潜在成長率低下ケースのグラフ（資料の図20と同じ形）. → output/tfplow2607_chart.png"""
from __future__ import annotations

import pickle
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import chuuchouki2607_data as D  # noqa: E402
import plot_projection as PP  # noqa: E402,F401  （日本語フォント）
import projection2607 as Q  # noqa: E402
from plot_tfplow2607 import PUB_LOW  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
YRS = list(range(2024, 2041))
CASES = {"s1": ("成長戦略実現ケース①", "#1baf7a"), "s2": ("成長戦略実現ケース②", "#2a78d6"),
         "gen": ("現状投影ケース", "#eb6834"), "low": ("潜在成長率低下ケース", "#b8322f")}
PANELS = [("公債等残高（対GDP比）", "（１）国・地方の公債等残高対GDP比（％）"),
          ("基礎的財政収支（対GDP比）", "（２）国・地方のPB対GDP比（％）"),
          ("名目GDP", "（３）名目GDP（兆円）"), ("潜在成長率", "（４）潜在成長率（％）")]


def main() -> None:
    Q.configure()
    model, pub = {}, {}
    for c in ("s1", "s2", "gen"):
        data = pickle.loads(Q.state_path(c).read_bytes())["data"]
        model[c] = pd.DataFrame({t: Q.item_values(data, t) for t in YRS}).T
        pub[c] = pd.DataFrame({it: D.PUB[c][it][:len(YRS)] for it, _ in PANELS}, index=YRS)
    low = pd.read_csv(ROOT / "output" / "tfplow2607_gen_tfplow.csv").pivot(index="year", columns="item", values="low")
    model["low"] = low.loc[YRS]
    pl = pub["gen"].copy()
    for it, v in PUB_LOW.items():
        pl.loc[2028:2040, it] = v
    pub["low"] = pl
    fig, axes = plt.subplots(2, 2, figsize=(13, 8.6), facecolor="white")
    for ax, (it, title) in zip(axes.flat, PANELS):
        for c, (name, col) in CASES.items():
            x0 = 2027 if c != "gen" else 2025
            m = model[c][it].loc[x0:]
            p = pub[c][it].loc[x0:]
            ax.plot(m.index, m.values, color=col, lw=2.2 if c == "low" else 1.8, label=f"{name}（モデル）")
            ax.plot(p.index, p.values, color=col, lw=1.2, ls=":", label=f"{name}（資料）")
            ax.annotate(f"{m.iloc[-1]:.1f}", (2040, m.iloc[-1]), xytext=(6, 0), textcoords="offset points",
                        color=col, fontsize=9, va="center")
        if it == "基礎的財政収支（対GDP比）" or it == "潜在成長率":
            ax.axhline(0, color="#888", lw=0.7)
        ax.axvline(2027.5, color="#bbb", lw=0.8, ls="--")
        ax.set_title(title, fontsize=11.5, loc="left")
        ax.set_xlim(2025, 2041.5)
        ax.set_xticks(range(2025, 2041, 1), [str(t) if t % 5 == 0 else "" for t in range(2025, 2041)])
        ax.grid(alpha=0.3)
    h, lab = axes[0, 0].get_legend_handles_labels()
    fig.legend(h, lab, loc="lower center", ncol=4, fontsize=9, frameon=False, bbox_to_anchor=(0.5, -0.005))
    fig.suptitle("潜在成長率低下ケース（2026年7月試算・図20）：モデルで解き直した結果", fontsize=14, x=0.01, ha="left")
    fig.text(0.01, -0.06,
             "実線：モデル（経済財政モデル2026年度版の Python 再現）、点線：資料（内閣府「中長期の経済財政に関する試算」2026年7月、主要計数表・図20）。\n"
             "成長戦略実現①②・現状投影は記事08の再現（毎年度実質10兆円の追加財政支出込み）。潜在成長率低下ケースは現状投影ケースから2028年度以降（破線の右）\n"
             "ＴＦＰ上昇率を0.5%pt下げて解き直した（実質の公需は現状投影のまま）。資料の低下ケースは主要乗数表による感応度分析。",
             fontsize=8.5, color="#52514e", va="top")
    fig.tight_layout(rect=(0, 0.07, 1, 0.96))
    out = ROOT / "output" / "tfplow2607_chart.png"
    fig.savefig(out, dpi=150, facecolor="white", bbox_inches="tight")
    print(f"→ {out}")


if __name__ == "__main__":
    main()
