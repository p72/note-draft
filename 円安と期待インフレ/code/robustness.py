"""第6節：追加の頑健性チェック
(1) 財務省PDFから読み取ったBEIとJSDA自前BEIの突き合わせ
(2) 3変数モデルの共和分検定（Engle-Granger）
(3) 1階差（四半期変化）での回帰
(4) サンプル外予測（2024年末までで推計し、2025年以降をランダムウォークと比較）
(5) Granger因果性（ドル円⇔BEI、四半期変化）
入力は同じフォルダの lasso_dataset.csv、bei_monthly.csv、mof_bei_monthly.csv。"""
import os, warnings, numpy as np, pandas as pd, statsmodels.api as sm
from statsmodels.tsa.stattools import coint, grangercausalitytests
warnings.filterwarnings("ignore")
H = os.path.dirname(os.path.abspath(__file__))

# (1) BEI の突き合わせ（2019年1月〜2026年7月）
j = pd.read_csv(f"{H}/bei_monthly.csv", parse_dates=["date"]).set_index("date").BEI
j.index = j.index.to_period("M").to_timestamp()
m = pd.read_csv(f"{H}/mof_bei_monthly.csv", index_col=0, parse_dates=True).bei
x = pd.concat({"jsda": j, "mof": m}, axis=1).dropna()
print(f"(1) n={len(x)} 相関={x.corr().iloc[0,1]:.3f} 平均差={(x.mof-x.jsda).mean()*100:.1f}bp 差の標準偏差={(x.mof-x.jsda).std()*100:.1f}bp")

d = pd.read_csv(f"{H}/lasso_dataset.csv", index_col=0)
sel = ["us2", "jpbei", "jitsuju"]
# (2) 共和分
t, p, _ = coint(d.logfx, d[sel], trend="c")
print(f"(2) Engle-Granger t={t:.2f} p={p:.3f}")
# (3) 1階差
dd = d[["logfx"] + sel].diff().dropna()
od = sm.OLS(dd.logfx, sm.add_constant(dd[sel])).fit(cov_type="HAC", cov_kwds={"maxlags": 2})
print("(3) 1階差 R2=%.2f" % od.rsquared); print(pd.DataFrame({"coef": od.params, "p": od.pvalues}).round(3))
# (4) サンプル外
tr, te = d.loc[:"2024Q4"], d.loc["2025Q1":]
ot = sm.OLS(tr.logfx, sm.add_constant(tr[sel])).fit()
pred = np.exp(ot.predict(sm.add_constant(te[sel], has_constant="add")))
rw = d.fx.shift(1).loc["2025Q1":]
rmse = lambda e: np.sqrt((e ** 2).mean())
print(f"(4) RMSE モデル={rmse(pred-te.fx):.1f}円 ランダムウォーク={rmse(rw-te.fx):.1f}円")
print(pd.DataFrame({"実績": te.fx, "予測": pred.round(1), "乖離": (pred - te.fx).round(1)}))
# (5) Granger
g = pd.DataFrame({"dbei": d.jpbei.diff(), "dfx": d.logfx.diff()}).dropna()
a = grangercausalitytests(g[["dbei", "dfx"]], maxlag=2); b = grangercausalitytests(g[["dfx", "dbei"]], maxlag=2)
print("(5) ドル円→BEI p:", [round(a[k][0]["ssr_ftest"][1], 3) for k in (1, 2)],
      " BEI→ドル円 p:", [round(b[k][0]["ssr_ftest"][1], 3) for k in (1, 2)])
