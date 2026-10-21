"""マネーの伸びに対する貸出の寄与度（名目・実質）を計算して作図する。"""
import sys, pathlib
import pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
HERE = pathlib.Path(__file__).parent
OUT = HERE.parent
sys.path.insert(0, "/mnt/skills/plugins/boj-api")
from scripts.boj_api import setup_japanese_font  # noqa: E402
setup_japanese_font()

ms = pd.read_csv(HERE / "survey.csv", index_col=0, parse_dates=True)
cur = pd.read_csv(HERE / "loan_m3.csv", index_col=0, parse_dates=True)
c = pd.read_csv(HERE / "cpi.csv", index_col=0)
c.index = pd.PeriodIndex(c.index, freq="M").to_timestamp()
P = c["cpi"]

def calc(L, M):
    p = P.reindex(L.index)
    r = pd.DataFrame(index=L.index)
    r["マネー名目"] = (M / M.shift(12) - 1) * 100
    r["貸出寄与名目"] = (L - L.shift(12)) / M.shift(12) * 100
    Lr, Mr = L / p, M / p
    r["マネー実質"] = (Mr / Mr.shift(12) - 1) * 100
    r["貸出寄与実質"] = (Lr - Lr.shift(12)) / Mr.shift(12) * 100
    return r

A = calc(ms["MASVK_MASV1A51"], ms["MASVK_MASV1L1"] + ms["MASVK_MASV1L2"]).loc[:"1999-03"]
B = calc(ms["MASV4NA51"], ms["MASV4NL1"] + ms["MASV4NL2"]).loc["1999-04":"2004-03"]
C = calc(cur["FAAP@01"], cur["MAM1NAM3M3MO"]).loc["2004-04":]
r = pd.concat([A, B, C]).loc["1980-01":].dropna(how="all")
for k in ["名目", "実質"]:
    r["その他寄与" + k] = r["マネー" + k] - r["貸出寄与" + k]
r["CPI前年比"] = (P / P.shift(12) - 1).reindex(r.index) * 100
r.round(2).to_csv(HERE / "contribution.csv", encoding="utf-8-sig")
SRC = "出所：日本銀行（マネタリーサーベイ、マネーストック、貸出・預金動向）、総務省「消費者物価指数」"

# 図1：1980年～
fig, ax = plt.subplots(2, 1, figsize=(12, 8.5), sharex=True)
for a, k, t in [(ax[0], "名目", "名目"), (ax[1], "実質", "実質（消費者物価指数・総合で実質化）")]:
    s = r.dropna(subset=["マネー" + k])
    a.fill_between(s.index, 0, s["貸出寄与" + k], color="#1f77b4", alpha=.8, lw=0, label="貸出による寄与")
    a.plot(s.index, s["マネー" + k], color="k", lw=1.3, label="マネー前年比（2004年3月まで M2+CD、以降 M3）")
    a.axhline(0, color="k", lw=.6)
    for d in ["1999-04-01", "2004-04-01"]:
        a.axvline(pd.Timestamp(d), color="gray", ls=":", lw=1)
    a.set_title(f"マネーの伸びと貸出の寄与度：{t}"); a.set_ylabel("％"); a.grid(alpha=.3)
ax[0].legend(loc="upper right", fontsize=9)
fig.text(0.01, 0.005, SRC + "。点線は系列の接続点", fontsize=8)
plt.tight_layout(rect=(0, 0.02, 1, 1)); plt.savefig(OUT / "01_chart_1980.png", dpi=150); plt.close()

# 図2：2004年4月～（M3、貸出とその他に分解）
fig, ax = plt.subplots(2, 1, figsize=(12, 8.5), sharex=True)
s0 = r.loc["2004-04":]
for a, k, t in [(ax[0], "名目", "名目"), (ax[1], "実質", "実質（消費者物価指数・総合で実質化）")]:
    s = s0.dropna(subset=["マネー" + k])
    a.fill_between(s.index, 0, s["貸出寄与" + k], color="#1f77b4", alpha=.8, lw=0, label="貸出による寄与")
    a.plot(s.index, s["その他寄与" + k], color="#999999", lw=1.2, label="その他の寄与（国債・対外資産など）")
    a.plot(s.index, s["マネー" + k], color="k", lw=1.5, label="M3 前年比")
    a.axhline(0, color="k", lw=.6)
    a.set_title(f"M3の伸びと貸出の寄与度（2004年～）：{t}"); a.set_ylabel("％"); a.grid(alpha=.3)
ax[0].legend(loc="upper left", fontsize=9)
fig.text(0.01, 0.005, SRC + "。貸出は銀行・信金の総貸出平残、M3は平残", fontsize=8)
plt.tight_layout(rect=(0, 0.02, 1, 1)); plt.savefig(OUT / "01_chart_2004.png", dpi=150); plt.close()

# 期間平均
bins = {"1980-84": ("1980", "1984"), "1985-90": ("1985", "1990"), "1991-95": ("1991", "1995"),
        "1996-2005": ("1996", "2005"), "2006-12": ("2006", "2012"), "2013-19": ("2013", "2019"),
        "2020-21": ("2020", "2021"), "2022-25": ("2022", "2025"), "2026/1-8": ("2026", "2026")}
tab = pd.DataFrame({k: r.loc[a:b].mean() for k, (a, b) in bins.items()}).T
print(tab.round(1).to_string())
print(r.dropna().tail(1).round(2).T)
