"""公表の前年比を連鎖して、1人1時間あたり実質賃金の指数（1994年＝100）を作り、作図する。

時給の伸び率 ＝ (1＋実質賃金の前年比)÷(1＋総実労働時間の前年比)−1
要: pip install xlrd pandas matplotlib（日本語フォントは Noto Sans CJK JP を想定）
"""
import pathlib
import xlrd, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = pathlib.Path(__file__).parent
plt.rcParams["font.family"] = ["Noto Sans CJK JP"]

def read_yoy(path):
    """シート TL（調査産業計）の「前年比」ブロックから、年平均と1-6月の前年比を読む。"""
    s = xlrd.open_workbook(path).sheet_by_name("TL")
    start = next(r for r in range(s.nrows) if "前年比" in str(s.row_values(r)[0]))
    ann, h1 = {}, {}
    for r in range(start, s.nrows):
        v = s.row_values(r)
        if isinstance(v[0], float):
            if isinstance(v[1], float): ann[int(v[0])] = v[1]
            if isinstance(v[2], float): h1[int(v[0])] = v[2]
    return pd.Series(ann), pd.Series(h1)

A, H = {}, {}
for n in ["real", "hours", "nominal"]:
    A[n], H[n] = read_yoy(HERE / "raw" / f"{n}.xls")
A, H = pd.DataFrame(A), pd.DataFrame(H)

LAST = 2025
def chain(g):
    v = [100.0]
    for y in range(1995, LAST + 1):
        v.append(v[-1] * (1 + g.loc[y] / 100))
    return pd.Series(v, index=range(1994, LAST + 1))

g_real_hr = ((1 + A.real / 100) / (1 + A.hours / 100) - 1) * 100
g_nom_hr = ((1 + A.nominal / 100) / (1 + A.hours / 100) - 1) * 100
S = pd.DataFrame({
    "1時間あたり実質賃金": chain(g_real_hr),
    "1人あたり実質賃金（月額）": chain(A.real),
    "1時間あたり名目賃金": chain(g_nom_hr),
    "総実労働時間": chain(A.hours),
    "1時間あたり実質賃金_前年比": g_real_hr.reindex(range(1994, LAST + 1)),
})
h = H.loc[2026]
r26 = ((1 + h.real / 100) / (1 + h.hours / 100) - 1) * 100   # 2026年1-6月の前年同期比
ref26 = S.loc[LAST, "1時間あたり実質賃金"] * (1 + r26 / 100)  # 参考値
S.round(2).to_csv(HERE / "01_hourly_real_wage.csv", encoding="utf-8-sig")
print(S.round(1)); print(f"2026年1-6月 前年同期比 {r26:.2f}%  参考値 {ref26:.1f}")

C = {"hr": "#2a78d6", "pp": "#eb6834", "nom": "#8a8985", "hrs": "#1baf7a"}
fig, (ax, bx) = plt.subplots(2, 1, figsize=(11, 8.2), gridspec_kw={"height_ratios": [2.3, 1]}, sharex=True)
x = S.index
ax.plot(x, S["1時間あたり名目賃金"], color=C["nom"], lw=1.6, ls="--", label="1時間あたり名目賃金")
ax.plot(x, S["1人あたり実質賃金（月額）"], color=C["pp"], lw=2, label="1人あたり実質賃金（月額）")
ax.plot(x, S["総実労働時間"], color=C["hrs"], lw=1.6, label="総実労働時間（1人あたり）")
ax.plot(x, S["1時間あたり実質賃金"], color=C["hr"], lw=2.8, label="1時間あたり実質賃金")
ax.plot([LAST, 2026], [S.loc[LAST, "1時間あたり実質賃金"], ref26], color=C["hr"], lw=1.5, ls=":")
ax.scatter([2026], [ref26], s=55, facecolor="white", edgecolor=C["hr"], lw=2, zorder=5, label="2026年1-6月（参考値）")
ax.axhline(100, color="#b0afaa", lw=0.8)
for col, dy in [("1時間あたり実質賃金", 0), ("1人あたり実質賃金（月額）", 5), ("1時間あたり名目賃金", 0), ("総実労働時間", -6)]:
    v = S.loc[LAST, col]
    ax.annotate(f"{v:.1f}", (LAST, v), xytext=(6, dy), textcoords="offset points", fontsize=10, va="center")
ax.annotate(f"{ref26:.1f}", (2026, ref26), xytext=(8, 0), textcoords="offset points", fontsize=10, va="center")
ax.set_ylabel("1994年＝100"); ax.set_title("1人1時間あたり実質賃金の推移（1994年＝100）", fontsize=14, loc="left")
ax.legend(loc="lower left", fontsize=9.5, frameon=False, ncol=2)
ax.grid(axis="y", color="#e6e5e1", lw=0.7); ax.spines[["top", "right"]].set_visible(False)
ax.set_xlim(1993.5, 2027.3)
g = S["1時間あたり実質賃金_前年比"]
bx.bar(g.index, g.values, color=[C["hr"] if v >= 0 else "#e34948" for v in g.values], width=0.7)
bx.bar([2026], [r26], color="white", edgecolor=C["hr"], hatch="///", width=0.7, lw=1)
bx.axhline(0, color="#52514e", lw=0.8); bx.set_ylabel("前年比（%）")
bx.set_title("1時間あたり実質賃金の前年比", fontsize=11, loc="left")
bx.grid(axis="y", color="#e6e5e1", lw=0.7); bx.spines[["top", "right"]].set_visible(False)
bx.set_xticks(range(1994, 2027, 2)); bx.tick_params(axis="x", rotation=45)
fig.text(0.01, 0.005,
    "出所：厚生労働省「毎月勤労統計調査」長期時系列表（事業所規模5人以上・調査産業計・就業形態計）。実質化は消費者物価指数（持家の帰属家賃を除く総合）。\n"
    "公表前年比を連鎖して指数化（サンプル入替による指数水準の段差を回避）。時給＝現金給与総額÷総実労働時間。2026年は1-6月の前年同期比を2025年値に適用した参考値。",
    fontsize=8, color="#52514e")
plt.tight_layout(rect=(0, 0.045, 1, 1))
plt.savefig(HERE.parent / "01_chart_hourly.png", dpi=150, facecolor="white")
