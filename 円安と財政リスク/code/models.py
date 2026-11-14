"""推計：週次の金利差モデル（図1）と月次の要因分解モデル（図2・図3、表1・表2）。"""
import numpy as np, pandas as pd, statsmodels.api as sm

def ols(y, X, lags):
    return sm.OLS(y, sm.add_constant(X)).fit(cov_type="HAC", cov_kwds={"maxlags": lags})

def coef_table(m, name):
    return pd.DataFrame({"model": name, "coef": m.params, "t": m.tvalues, "R2": m.rsquared, "n": int(m.nobs)})

# ---- 週次：日米2年金利差モデルの乖離 ----
j = pd.read_csv("jgb_daily.csv", index_col=0, parse_dates=True)
u = pd.read_csv("daily_us_fx.csv", index_col=0, parse_dates=True)
w = u.join(j, how="outer").ffill().loc["2022-01-01":].resample("W-FRI").last().dropna()
w["lfx"] = np.log(w.usdjpy) * 100; w["sp2"] = w.us2 - w.jp2; w["slope"] = w.jp30 - w.jp2
cal = w.loc["2022-01":"2025-04"]
mw = sm.OLS(cal.lfx, sm.add_constant(cal[["sp2"]])).fit()
w["fit"] = mw.predict(sm.add_constant(w[["sp2"]])); w["gap"] = w.lfx - w.fit
w.to_csv("weekly.csv")
tabs = []
dw = w.diff().dropna()
for nm, (a, b) in {"週次変化_2022.1-2025.9": ("2022-01", "2025-09"),
                   "週次変化_2025.10-2026.7": ("2025-10", "2026-07")}.items():
    x = dw.loc[a:b]
    tabs.append(coef_table(ols(x.lfx, x[["sp2"]], 4), nm + "_金利差のみ"))
    tabs.append(coef_table(ols(x.lfx, x[["us10", "jp10"]], 4), nm + "_日米10年"))

# ---- 月次：要因分解モデル ----
b = pd.read_csv("bop.csv", index_col=0, parse_dates=True) / 1e4          # 億円→兆円
jm = j.resample("MS").mean()
x = pd.DataFrame(index=b.index)
x["dig"] = (b.IP + b.ICT + b.OBS).rolling(12).sum()                     # デジタル収支（12か月累計）
x["fdi"] = (b.FDI - b.FDI_reinv_A).rolling(12).sum()                     # 直接投資の現金流出（再投資収益を除く）
x["tb"] = b.TB.rolling(12).sum(); x["eq"] = b.EQ_A.rolling(12).sum()
x = x.join(pd.read_csv("monthly_us.csv", index_col=0, parse_dates=True)).join(jm)
x = x.join(pd.read_csv("jpcpi.csv", index_col=0, parse_dates=True)).dropna()
x["lfx"] = np.log(x.fx) * 100; x["oil"] = np.log(x.brent) * 100
x["slope"] = x.jp30 - x.jp2
x["rsp2"] = (x.us2 - x.us_core) - (x.jp2 - x.jp_cc)                      # 実質2年金利差（事後）
x = x.loc["2015-01":"2026-09"]
C = ["rsp2", "slope", "dig", "fdi", "oil"]
m = ols(x.lfx, x[C], 12); tabs.append(coef_table(m, "月次水準_2015.1-2026.9"))
d12 = x[["lfx"] + C].diff(12).dropna().iloc[::3]
tabs.append(coef_table(ols(d12.lfx, d12[C], 4), "月次前年差_2015.1-2026.9"))
pre = x.loc[:"2021-12"]; tabs.append(coef_table(ols(pre.lfx, pre[C], 12), "月次水準_2015.1-2021.12"))
C2 = ["rsp2", "slope", "dig", "fdi", "oil", "tb", "eq"]
tabs.append(coef_table(ols(x.lfx, x[C2], 12), "月次水準_貿易収支・対外株式追加"))
pd.concat(tabs).round(3).to_csv("regression_results.csv")
x["fit"] = m.fittedvalues; x.to_csv("monthly.csv")

rows = []
for a, z in [("2021-12-01", "2026-09-01"), ("2025-09-01", "2026-09-01"),
             ("2025-09-01", "2026-02-01"), ("2026-02-01", "2026-09-01")]:
    dl = x.loc[z] - x.loc[a]; c = {k: m.params[k] * dl[k] for k in C}
    rows.append({"start": a[:7], "end": z[:7], "actual": dl.lfx, **c, "resid": dl.lfx - sum(c.values())})
dec = pd.DataFrame(rows).round(1); dec.to_csv("decomposition.csv", index=False)
print(pd.concat(tabs).round(2).to_string()); print(dec.to_string())
print(x.loc[["2021-12-01", "2025-09-01", "2026-02-01", "2026-09-01"], ["fx", "rsp2", "slope", "dig", "fdi", "brent"]].round(2))
print(w.gap.loc["2025-04"].mean(), w.gap.loc["2025-09"].mean(), w.gap.max(), w.gap.idxmax(), w.gap.iloc[-1], w.index[-1])
p = w.loc["2025-05":]; mg = ols(p.gap, p[["slope"]], 8); print("gap~slope", mg.params.round(2).to_dict(), mg.tvalues.round(1).to_dict(), round(mg.rsquared, 2))
