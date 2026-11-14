"""推計：週次の金利差モデル（図1・表1）、月次の要因分解モデル（図2・図3・表2〜表4）、
財政ニュースのイベントスタディと日次の符号分類（図4・表5・表6）。

単位：ドル円は対数×100。差をとった値は「対数ポイント」（ふつうの変化率とは少しずれる）。
"""
import numpy as np, pandas as pd, statsmodels.api as sm
from statsmodels.tsa.stattools import adfuller

def ols(y, X, lags):
    return sm.OLS(y, sm.add_constant(X)).fit(cov_type="HAC", cov_kwds={"maxlags": lags})

def coef_table(m, name):
    return pd.DataFrame({"model": name, "coef": m.params, "t": m.tvalues, "p": m.pvalues,
                         "R2": m.rsquared, "n": int(m.nobs)})

tabs = []

# =============================================================
# A. 週次：日米2年金利差モデルの乖離（図1）と週次変化の回帰（表1）
# =============================================================
j = pd.read_csv("jgb_daily.csv", index_col=0, parse_dates=True)
u = pd.read_csv("daily_us_fx.csv", index_col=0, parse_dates=True)
w = u.join(j, how="outer").ffill().loc["2022-01-01":].resample("W-FRI").last().dropna(subset=["usdjpy", "us2", "jp2"])
w["lfx"] = np.log(w.usdjpy) * 100; w["sp2"] = w.us2 - w.jp2; w["slope"] = w.jp30 - w.jp2
cal = w.loc["2022-01":"2025-04"]
mw = sm.OLS(cal.lfx, sm.add_constant(cal[["sp2"]])).fit()
w["fit"] = mw.predict(sm.add_constant(w[["sp2"]])); w["gap"] = w.lfx - w.fit
w.to_csv("weekly.csv")
tabs.append(coef_table(mw, "週次水準_金利差モデル_2022.1-2025.4"))
p = w.loc["2025-05":]; tabs.append(coef_table(ols(p.gap, p[["slope"]], 8), "週次_乖離をカーブの傾きに回帰_2025.5-"))

dw = w.diff().dropna()
for nm, (a, b) in {"週次変化_2022.1-2025.9": ("2022-01", "2025-09"),
                   "週次変化_2025.10-2026.7": ("2025-10", "2026-07")}.items():
    x = dw.loc[a:b]
    tabs.append(coef_table(ols(x.lfx, x[["sp2"]], 4), nm + "_金利差のみ"))
    tabs.append(coef_table(ols(x.lfx, x[["us10", "jp10"]], 4), nm + "_日米10年"))
# 係数差の検定：政権期ダミーとの交差項（切片・米10年・日本10年）
x = dw.loc["2022-01":"2026-07"].copy()
x["D"] = (x.index >= "2025-10-01").astype(float)
x["D_us10"] = x.D * x.us10; x["D_jp10"] = x.D * x.jp10
tabs.append(coef_table(ols(x.lfx, x[["us10", "jp10", "D", "D_us10", "D_jp10"]], 4), "週次変化_政権期交差項"))

# =============================================================
# B. 月次：要因分解モデル
# =============================================================
b = pd.read_csv("bop.csv", index_col=0, parse_dates=True) / 1e4          # 億円→兆円
jm = j.resample("MS").mean()
x = pd.DataFrame(index=b.index)
# デジタル関連収支（日本銀行の定義）：著作権等使用料＋通信・コンピュータ・情報サービス＋専門・経営コンサルティングサービス
x["dig"] = (b.COPY + b.ICT + b.CONS).rolling(12).sum()
# 再投資収益を除いた直接投資ネット：(資産−資産側再投資)−(負債−負債側再投資) = ネット − RA + RL
x["fdi"] = (b.FDI - b.FDI_reinv_A + b.FDI_reinv_L).rolling(12).sum()
x["tb"] = b.TB.rolling(12).sum(); x["eq"] = b.EQ_A.rolling(12).sum()
x = x.join(pd.read_csv("monthly_us.csv", index_col=0, parse_dates=True)).join(jm)
x = x.join(pd.read_csv("jpcpi.csv", index_col=0, parse_dates=True))
x["lfx"] = np.log(x.fx) * 100; x["oil"] = np.log(x.brent) * 100
x["slope"] = x.jp30 - x.jp2; x["sp2"] = x.us2 - x.jp2
x["rsp2"] = (x.us2 - x.us_core) - (x.jp2 - x.jp_cc)       # 足元のコア物価で調整した2年金利差（代理指標）
x = x.loc["2015-01":"2026-09"].asfreq("MS")               # 暦月を保持（2025年10月は米CPI未公表で欠測）

C = ["rsp2", "slope", "dig", "fdi", "oil"]
def lvl(cols, a="2015-01", z="2026-09"):
    d = x.loc[a:z, ["lfx"] + cols].dropna()
    return ols(d.lfx, d[cols], 12)
def d12(cols, a="2015-01", z="2026-09"):
    d = x[["lfx"] + cols].diff(12)                        # 暦月での前年差
    d = d.loc[a:z]; d = d[d.index.month.isin([1, 4, 7, 10])].dropna()
    return ols(d.lfx, d[cols], 4)

m = lvl(C); tabs.append(coef_table(m, "月次水準_2015.1-2026.9"))
md = d12(C); tabs.append(coef_table(md, "月次前年差_2015.1-2026.9"))
tabs.append(coef_table(lvl(C, z="2021-12"), "月次水準_2015.1-2021.12"))
tabs.append(coef_table(lvl(C, a="2022-01"), "月次水準_2022.1-2026.9"))
C2 = C + ["tb", "eq"]; m2 = lvl(C2); tabs.append(coef_table(m2, "月次水準_貿易収支・対外株式追加"))
tabs.append(coef_table(d12(C2), "月次前年差_貿易収支・対外株式追加"))
C3 = ["sp2", "slope", "dig", "fdi", "oil"]; m3 = lvl(C3); tabs.append(coef_table(m3, "月次水準_名目2年金利差"))
m4 = lvl(C, a="2017-01"); tabs.append(coef_table(m4, "月次水準_2017.1-2026.9"))
pd.concat(tabs).round(4).to_csv("regression_results.csv")

# 単位根・共和分（Engle-Granger：水準回帰の残差のADF。臨界値は通常のADFより厳しい）
rows = []
for v in ["lfx"] + C:
    s = x[v].dropna(); r = adfuller(s, regression="c", autolag="AIC", result_object=False)
    r2 = adfuller(s.diff().dropna(), regression="c", autolag="AIC", result_object=False)
    rows.append({"series": v, "ADF_level_stat": r[0], "ADF_level_p": r[1], "ADF_diff_stat": r2[0], "ADF_diff_p": r2[1]})
res = x.loc["2015-01":"2026-09", ["lfx"] + C].dropna()
resid = res.lfx - sm.add_constant(res[C]) @ m.params
r = adfuller(resid, regression="n", autolag="AIC", result_object=False)
# MacKinnon (2010) の共和分臨界値（定数あり、変数6個＝被説明変数＋説明変数5、標本の大きさで補正）
from statsmodels.tsa.adfvalues import mackinnoncrit
cv = mackinnoncrit(N=6, regression="c", nobs=len(resid))
rows.append({"series": "EG残差（定数あり・6変数）", "ADF_level_stat": r[0], "ADF_level_p": np.nan,
             "ADF_diff_stat": cv[1], "ADF_diff_p": cv[2]})   # 列を流用：5%臨界値、10%臨界値
pd.DataFrame(rows).round(3).to_csv("unitroot.csv", index=False)

# 要因分解（対数ポイント）
def decomp(model, cols, a, z, name):
    dl = x.loc[z] - x.loc[a]; c = {k: model.params[k] * dl[k] for k in cols}
    out = {"spec": name, "start": a[:7], "end": z[:7], "actual_logpt": dl.lfx,
           "actual_pct": (x.loc[z, "fx"] / x.loc[a, "fx"] - 1) * 100, **c}
    out["resid"] = dl.lfx - sum(c.values()); return out
P = [("2021-12-01", "2026-09-01"), ("2025-09-01", "2026-09-01"),
     ("2025-09-01", "2026-02-01"), ("2026-02-01", "2026-09-01")]
rows = [decomp(m, C, a, z, "基本") for a, z in P]
rows += [decomp(m2, C2, a, z, "貿易収支・対外株式追加") for a, z in P]
rows += [decomp(m3, C3, a, z, "名目2年金利差") for a, z in P]
rows += [decomp(m4, C, a, z, "推計2017年から") for a, z in P]
rows += [decomp(md, C, a, z, "前年差モデルの係数") for a, z in P]
dec = pd.DataFrame(rows).round(1); dec.to_csv("decomposition.csv", index=False)
x["fit"] = (sm.add_constant(x[C]) @ m.params); x.to_csv("monthly.csv")

# =============================================================
# C. 財政ニュースのイベントスタディ（日次、東京市場の時点にそろえる）
# =============================================================
fx = pd.read_csv("usdjpy_tokyo17.csv", index_col=0, parse_dates=True).usdjpy_tokyo17
us = pd.read_csv("daily_us_fx.csv", index_col=0, parse_dates=True)[["us2", "us10", "us30"]]
d = pd.DataFrame({"fx": np.log(fx) * 100}).join(j, how="inner")       # 東京17時の為替と国債の東京終値
d = d.join(us.reindex(d.index, method="ffill").shift(1))             # 前日のニューヨーク終値（東京の当日より前に確定）
d = d.dropna()
dd = d.diff().dropna()
dd["us2"] = d.us2.diff().reindex(dd.index); dd["us10"] = d.us10.diff().reindex(dd.index)
est = dd.loc["2023-01-01":"2025-09-30"]
mk = ols(est.fx, est[["us2", "us10"]], 5); tabs_ev = [coef_table(mk, "日次_米金利による為替の期待変化_2023.1-2025.9")]
dd["ab"] = dd.fx - sm.add_constant(dd[["us2", "us10"]]) @ mk.params        # 異常変化（米金利で説明できない円の動き）
dd.to_csv("daily.csv")
ab2 = dd.ab.rolling(2).sum()                                               # 2営業日の累積
sd2 = ab2.loc["2023-01-01":"2025-09-30"].std()

# 事前に定めたイベント：最初に市場が反応できる東京の営業日を0日目とし、0〜1日目の2営業日で測る
EV = [
    ("2025-10-06", "拡張", "自民党総裁選で高市氏が勝利（10月4日・土）"),
    ("2025-11-07", "拡張", "単年度PB目標の取り下げを国会で答弁"),
    ("2025-11-21", "拡張", "総合経済対策（国費等21.3兆円）を閣議決定"),
    ("2025-12-26", "規律", "2026年度予算案を閣議決定（PB黒字、新規国債30兆円未満）"),
    ("2026-01-19", "拡張", "食料品消費税ゼロの検討報道（17日・土）と首相会見（19日夜）"),
    ("2026-02-09", "規律", "衆院選で与党圧勝、首相が「赤字国債に頼らず」と表明"),
    ("2026-07-31", "拡張", "食料品消費税1%（2027年4月から2年）を首相が表明（30日夜）"),
    ("2026-08-05", "拡張", "政府が食料品消費税1%の方針を決定"),
    ("2026-10-19", "拡張", "財源について「国債発行を否定するものではない」と答弁"),
]
# 為替介入日（2024年4・5・7月、2026年7月30日・31日、8月3日）を含む窓は、介入の影響と区別できないため集計から除く
INTERV = pd.to_datetime(["2024-04-29", "2024-05-01", "2024-07-11", "2024-07-12",
                         "2026-07-30", "2026-07-31", "2026-08-03"])
rows = []
for day, kind, label in EV:
    t0 = dd.index[dd.index >= day][0]; i = dd.index.get_loc(t0); win = dd.iloc[i:i + 2]
    rows.append({"date": t0.date(), "kind": kind, "event": label,
                 "intervention": bool(win.index.isin(INTERV).any()),
                 "fx_raw": win.fx.sum(), "fx_abnormal": win.ab.sum(), "z": win.ab.sum() / sd2,
                 "jp30": win.jp30.sum() * 100, "jp10": win.jp10.sum() * 100, "jp2": win.jp2.sum() * 100,
                 "us2_prevNY": win.us2.sum() * 100})
ev = pd.DataFrame(rows).round(2); ev.to_csv("events.csv", index=False)
# 拡張ニュースの平均と、ランダムな日付との比較（並べ替え）
exp = ev[(ev.kind == "拡張") & (~ev.intervention)]; k = len(exp)
bad = ab2.index.isin(INTERV) | ab2.index.isin(INTERV + pd.offsets.BDay(1))
pool = ab2[~bad].loc["2023-01-01":"2026-11-30"].dropna().values
rng = np.random.default_rng(0)
sims = np.array([rng.choice(pool, k, replace=False).mean() for _ in range(20000)])
summ = {"拡張ニュースの数（介入を除く）": k, "拡張_異常変化の平均": exp.fx_abnormal.mean(),
        "拡張_30年金利の平均変化bp": exp.jp30.mean(),
        "並べ替えp値（片側、円安方向）": (sims >= exp.fx_abnormal.mean()).mean(),
        "拡張_30年金利の並べ替えp値（片側、上昇方向）": np.nan,
        "拡張_異常変化の合計": exp.fx_abnormal.sum(),
        "規律_異常変化の平均": ev[ev.kind == "規律"].fx_abnormal.mean(),
        "2営業日異常変化の標準偏差（2023.1-2025.9）": sd2}
j30 = d.jp30.diff().rolling(2).sum() * 100
j30 = j30[~(j30.index.isin(INTERV) | j30.index.isin(INTERV + pd.offsets.BDay(1)))].loc["2023-01-01":"2026-11-30"].dropna().values
sims30 = np.array([rng.choice(j30, k, replace=False).mean() for _ in range(20000)])
summ["拡張_30年金利の並べ替えp値（片側、上昇方向）"] = (sims30 >= exp.jp30.mean()).mean()
summ["2営業日30年金利変化の標準偏差bp"] = j30.std()
# 1月の解散・減税報道の前後（1月9日〜23日）の累積
summ["2026.1.9-1.23_異常変化の累積"] = dd.loc["2026-01-09":"2026-01-23"].ab.sum()
summ["2026.1.9-1.23_30年金利の累積変化bp"] = dd.loc["2026-01-09":"2026-01-23"].jp30.sum() * 100
pd.Series(summ).round(3).to_csv("events_summary.csv", header=["value"])

# 日次の符号分類（Jarociński and Karadi 2020 の符号制約の考え方を応用）：
#  異常変化（円安＝プラス）と30年金利の変化が同符号 → 「財政型」（金利上昇と円安が同時）
#  異符号 → 「金融型」（金利上昇で円高。通常の金利差の関係）
dd["type"] = np.where(np.sign(dd.ab) == np.sign(dd.jp30), "財政型", "金融型")
dd.loc[(dd.ab == 0) | (dd.jp30 == 0), "type"] = "その他"
rows = []
for nm, (a, z) in {"2023.1-2025.9": ("2023-01-01", "2025-09-30"),
                   "2025.10-2026.2": ("2025-10-01", "2026-02-27"),
                   "2026.3-2026.11": ("2026-03-01", "2026-11-30")}.items():
    s = dd.loc[a:z]
    r = {"period": nm, "days": len(s), "fx_total": s.fx.sum(), "ab_total": s.ab.sum()}
    for t in ["財政型", "金融型"]:
        ss = s[s.type == t]; r[f"{t}_days"] = len(ss); r[f"{t}_ab"] = ss.ab.sum(); r[f"{t}_ab_per_day"] = ss.ab.mean()
    rows.append(r)
pd.DataFrame(rows).round(2).to_csv("signclass.csv", index=False)
dd.to_csv("daily.csv")
pd.concat(tabs + tabs_ev).round(4).to_csv("regression_results.csv")

if __name__ == "__main__":
    pd.set_option("display.width", 250)
    print(pd.concat(tabs + tabs_ev).round(3).to_string())
    print(pd.read_csv("unitroot.csv").to_string())
    print(dec.to_string())
    print(ev.to_string()); print(pd.Series(summ).round(3)); print(pd.read_csv("signclass.csv").to_string())
    print(x.loc[["2021-12-01", "2025-09-01", "2026-02-01", "2026-09-01"], ["fx", "rsp2", "slope", "dig", "fdi", "brent"]].round(2))
    print("gap", w.gap.loc["2025-04"].mean(), w.gap.loc["2025-09"].mean(), w.gap.max(), w.gap.idxmax(), w.gap.iloc[-1], w.index[-1],
          np.exp(w.fit.iloc[-1] / 100), w.usdjpy.iloc[-1], (np.exp(w.gap.iloc[-1] / 100) - 1) * 100)
