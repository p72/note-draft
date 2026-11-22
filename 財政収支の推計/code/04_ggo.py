#!/usr/bin/env python3
"""2025年度の一般政府PB・財政収支の推計：データ取得・集計・作図コード

データ:
  ESRI SDDSプラス 四半期別一般政府収支（General Government Operations, ggo.xlsx, 10億円）
    https://www.esri.cao.go.jp/en/sna/sddsplus/tables/ggo.xlsx
  日本銀行 時系列統計API 資金循環統計（年度・フロー、資金過不足）
    FOF_FFYF420L700 一般政府 / 421 中央政府 / 422 地方公共団体 / 423 社会保障基金
出力: 04_data.csv、04_chart_halfyear.svg、04_chart_real_vs_fin.svg（記事フォルダ直下）
"""
import csv
import json
import os
import urllib.request

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import openpyxl

plt.style.use("default")
plt.rcParams["font.family"] = "Noto Sans CJK JP"
plt.rcParams["axes.facecolor"] = "white"
plt.rcParams["figure.facecolor"] = "white"
plt.rcParams["svg.fonttype"] = "path"

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
WORK = os.path.join(HERE, "work")
os.makedirs(WORK, exist_ok=True)

GGO_URL = "https://www.esri.cao.go.jp/en/sna/sddsplus/tables/ggo.xlsx"
BOJ_URL = ("https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=json&lang=jp&db=FF"
           "&startDate=2015&code=FOF_FFYF420L700,FOF_FFYF421L700,FOF_FFYF422L700,FOF_FFYF423L700")


def fetch(url, path):
    if not os.path.exists(path):
        urllib.request.urlretrieve(url, path)
    return path


# ---------- ESRI 四半期別一般政府収支 ----------
ws = openpyxl.load_workbook(fetch(GGO_URL, os.path.join(WORK, "ggo.xlsx")), data_only=True)["GGO"]
rows = list(ws.iter_rows(values_only=True))
hdr = rows[3]
D = {r[0]: dict(zip(hdr[1:], r[1:])) for r in rows if r[0]}


def fy_quarters(fy, half=None):
    """年度 fy の四半期ラベル（暦年表記: 4-6月期=Q2 … 1-3月期=翌年Q1）"""
    q = [f"{fy}Q2", f"{fy}Q3", f"{fy}Q4", f"{fy + 1}Q1"]
    return q[:2] if half == 1 else q[2:] if half == 2 else q


def ssum(item, qs):
    vals = [D[item].get(q) for q in qs]
    if any(v is None or isinstance(v, str) for v in vals):
        return None
    return sum(vals) / 1000.0  # 兆円


def fin(qs):
    a = ssum("Net acquisition of financial assets", qs)
    l = ssum("Net incurrence of liabilities", qs)
    return None if a is None or l is None else a - l


# ---------- 日銀 資金循環統計 ----------
boj = json.load(open(fetch(BOJ_URL, os.path.join(WORK, "boj_ff.json"))))
FOF = {}
for r in boj["RESULTSET"]:
    v = r["VALUES"]
    FOF[r["SERIES_CODE"]] = {int(t): x / 10000.0 for t, x in zip(v["SURVEY_DATES"], v["VALUES"]) if x is not None}

# ---------- 集計 ----------
years = list(range(2015, 2026))
recs = []
for fy in years:
    recs.append(dict(
        年度=fy,
        純貸出_上期=ssum("Net lending/borrowing", fy_quarters(fy, 1)),
        純貸出_下期=ssum("Net lending/borrowing", fy_quarters(fy, 2)),
        純貸出_通年=ssum("Net lending/borrowing", fy_quarters(fy)),
        税_上期=ssum(" Taxes", fy_quarters(fy, 1)),
        支払利子_上期=ssum(" Interest", fy_quarters(fy, 1)),
        金融側_通年=fin(fy_quarters(fy)),
        資金循環_一般政府=FOF["FOF_FFYF420L700"].get(fy),
        資金循環_中央政府=FOF["FOF_FFYF421L700"].get(fy),
        資金循環_地方=FOF["FOF_FFYF422L700"].get(fy),
        資金循環_社会保障基金=FOF["FOF_FFYF423L700"].get(fy),
    ))

with open(os.path.join(ART, "04_data.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(recs[0].keys()))
    w.writeheader()
    for r in recs:
        w.writerow({k: (round(v, 2) if isinstance(v, float) else v) for k, v in r.items()})

for r in recs:
    print(r)

# ---------- 2025年度下期のシナリオ（兆円、筆者の仮定） ----------
SCN = {"楽観": 0.0, "中位": -2.3, "悲観": -6.6}
h1_25 = recs[-1]["純貸出_上期"]

# ---------- Chart 1: 上期・下期の純貸出 ----------
fig, ax = plt.subplots(figsize=(9.2, 5.0), dpi=150)
x = list(range(len(years)))
h1 = [r["純貸出_上期"] for r in recs]
h2 = [r["純貸出_下期"] if r["純貸出_下期"] is not None else SCN["中位"] for r in recs]
ax.bar([i - 0.2 for i in x], h1, width=0.4, color="#1f4e79", label="上期（4〜9月）")
bars = ax.bar([i + 0.2 for i in x], h2, width=0.4, color="#9dc3e6", label="下期（10〜3月）")
bars[-1].set_hatch("//")
bars[-1].set_facecolor("white")
bars[-1].set_edgecolor("#5b9bd5")
ax.errorbar([x[-1] + 0.2], [SCN["中位"]], yerr=[[SCN["中位"] - SCN["悲観"]], [SCN["楽観"] - SCN["中位"]]],
            fmt="none", ecolor="#c00000", capsize=5, lw=1.5)
ax.annotate(f"2025年度上期 +{h1_25:.1f}兆円", xy=(x[-1] - 0.2, h1_25), xytext=(x[-1] - 4.6, 4.0),
            fontsize=10.5, color="#1f4e79", fontweight="bold",
            arrowprops=dict(arrowstyle="->", color="#1f4e79"))
ax.annotate("下期は未公表\n（斜線：中位シナリオ、赤線：楽観〜悲観）", xy=(x[-1] + 0.2, SCN["悲観"]),
            xytext=(x[-1] - 3.6, -26.0), fontsize=9.5, color="#c00000",
            arrowprops=dict(arrowstyle="->", color="#c00000"))
ax.axhline(0, color="#333333", lw=1.0)
ax.set_xticks(x)
ax.set_xticklabels([f"{y}" for y in years])
ax.set_ylabel("兆円")
ax.set_xlabel("年度")
ax.set_ylim(-36, 8)
ax.set_title("一般政府の純貸出（＋）／純借入（－）：年度上期・下期", fontsize=13)
ax.legend(loc="lower left", frameon=False)
ax.grid(axis="y", color="#dddddd", lw=0.6)
fig.text(0.01, 0.012, "出所：内閣府 経済社会総合研究所「SDDSプラス 四半期別一般政府収支」（2026年10月30日公表）より作成。"
        "2025年度下期は筆者のシナリオ。", fontsize=8, color="#555555")
fig.tight_layout(rect=[0, 0.04, 1, 1])
fig.savefig(os.path.join(ART, "04_chart_halfyear.svg"))
fig.savefig(os.path.join(WORK, "04_chart_halfyear.png"))
plt.close(fig)

# ---------- Chart 2: 実物側と金融側 ----------
fig, ax = plt.subplots(figsize=(9.2, 5.0), dpi=150)
real = [r["純貸出_通年"] for r in recs[:-1]] + [h1_25 + SCN["中位"]]
finl = [r["金融側_通年"] for r in recs]
fof = [r["資金循環_一般政府"] for r in recs]
ax.plot(years[:-1], real[:-1], color="#1f4e79", lw=2.2, marker="o", ms=4, label="実物側の純貸出（SNA、四半期別一般政府収支）")
ax.plot(years[-2:], real[-2:], color="#1f4e79", lw=2.0, ls="--")
ax.errorbar([2025], [real[-1]], yerr=[[SCN["中位"] - SCN["悲観"]], [SCN["楽観"] - SCN["中位"]]],
            fmt="D", color="#1f4e79", ecolor="#c00000", capsize=5, ms=6)
ax.plot(years, finl, color="#ed7d31", lw=1.8, marker="s", ms=4, label="金融側（金融資産の増加－負債の増加、同上）")
ax.plot(years, fof, color="#7f7f7f", lw=1.4, ls=":", marker="^", ms=4, label="資金循環統計の資金過不足（日本銀行）")
ax.axhline(0, color="#333333", lw=1.0)
ax.annotate("2025年度（推計）\n上期実績＋下期中位", xy=(2025, real[-1]), xytext=(2021.3, -42.0),
            fontsize=10, color="#1f4e79", arrowprops=dict(arrowstyle="->", color="#1f4e79"))
ax.set_xticks(years)
ax.set_ylabel("兆円")
ax.set_xlabel("年度")
ax.set_title("一般政府の財政収支：実物側と金融側の乖離", fontsize=13)
ax.legend(loc="lower left", frameon=False, fontsize=9)
ax.grid(axis="y", color="#dddddd", lw=0.6)
fig.text(0.01, 0.012, "出所：内閣府 経済社会総合研究所「SDDSプラス 四半期別一般政府収支」、日本銀行「資金循環統計」より作成。",
        fontsize=8, color="#555555")
fig.tight_layout(rect=[0, 0.04, 1, 1])
fig.savefig(os.path.join(ART, "04_chart_real_vs_fin.svg"))
fig.savefig(os.path.join(WORK, "04_chart_real_vs_fin.png"))
plt.close(fig)
