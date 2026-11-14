"""推計：週次の金利差モデル（図1・表1）、月次の要因分解モデル（図2・図3・表2〜表4）、
財政ニュースのイベントスタディと日次の記述的な分類（図4・表5・表6）。

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
x["trend"] = np.arange(len(x)) / 12.0                      # 時間トレンド（年）
tabs.append(coef_table(lvl(C + ["trend"]), "月次水準_時間トレンド追加"))
m5 = lvl(C, a="2022-01")                                   # 2022年以降の係数（分解の感度用）
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
rows += [decomp(m5, C, a, z, "2022年以降の係数") for a, z in P]
dec = pd.DataFrame(rows).round(1); dec.to_csv("decomposition.csv", index=False)
x["fit"] = (sm.add_constant(x[C]) @ m.params); x.to_csv("monthly.csv")

# =============================================================
# C. 財政ニュースのイベントスタディ（日次、東京市場の時点にそろえる）
# =============================================================
fx = pd.read_csv("usdjpy_tokyo17.csv", index_col=0, parse_dates=True).usdjpy_tokyo17
us = pd.read_csv("daily_us_fx.csv", index_col=0, parse_dates=True)[["us2", "us10"]]
# 東京の営業日（東京17時の為替と国債の東京終値がそろう日）をカレンダーとして固定する
base = pd.DataFrame({"fx": np.log(fx) * 100}).join(j[["jp2", "jp10", "jp30"]], how="inner").dropna()
# 各東京日の前日（暦日）までに確定した最新のニューヨーク終値を対応させる（米国の休場日は有効な直近値）
valid_us = us.dropna()
prev = valid_us.reindex(base.index - pd.Timedelta(days=1), method="ffill"); prev.index = base.index
us30 = pd.read_csv("daily_us_fx.csv", index_col=0, parse_dates=True)["us30"].dropna()
p30 = us30.reindex(base.index - pd.Timedelta(days=1), method="ffill"); p30.index = base.index
d = base.join(prev).join(p30.rename("us30"))
dd = d.diff().iloc[1:]                                          # 東京営業日どうしの差（行を落とさない）
est = dd.loc["2023-01-01":"2025-09-30"].dropna()
mk = ols(est.fx, est[["us2", "us10"]], 5); tabs_ev = [coef_table(mk, "日次_米金利による為替の期待変化_2023.1-2025.9")]
dd["ab"] = dd.fx - sm.add_constant(dd[["us2", "us10"]]) @ mk.params        # 異常変化（米金利で説明できない円の動き）
# 国債30年金利も、前日の米30年金利の変化で説明できる分を除いた「異常変化」を作る（bp）
est30 = dd.loc["2023-01-01":"2025-09-30", ["jp30", "us30"]].dropna() * 100
m30 = ols(est30.jp30, est30[["us30"]], 5); tabs_ev.append(coef_table(m30, "日次_米30年金利による国債30年の期待変化_2023.1-2025.9"))
dd["ab30"] = dd.jp30 * 100 - sm.add_constant(dd[["us30"]] * 100) @ m30.params

# 為替介入日。2営業日の窓（前営業日の東京17時→1日目の東京17時）にこれらの日が入れば介入と重なるとみなす
INTERV = pd.to_datetime(["2024-04-29", "2024-05-01", "2024-07-11", "2024-07-12",
                         "2026-07-30", "2026-07-31", "2026-08-03"])
idx = dd.index
start = pd.Series(d.index[:-1], index=idx)                       # 各リターンの始点（前の東京営業日）
def window_hits(i0, i1):
    lo, hi = start.iloc[i0], idx[i1]
    return bool(((INTERV > lo) & (INTERV <= hi)).any())
ab2 = dd.ab.rolling(2).sum(); j302 = dd.jp30.rolling(2).sum() * 100; a302 = dd.ab30.rolling(2).sum()
hit2 = pd.Series([window_hits(i - 1, i) if i >= 1 else True for i in range(len(idx))], index=idx)
sd2 = ab2[~hit2].loc["2023-01-01":"2025-09-30"].std(); sd30 = j302[~hit2].loc["2023-01-01":"2025-09-30"].std()

# 事前に定めたイベント：最初に市場が反応できる東京の営業日を0日目とし、0〜1日目の2東京営業日で測る
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
rows = []
for day, kind, label in EV:
    i0 = idx.get_indexer([idx[idx >= day][0]])[0]; win = dd.iloc[i0:i0 + 2]
    ok = len(win) == 2 and win[["ab", "jp30"]].notna().all().all()
    rows.append({"date": idx[i0].date(), "day1": idx[i0 + 1].date(), "kind": kind, "event": label,
                 "intervention": window_hits(i0, i0 + 1),
                 "fx_raw": win.fx.sum() if ok else np.nan, "fx_abnormal": win.ab.sum() if ok else np.nan,
                 "z": win.ab.sum() / sd2 if ok else np.nan,
                 "jp30": win.jp30.sum() * 100, "jp30_z": win.jp30.sum() * 100 / sd30,
                 "jp30_abnormal": win.ab30.sum(), "us30_prevNY": win.us30.sum() * 100,
                 "jp10": win.jp10.sum() * 100, "jp2": win.jp2.sum() * 100,
                 "us2_prevNY": win.us2.sum() * 100})
ev = pd.DataFrame(rows).round(2); ev.to_csv("events.csv", index=False)

# ランダムな日付との比較（プラセボ）：介入と重なる窓を除いた2営業日窓から k 件を選ぶ操作を2万回
exp = ev[(ev.kind == "拡張") & (~ev.intervention)]; k = len(exp)
rng = np.random.default_rng(0)
def placebo(series, a, z, stat):
    pool = series[~hit2].loc[a:z].dropna().values
    sims = np.array([rng.choice(pool, k, replace=False).mean() for _ in range(20000)])
    return (sims >= stat).mean()
summ = {"拡張ニュースの数（介入を除く）": k,
        "拡張_異常変化の平均": exp.fx_abnormal.mean(), "拡張_30年金利の平均変化bp": exp.jp30.mean(),
        "p_円_参照2023.1-2026.11": placebo(ab2, "2023-01-01", "2026-11-30", exp.fx_abnormal.mean()),
        "p_30年_参照2023.1-2026.11": placebo(j302, "2023-01-01", "2026-11-30", exp.jp30.mean()),
        "p_円_参照2025.7-2026.11": placebo(ab2, "2025-07-01", "2026-11-30", exp.fx_abnormal.mean()),
        "p_30年_参照2025.7-2026.11": placebo(j302, "2025-07-01", "2026-11-30", exp.jp30.mean()),
        "規律_異常変化の平均": ev[ev.kind == "規律"].fx_abnormal.mean(),
        "2営業日異常変化の標準偏差（2023.1-2025.9）": sd2, "2営業日30年金利変化の標準偏差bp": sd30,
        "推計期間の日数": len(est),
        "2026.1.9-1.23_異常変化の累積": dd.loc["2026-01-09":"2026-01-23"].ab.sum(),
        "2026.1.9-1.23_30年金利の累積変化bp": dd.loc["2026-01-09":"2026-01-23"].jp30.sum() * 100}
# 総裁選翌日（10月6日）を除いた5件（日銀の見通しの変化と重なるため）
ex = exp[exp.date.astype(str) != "2025-10-06"]
def placebo_k(series, a, z, stat, kk):
    pool = series[~hit2].loc[a:z].dropna().values
    sims = np.array([rng.choice(pool, kk, replace=False).mean() for _ in range(20000)])
    return (sims >= stat).mean()
summ["10月6日を除く5件_異常変化の平均"] = ex.fx_abnormal.mean()
summ["10月6日を除く5件_p_円"] = placebo_k(ab2, "2023-01-01", "2026-11-30", ex.fx_abnormal.mean(), len(ex))
summ["10月6日を除く5件_30年金利の平均bp"] = ex.jp30.mean()
summ["10月6日を除く5件_p_30年"] = placebo_k(j302, "2023-01-01", "2026-11-30", ex.jp30.mean(), len(ex))
ex1 = exp[exp.date.astype(str) != "2026-01-19"]
summ["1月19日を除く5件_30年金利の平均bp"] = ex1.jp30.mean()
summ["1月19日を除く5件_p_30年"] = placebo_k(j302, "2023-01-01", "2026-11-30", ex1.jp30.mean(), len(ex1))
summ["1月19日を除く5件_異常変化の平均"] = ex1.fx_abnormal.mean()
summ["拡張_30年金利の異常変化の平均bp"] = exp.jp30_abnormal.mean()
summ["p_30年異常_参照2023.1-2026.11"] = placebo_k(a302, "2023-01-01", "2026-11-30", exp.jp30_abnormal.mean(), k)
summ["1月19日を除く5件_30年金利の異常変化の平均bp"] = ex1.jp30_abnormal.mean()
pd.Series(summ).round(3).to_csv("events_summary.csv", header=["value"])

# 査読後に追加で確認したイベント（事前に決めた9件とは分けて扱う）：「骨太ショック」
POST = [("骨太の方針2026の原案発表（6月30日）", "2026-06-30", "2026-07-01"),
        ("原案発表の翌日から（7月1日〜2日）", "2026-07-01", "2026-07-02"),
        ("骨太ショックの期間（6月30日〜7月9日）", "2026-06-30", "2026-07-09"),
        ("片山財務相の発言（7月10日〜13日）", "2026-07-10", "2026-07-13"),
        ("骨太の方針2026の閣議決定（7月21日〜22日）", "2026-07-21", "2026-07-22")]
rows = []
for label, a, z in POST:
    w_ = dd.loc[a:z]
    rows.append({"window": label, "start": a, "end": z, "days": len(w_), "fx_raw": w_.fx.sum(),
                 "fx_abnormal": w_.ab.sum(), "z_2day_sd": w_.ab.sum() / sd2 if len(w_) == 2 else np.nan,
                 "fx_predicted": (w_.fx - w_.ab).sum(), "const_part": mk.params["const"] * len(w_),
                 "jp30_abnormal": w_.ab30.sum(),
                 "jp30": w_.jp30.sum() * 100, "jp10": w_.jp10.sum() * 100, "jp2": w_.jp2.sum() * 100})
pd.DataFrame(rows).round(2).to_csv("events_posthoc.csv", index=False)

# 日次の記述的な分類：30年金利の変化と異常変化の符号が同じ日・逆の日・どちらかが0の日
dd["type"] = np.where(np.sign(dd.ab) == np.sign(dd.jp30), "同符号", "逆符号")
dd.loc[(dd.ab == 0) | (dd.jp30 == 0) | dd.ab.isna(), "type"] = "その他"
rows = []
for nm, (a, z) in {"2023.1-2025.9": ("2023-01-01", "2025-09-30"),
                   "2025.10-2026.2": ("2025-10-01", "2026-02-27"),
                   "2026.3-2026.11": ("2026-03-01", "2026-11-30")}.items():
    s_ = dd.loc[a:z]
    r = {"period": nm, "days": len(s_), "ab_total": s_.ab.sum()}
    for t in ["同符号", "逆符号", "その他"]:
        ss = s_[s_.type == t]; r[f"{t}_days"] = len(ss); r[f"{t}_ab"] = ss.ab.sum(); r[f"{t}_ab_per_day"] = ss.ab.mean()
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
    c = dd.loc["2025-07-01":].ab.cumsum()
    print("Oct", round(dd.loc["2025-10"].ab.sum(), 2), "Jul-Sep", round(dd.loc["2025-07":"2025-09"].ab.sum(), 2),
          "Jan5", round(c.loc["2026-01-05"], 2), "Feb27", round(c.loc["2026-02-27"], 2), "Oct-Feb", round(dd.loc["2025-10-01":"2026-02-27"].ab.sum(), 2))
    print(x.loc[["2021-12-01", "2025-09-01", "2026-02-01", "2026-09-01"], ["fx", "rsp2", "slope", "dig", "fdi", "brent"]].round(2))
    print("gap", w.gap.loc["2025-04"].mean(), w.gap.loc["2025-09"].mean(), w.gap.max(), w.gap.idxmax(), w.gap.iloc[-1], w.index[-1],
          np.exp(w.fit.iloc[-1] / 100), w.usdjpy.iloc[-1], (np.exp(w.gap.iloc[-1] / 100) - 1) * 100)
