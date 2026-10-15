"""日銀短観「企業の物価見通し」のヘアリーチャート3枚を作る。
入力: boj.json（日本銀行 時系列統計データ検索サイトAPIで取得）、cpi_yoy.csv（e-Stat API, statsDataId=0003427113, 総合・全国・前年同月比）
"""
import json, re
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl
import matplotlib_fontja  # noqa

QMON = {1: 3, 2: 6, 3: 9, 4: 12}   # 3月調査=第1四半期 …
CMAP = mpl.colormaps["turbo"]
TS = lambda p: p.to_timestamp()
XLIM = (pd.Timestamp("2012-01"), pd.Timestamp("2031-12"))

def ser(s, survey=False):
    idx = [pd.Period(f"{i//100}-{(QMON[i%100] if survey else i%100):02d}", "M") for i in s["VALUES"]["SURVEY_DATES"]]
    return pd.Series(s["VALUES"]["VALUES"], index=idx, dtype=float)

def cpi_monthly(fn):
    df = pd.read_csv(fn, dtype=str)
    rows = {}
    for n, v in zip(df.time_name, df.value):
        m = re.fullmatch(r"(\d{4})年(\d{1,2})月", n.strip())
        if m:
            rows[pd.Period(f"{m[1]}-{int(m[2]):02d}", "M")] = float(v)
    s = pd.Series(rows).sort_index()
    return s[s.index >= pd.Period("2012-01", "M")]

def annualize(df):
    """販売価格見通し（現在の水準と比べた変化率）を年率に換算"""
    a = df.copy()
    a[36] = ((1 + df[36] / 100) ** (1 / 3) - 1) * 100
    a[60] = ((1 + df[60] / 100) ** (1 / 5) - 1) * 100
    return a

def deco(ax, ylo):
    ax.axhline(0, color="k", lw=0.5)
    ax.axhline(2, color="gray", ls="--", lw=0.8)
    for d_, t in [("2014-04", "消費税8%"), ("2019-10", "消費税10%")]:
        ax.axvline(pd.Timestamp(d_), color="gray", ls=":", lw=0.8)
        ax.text(pd.Timestamp(d_), ylo, " " + t, fontsize=9, color="gray")
    ax.set_xlim(*XLIM)
    ax.grid(alpha=0.3)

def colorbar(fig, ax, n0, n1, **kw):
    sm = mpl.cm.ScalarMappable(cmap=CMAP, norm=mpl.colors.Normalize(n0, n1))
    cb = fig.colorbar(sm, ax=ax, pad=0.01, **kw)
    cb.set_label("短観の調査時点（年）")

d = json.load(open("boj.json"))
code = lambda s: s["SERIES_CODE"]
H = {"1": 12, "2": 36, "3": 60, "4": 12, "5": 36, "6": 60}
sales_all = pd.DataFrame({H[code(s)[11]]: ser(s, True) for s in d["CO"]["RESULTSET"] if code(s)[9:11] == "20" and code(s)[11] in "123"})
general = pd.DataFrame({H[code(s)[11]]: ser(s, True) for s in d["CO"]["RESULTSET"] if code(s)[11] in "456"})
sector = {sec: pd.DataFrame({H[code(s)[11]]: ser(s, True) for s in d["COSEC"]["RESULTSET"] if code(s)[5] == sec}) for sec in "12"}
cgpi = ser(d["PR01"]["RESULTSET"][0])
sppi = ser(d["PR02"]["RESULTSET"][0])
cpi = cpi_monthly("cpi_yoy.csv")
last = general.index[-1]
n1 = last.year + (last.month - 1) / 12
SRC_SURVEY = f"（{last.year}年{last.month}月調査まで）"

# ---------- 図1：物価全般の見通し × CPI
fig, ax = plt.subplots(figsize=(13, 7))
n = len(general)
for i, (p, r) in enumerate(general.iterrows()):
    c = CMAP(0.05 + 0.9 * i / (n - 1))
    xs = [TS(p)] + [TS(p + h) for h in (12, 36, 60)]
    ys = [cpi.get(p)] + [r[h] for h in (12, 36, 60)]
    ax.plot(xs, ys, "-", color=c, lw=1.1, alpha=0.85)
    ax.plot(xs[1:], ys[1:], "o", color=c, ms=2.5, alpha=0.85)
ax.plot([TS(p) for p in cpi.index], cpi.values, color="black", lw=2.6, label="CPI総合 前年比（実績）", zorder=5)
ax.plot([], [], "-o", color="tab:blue", ms=3, lw=1, label="短観 物価全般の見通し（調査月のCPI実績→1年後→3年後→5年後）")
deco(ax, -1.55)
ax.set_ylim(-1.8, 4.6)
ax.set_ylabel("前年比 %")
ax.legend(loc="upper left", fontsize=10)
ax.set_title("図1　日銀短観「物価全般の見通し」（全規模・全産業）とCPIの実績", fontsize=14)
colorbar(fig, ax, 2014.2, n1)
fig.text(0.01, 0.01, f"出所：日本銀行「短観」（全規模・全産業、物価全般の見通しの平均）{SRC_SURVEY}、総務省「消費者物価指数」2020年基準 総合（e-Stat）。"
         "1年後・3年後・5年後とも、その時点の前年比として回答されたもの。", fontsize=8)
plt.tight_layout(rect=(0, 0.025, 1, 1))
plt.savefig("01_chart_hairy_general.png", dpi=150)
plt.close()

# ---------- 図2：販売価格見通し（全規模・全産業）
ann = annualize(sales_all)
fig, ax = plt.subplots(figsize=(13, 7.5))
n = len(ann)
for i, (p, r) in enumerate(ann.iterrows()):
    c = CMAP(0.05 + 0.9 * i / (n - 1))
    ax.plot([TS(p), TS(p + 12)], [r[12], r[12]], ":", color=c, lw=0.9, alpha=0.7)
    ax.plot([TS(p + h) for h in (12, 36, 60)], [r[h] for h in (12, 36, 60)], "-o", color=c, lw=1.2, ms=3, alpha=0.9)
ax.plot([TS(p) for p in cgpi.index], cgpi.values, color="black", lw=2.2, label="国内企業物価指数 前年比", zorder=5)
ax.plot([TS(p) for p in sppi.index], sppi.values, color="dimgray", lw=2.2, ls="--", label="企業向けサービス価格指数 前年比", zorder=5)
ax.plot([TS(p) for p in cpi.index], cpi.values, color="saddlebrown", lw=1.6, alpha=0.8, label="CPI総合 前年比", zorder=4)
ax.plot([], [], "-o", color="tab:blue", ms=3, lw=1.2, label="短観 販売価格見通し：1年後→3年後→5年後（年率換算）")
ax.plot([], [], ":", color="tab:blue", lw=1, label="調査時点から1年後までの見通し期間")
deco(ax, -4.6)
ax.set_ylim(-5, 11)
ax.set_ylabel("前年比 / 年率 %")
ax.legend(loc="upper left", fontsize=9)
ax.set_title("図2　日銀短観「販売価格の見通し」（全規模・全産業、年率換算）と価格指数の実績", fontsize=14)
colorbar(fig, ax, 2014.2, n1)
fig.text(0.01, 0.01, f"出所：日本銀行「短観」（全規模・全産業、販売価格の見通しの平均）{SRC_SURVEY}、日本銀行「企業物価指数」「企業向けサービス価格指数」、総務省「消費者物価指数」（いずれも2020年基準）。\n"
         "3年後・5年後は「現在の水準と比べた変化率」を年率に換算。", fontsize=8)
plt.tight_layout(rect=(0, 0.04, 1, 1))
plt.savefig("01_chart_hairy_sales_all.png", dpi=150)
plt.close()

# ---------- 図3：製造業・非製造業
panels = [("1", "製造業（全規模）× 国内企業物価指数", "国内企業物価指数 前年比（実績）", cgpi, (-5, 11), -4.6),
          ("2", "非製造業（全規模）× 企業向けサービス価格指数", "企業向けサービス価格指数 前年比（実績）", sppi, (-1.6, 5), -1.3)]
fig, axes = plt.subplots(2, 1, figsize=(13, 12))
for ax, (sec, title, alab, a, ylim, ylo) in zip(axes, panels):
    an = annualize(sector[sec])
    n = len(an)
    for i, (p, r) in enumerate(an.iterrows()):
        c = CMAP(0.05 + 0.9 * i / (n - 1))
        xs = [TS(p)] + [TS(p + h) for h in (12, 36, 60)]
        ys = [a.get(p)] + [r[h] for h in (12, 36, 60)]
        ax.plot(xs, ys, "-", color=c, lw=1.1, alpha=0.85)
        ax.plot(xs[1:], ys[1:], "o", color=c, ms=2.5, alpha=0.85)
    ax.plot([TS(p) for p in a.index], a.values, color="black", lw=2.6, label=alab, zorder=5)
    ax.plot([], [], "-o", color="tab:blue", ms=3, lw=1, label="短観 販売価格見通し（調査月の実績→1年後→3年後→5年後、年率換算）")
    deco(ax, ylo)
    ax.set_ylim(*ylim)
    ax.set_ylabel("前年比 / 年率 %")
    ax.set_title(title, fontsize=12)
    ax.legend(loc="upper left", fontsize=9)
colorbar(fig, axes, 2014.2, n1, shrink=0.6)
fig.suptitle("図3　日銀短観「販売価格の見通し」：製造業と非製造業", fontsize=15, x=0.45, y=0.93)
fig.text(0.01, 0.005, f"出所：日本銀行「短観」（全規模、販売価格の見通しの平均）{SRC_SURVEY}、日本銀行「企業物価指数」「企業向けサービス価格指数」（2020年基準、前年比）。"
         "3年後・5年後は「現在の水準と比べた変化率」を年率に換算。", fontsize=8)
plt.savefig("01_chart_hairy_sales_sector.png", dpi=150, bbox_inches="tight")
plt.close()
