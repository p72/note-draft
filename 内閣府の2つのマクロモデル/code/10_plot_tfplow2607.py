"""tfplow2607.py の結果を、主要計数表と同じ見た目の表にする.

  → output/tfplow2607_table.png（上段: モデルの潜在成長率低下ケース、下段（灰色）: 資料の図20の参考計数）
  → output/tfplow2607_diff.png（現状投影ケースとの差。モデルと資料）
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import chuuchouki2607_data as D  # noqa: E402
import plot_projection as PP  # noqa: E402  （フォント・書式・罫線の表を共用）

ROOT = Path(__file__).resolve().parents[1]
INK, MUTED = PP.INK, PP.MUTED
YEARS = list(range(2025, 2041))
PYEARS = list(range(2028, 2041))
# 資料 図20（３）参考計数（潜在成長率低下ケース、2028〜2040年度）
PUB_LOW = {
    "潜在成長率": [0.1, 0.1, 0.0, -0.0, -0.1, -0.2, -0.3, -0.4, -0.5, -0.6, -0.7, -0.8, -0.8],
    "名目GDP": [730.8, 744.6, 757.6, 770.1, 782.2, 794.6, 807.7, 821.0, 834.3, 847.4, 860.1, 872.3, 884.4],
    "公債等残高（対GDP比）": [181.9, 181.6, 181.8, 182.6, 183.9, 185.4, 187.1, 189.0, 191.2, 193.6, 196.3, 199.3, 202.6],
    "基礎的財政収支（対GDP比）": [0.5, 0.5, 0.3, 0.2, 0.0, -0.1, -0.3, -0.5, -0.6, -0.8, -1.1, -1.3, -1.5],
}


def pub_gen(item: str, t: int) -> float:
    return D.PUB["gen"][item][t - 2024]


def published_low(item: str, t: int) -> float | None:
    if t < 2028:                         # 2027年度まではショック前なので現状投影ケースと同じ
        return pub_gen(item, t) if item in D.PUB["gen"] else None
    if item in PUB_LOW:
        return PUB_LOW[item][t - 2028]
    return None


def table(df: pd.DataFrame, tag: str, note2: str) -> None:
    x = df.pivot(index="year", columns="item", values="low")
    rows = [{"item": it, "year": t, "model": x.loc[t, it], "published": published_low(it, t)}
            for it in PP.ITEMS for t in YEARS]
    tab = pd.DataFrame(rows)
    fig = plt.figure(figsize=(14.5, 7.6), facecolor="white")
    ax = fig.add_axes([0.02, 0.03, 0.96, 0.94])
    ax.axis("off")
    ax.text(0.0, 0.985, "主要計数表：潜在成長率低下ケース（2026年7月試算・図20）", fontsize=14, color=INK, va="center",
            transform=ax.transAxes)
    ax.text(1.0, 0.955, "（％程度）、兆円程度　各欄の上段：モデル　下段（灰色）：資料（図20の参考計数。2027年度までは現状投影ケース）",
            fontsize=8.5, color=INK, ha="right", va="center", transform=ax.transAxes)
    # 資料の値がない欄は空ける
    orig_fmt = PP.fmt
    PP.fmt = lambda item, v: "" if v is None or pd.isna(v) else orig_fmt(item, v)
    bottom = PP._grid_table(ax, 0.0, 0.935, 1.0, tab, YEARS, compare=True, rowh=0.066)
    PP.fmt = orig_fmt
    ax.text(0.0, bottom - 0.015,
            "資料：内閣府「中長期の経済財政に関する試算」（2026年7月）図20。資料は主要乗数表による感応度分析で、参考計数は潜在成長率・名目GDP・公債等残高比・PB比のみ。\n"
            "モデル：経済財政モデル（2026年度版）の Python 再現（財政ブロック移植版）。記事08の現状投影ケースの再現経路（追加財政支出込み）から、"
            "2028年度以降ＴＦＰ上昇率を0.5%pt下げて解き直した。\n" + note2,
            fontsize=7.8, color=MUTED, va="top", transform=ax.transAxes)
    out = ROOT / "output" / f"tfplow2607_table{tag}.png"
    fig.savefig(out, dpi=150, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    print(f"→ {out}")


DIFF_ITEMS = [("潜在成長率", "潜在成長率（%pt）"), ("実質GDP（水準比、%）", "実質GDP（%）"), ("名目GDP", "名目GDP（%）"),
              ("名目長期金利", "名目長期金利（%pt）"), ("基礎的財政収支（対GDP比）", "国・地方のPB対GDP比（%pt）"),
              ("公債等残高（対GDP比）", "国・地方の公債等残高対GDP比（%pt）")]


def diff_table(df: pd.DataFrame, tag: str) -> None:
    b = df.pivot(index="year", columns="item", values="base")
    lo = df.pivot(index="year", columns="item", values="low")

    def model(item, t):
        if item == "名目GDP":
            return (lo.loc[t, item] / b.loc[t, item] - 1) * 100
        return lo.loc[t, item] - b.loc[t, item]

    def pub(item, t):
        if item not in PUB_LOW:
            return None
        v = PUB_LOW[item][t - 2028]
        if item == "名目GDP":
            return (v / pub_gen(item, t) - 1) * 100
        return v - pub_gen(item, t)

    def f(v):
        if v is None:
            return ""
        s = f"{abs(v):.2f}" if abs(v) < 10 else f"{abs(v):.1f}"
        return ("▲" + s) if round(v, 2) < 0 else ("+" + s if round(v, 2) > 0 else "0.00")

    def f1(v):
        s = f"{abs(v):.1f}"
        return ("▲" + s) if round(v, 1) < 0 else ("+" + s if round(v, 1) > 0 else "0.0")

    fig = plt.figure(figsize=(14.5, 5.2), facecolor="white")
    ax = fig.add_axes([0.02, 0.03, 0.96, 0.94])
    ax.axis("off")
    kw = dict(transform=ax.transAxes, color=INK)
    ax.text(0.0, 0.975, "現状投影ケースとの差（潜在成長率低下ケース − 現状投影ケース）", fontsize=14, va="center", **kw)
    ax.text(1.0, 0.925, "各欄の上段：モデル　下段（灰色）：資料（主要乗数表による感応度分析）", fontsize=8.5, ha="right", va="center", **kw)
    x0, y0, width, rowh = 0.0, 0.895, 1.0, 0.115
    labw = 0.2
    colw = (width - labw) / len(PYEARS)
    nrow = len(DIFF_ITEMS) + 1
    bottom = y0 - rowh * nrow
    ax.add_patch(plt.Rectangle((x0, bottom), width, rowh * nrow, fill=False, lw=1.0, ec=INK, transform=ax.transAxes))
    for r in range(1, nrow):
        ax.plot([x0, x0 + width], [y0 - rowh * r] * 2, lw=0.9 if r == 1 else 0.5, **kw)
    ax.plot([labw] * 2, [bottom, y0], lw=0.6, **kw)
    for j in range(1, len(PYEARS)):
        ax.plot([labw + colw * j] * 2, [bottom, y0], lw=0.4, **kw)
    ax.text(labw / 2, y0 - rowh / 2, "年　　　度", ha="center", va="center", fontsize=9.5, **kw)
    for j, t in enumerate(PYEARS):
        ax.text(labw + colw * (j + 0.5), y0 - rowh / 2, str(t), ha="center", va="center", fontsize=9.5, **kw)
    for i, (item, label) in enumerate(DIFF_ITEMS):
        yc = y0 - rowh * (i + 1.5)
        ax.text(0.006, yc, label, ha="left", va="center", fontsize=9, **kw)
        for j, t in enumerate(PYEARS):
            cx = labw + colw * (j + 0.5)
            p = pub(item, t)
            if p is None:
                ax.text(cx, yc, f(model(item, t)), ha="center", va="center", fontsize=8.8, **kw)
            else:
                ax.text(cx, yc + rowh * 0.17, f(model(item, t)), ha="center", va="center", fontsize=8.8, **kw)
                ax.text(cx, yc - rowh * 0.22, f1(p), ha="center", va="center", fontsize=7.2, color="#8a8984",
                        transform=ax.transAxes)
    ax.text(0.0, bottom - 0.03,
            "資料の差は、図20の参考計数から現状投影ケースの主要計数表の値を引いたもの（どちらも0.1刻みに丸められた値なので、±0.1程度の誤差がある）。"
            "実質GDPと長期金利は資料に値がない。",
            fontsize=7.8, color=MUTED, va="top", transform=ax.transAxes)
    out = ROOT / "output" / f"tfplow2607_diff{tag}.png"
    fig.savefig(out, dpi=150, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    print(f"→ {out}")


# ---- 各ケースの主要計数表（成長戦略実現①②・現状投影の再現）と、4ケースを並べた表 ----
CASE_NAMES = {"s1": "成長戦略実現ケース①", "s2": "成長戦略実現ケース②", "gen": "現状投影ケース"}


def case_values(case: str) -> pd.DataFrame:
    import pickle
    import projection2607 as Q
    Q.configure()
    data = pickle.loads(Q.state_path(case).read_bytes())["data"]
    rows = []
    for t in YEARS:
        v = Q.item_values(data, t)
        for it in PP.ITEMS:
            rows.append({"item": it, "year": t, "model": v[it], "published": D.PUB[case][it][t - 2024]})
    return pd.DataFrame(rows)


def case_table(case: str) -> None:
    tab = case_values(case)
    fig = plt.figure(figsize=(14.5, 7.6), facecolor="white")
    ax = fig.add_axes([0.02, 0.03, 0.96, 0.94])
    ax.axis("off")
    ax.text(0.0, 0.985, f"主要計数表の再現：{CASE_NAMES[case]}（2026年7月試算）", fontsize=14, color=INK, va="center",
            transform=ax.transAxes)
    ax.text(1.0, 0.955, "（％程度）、兆円程度　各欄の上段：モデル　下段（灰色）：資料", fontsize=8.5, color=INK, ha="right",
            va="center", transform=ax.transAxes)
    bottom = PP._grid_table(ax, 0.0, 0.935, 1.0, tab, YEARS, compare=True, rowh=0.066)
    ax.text(0.0, bottom - 0.015,
            "資料：内閣府「中長期の経済財政に関する試算」（2026年7月）計数表「主要計数表」。モデルは経済財政モデル（2026年度版）の Python 再現（財政ブロック移植版）。\n"
            "記事08と同じ再現（毎年度実質10兆円の追加財政支出込み）。マクロの7項目と予算ベースの歳出等を資料に合わせ、名目GDP・PB・公債等残高はモデルで計算した。",
            fontsize=7.8, color=MUTED, va="top", transform=ax.transAxes)
    out = ROOT / "output" / f"chuuchouki2607_table_{case}.png"
    fig.savefig(out, dpi=150, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    print(f"→ {out}")


CMP_ITEMS = [("潜在成長率", "潜在成長率（%）"), ("実質GDP成長率", "実質GDP成長率（%）"), ("名目GDP成長率", "名目GDP成長率（%）"),
             ("名目GDP", "名目GDP（兆円）"), ("名目長期金利", "名目長期金利（%）"),
             ("基礎的財政収支（対GDP比）", "国・地方PB（対GDP比、%）"), ("公債等残高（対GDP比）", "公債等残高（対GDP比、%）")]


def compare_cases(low: pd.DataFrame) -> None:
    """4ケースの主な計数をモデルで並べる（2030・2035・2040年度は資料も）."""
    lo = low.pivot(index="year", columns="item", values="low")
    vals = {c: case_values(c).pivot(index="year", columns="item", values="model") for c in CASE_NAMES}
    pubs = {c: case_values(c).pivot(index="year", columns="item", values="published") for c in CASE_NAMES}
    vals["low"] = lo
    pubs["low"] = pd.DataFrame({it: {t: published_low(it, t) for t in YEARS} for it, _ in CMP_ITEMS})
    names = {**CASE_NAMES, "low": "潜在成長率低下ケース"}
    colors = {"s1": "#1baf7a", "s2": "#2a78d6", "gen": "#eb6834", "low": "#b8322f"}
    yrs = [2026, 2027, 2028, 2030, 2032, 2035, 2038, 2040]
    fig = plt.figure(figsize=(14.5, 12.5), facecolor="white")
    ax = fig.add_axes([0.02, 0.02, 0.96, 0.96])
    ax.axis("off")
    kw = dict(transform=ax.transAxes)
    ax.text(0.0, 0.99, "4ケースの主要計数（2026年7月試算の再現と潜在成長率低下ケース）", fontsize=14, color=INK, va="center", **kw)
    ax.text(1.0, 0.968, "各欄の上段：モデル　下段（灰色）：資料（低下ケースは図20の参考計数がある項目のみ）", fontsize=8.5,
            color=INK, ha="right", va="center", **kw)
    labw, casew = 0.17, 0.13
    colw = (1 - labw - casew) / len(yrs)
    rowh = 0.0305
    y = 0.95
    ax.plot([0, 1], [y, y], lw=1.0, color=INK, **kw)
    ax.text(labw / 2, y - rowh / 2, "項目", ha="center", va="center", fontsize=9.5, color=INK, **kw)
    ax.text(labw + casew / 2, y - rowh / 2, "ケース", ha="center", va="center", fontsize=9.5, color=INK, **kw)
    for j, t in enumerate(yrs):
        ax.text(labw + casew + colw * (j + 0.5), y - rowh / 2, f"{t}年度", ha="center", va="center", fontsize=9.5,
                color=INK, **kw)
    y -= rowh
    ax.plot([0, 1], [y, y], lw=0.9, color=INK, **kw)
    for it, lab in CMP_ITEMS:
        top = y
        for c in ("s1", "s2", "gen", "low"):
            yc = y - rowh / 2
            ax.text(labw + 0.005, yc, names[c], ha="left", va="center", fontsize=8.6, color=colors[c], **kw)
            for j, t in enumerate(yrs):
                cx = labw + casew + colw * (j + 0.5)
                m = vals[c].loc[t, it]
                p = pubs[c].loc[t, it] if t in pubs[c].index else None
                ms = f"{m:.1f}" if it == "名目GDP" else (f"▲{abs(m):.1f}" if round(m, 1) < 0 else f"{abs(round(m, 1)):.1f}")
                ax.text(cx - colw * 0.2, yc, ms, ha="center", va="center", fontsize=9, color=INK, **kw)
                if p is not None and not pd.isna(p):
                    ps = f"{p:.1f}" if it == "名目GDP" else (f"▲{abs(p):.1f}" if round(p, 1) < 0 else f"{p:.1f}")
                    ax.text(cx + colw * 0.25, yc, ps, ha="center", va="center", fontsize=7.6, color="#8a8984", **kw)
            y -= rowh
        ax.text(0.006, (top + y) / 2, lab, ha="left", va="center", fontsize=9.2, color=INK, **kw)
        ax.plot([0, 1], [y, y], lw=0.6, color=INK, **kw)
    ax.plot([labw, labw], [y, 0.95], lw=0.6, color=INK, **kw)
    ax.plot([labw + casew, labw + casew], [y, 0.95], lw=0.4, color=INK, **kw)
    for j in range(1, len(yrs)):
        ax.plot([labw + casew + colw * j] * 2, [y, 0.95], lw=0.3, color="#bbbbbb", **kw)
    ax.text(0.0, y - 0.012,
            "各欄の左：モデル、右（灰色）：資料。モデルは経済財政モデル（2026年度版）の Python 再現。成長戦略実現①②・現状投影は記事08の再現（追加財政支出込み）、\n"
            "潜在成長率低下ケースは現状投影ケースから2028年度以降ＴＦＰ上昇率を0.5%pt下げて解き直したもの（実質の公需は現状投影ケースのまま）。",
            fontsize=7.8, color=MUTED, va="top", **kw)
    out = ROOT / "output" / "tfplow2607_cases.png"
    fig.savefig(out, dpi=150, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    print(f"→ {out}")


if __name__ == "__main__":
    tag = sys.argv[1] if len(sys.argv) > 1 else ""      # "" か "_nominal"
    df = pd.read_csv(ROOT / "output" / f"tfplow2607_gen_tfplow{tag}.csv")
    note = ("実質の政府消費・公的固定資本形成は現状投影ケースのまま（追加財政支出の公需も実質で同じ）。金利・税収・利払費などはモデルの式で動く。"
            if tag == "" else "歳出の調整項は現状投影ケースのまま（名目の予算の置き方を変えない）。金利・税収・利払費などはモデルの式で動く。")
    table(df, tag, note)
    diff_table(df, tag)
    if tag == "":
        for c in CASE_NAMES:
            if (ROOT / "output" / "parts" / f"proj_state_2607_{c}.pkl").exists():
                case_table(c)
        if all((ROOT / "output" / "parts" / f"proj_state_2607_{c}.pkl").exists() for c in CASE_NAMES):
            compare_cases(df)
