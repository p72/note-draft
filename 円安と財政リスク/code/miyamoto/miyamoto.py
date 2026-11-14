"""宮本（2025、日本銀行WP 25-J-2）の構造VARを公表データで再現する。

論文の仕様（本文で確認できたもの）
- 変数：X_t = [Δi1, …, Δi5, Δs]'（米国債1〜5年の日次変化（%pt）、ドル円の対数日次変化×100）
- VAR(2)、定数項あり、最小二乗法。期間は1995年1月〜2023年9月半ば
- 識別：FOMC公表日などの誘導型残差 u^F = B^F e^F の共分散から B^F（下三角）を求め、
  金利ショックの列に B_n = x_n B^F_n（論文はn=1..5、本稿はn=1..4）の制約を置き、g = vech(BB') − vech(Ω̂) について
  g'Wg を最小化（Wは2段階）
- 要因分解：構造ショック e1..e5 による部分を、VARトレンドからの乖離として示す

本稿の置き換え・仮定（論文本文に記載がない、または公表データで代替したもの）
- 金利：Gürkaynak-Sack-Wright のゼロクーポン金利の代わりに FRED の国債定満期利回り（DGS1・2・3・5）。FREDに4年物がないため、論文の5本ではなく4本（M=4）
- ドル円：Bloomberg の代わりに FRED の DEXJPUS（ニューヨーク正午）
- イベント日：FOMCの政策決定の公表日（臨時を含む）。Glick and Leduc (2018) の重要スピーチ日は含めていない
- ドル円の列：B_6 = x_6 B^F_6（下三角のため、ドル円のショックは同時点の金利に影響しない）
- W：1段階目は単位行列、2段階目は vech(u_t u_t') の分散の逆行列
- 「VARトレンド」：期首の値と定数項による予測。窓の中の構造ショックの寄与を、期首を0として累積する
"""
import sys
import numpy as np, pandas as pd
from scipy.optimize import minimize
from statsmodels.tsa.api import VAR

START, END = "1995-01-01", "2023-09-15"
DEC_START, DEC_END = "2021-01-01", "2023-09-15"
FX = "fred"
for a in sys.argv[1:]:
    k, v = a.split("="); globals()[k] = v

raw = pd.read_csv("us_daily_1994.csv", index_col=0, parse_dates=True)
if FX == "yahoo":     # 終値（発表後の時点）。1996年10月30日から
    y = pd.read_csv("yahoo_jpy.csv", index_col=0, parse_dates=True).iloc[:, 0]
    raw["fx"] = y.reindex(raw.index)
elif FX == "fred_lead":   # NY正午の翌営業日の値を当日の終わりの値とみなす
    raw["fx"] = raw.fx.dropna().shift(-1).reindex(raw.index)
lv = pd.DataFrame({"i1": raw.i1, "i2": raw.i2, "i3": raw.i3, "i5": raw.i5,
                   "s": np.log(raw.fx) * 100}).dropna()
M = 4   # 金利の本数（論文は1〜5年の5本。FREDに4年がないため1・2・3・5年の4本）
X = lv.diff().dropna().loc[START:END]
names = list(X.columns); K = len(names)

res = VAR(X).fit(2, trend="c")
U = res.resid.values; idx = res.resid.index
Omega = U.T @ U / len(U)

fomc = pd.to_datetime(open("fomc_dates.txt").read().split())
ev = sorted({idx[idx >= d][0] for d in fomc if (idx >= d).any() and idx[0] <= d <= idx[-1]})
UF = res.resid.loc[ev].values
SigF = UF.T @ UF / len(UF)
BF = np.linalg.cholesky(SigF)

tri = np.tril_indices(K)
def vech(M): return M[tri]
def Bmat(x): return BF * x[None, :]
def g(x): return vech(Bmat(x) @ Bmat(x).T) - vech(Omega)
def fit(W):
    obj = lambda x: g(x) @ W @ g(x)
    best = None
    for x0 in [np.ones(K), np.full(K, 0.5), np.full(K, 0.3)]:
        r = minimize(obj, x0, method="BFGS")
        if best is None or r.fun < best.fun: best = r
    return best.x
x1 = fit(np.eye(len(tri[0])))
V = np.array([vech(np.outer(u, u)) for u in U]); S = np.cov(V.T)
x2 = fit(np.linalg.pinv(S))
B = Bmat(x2)
if B[0, 0] < 0: B[:, 0] *= -1

# 構造ショック
E = np.linalg.solve(B, U.T).T

# インパルス応答（累積＝水準）
A = res.coefs; H = 250
Psi = [np.eye(K)]
for h in range(1, H + 1):
    P = sum(A[j] @ Psi[h - 1 - j] for j in range(min(2, h)))
    Psi.append(P)
Theta = np.array([P @ B for P in Psi])          # (H+1, K, K)
cum = Theta.cumsum(axis=0)

# 要因分解（窓の中の構造ショックの寄与を累積。期首を0とする）
w = (idx >= DEC_START) & (idx <= DEC_END); wi = np.where(w)[0]
T = len(wi); contrib = np.zeros((T, K, K))     # 時点, 変数, ショック
for t in range(T):
    for j in range(t + 1):
        h = t - j
        if h > H: continue
        contrib[t] += Theta[h] * E[wi[j]][None, :]
cc = contrib.cumsum(axis=0)
actual = X.loc[idx[wi[0]]:idx[wi[-1]], "s"].sum()
fx_rate = cc[-1, K - 1, :M].sum(); fx_own = cc[-1, K - 1, M]
s0 = lv.s.loc[:idx[wi[0]]].iloc[-2]; s1 = lv.s.loc[idx[wi[-1]]]

out = {
    "sample": f"{X.index[0].date()}..{X.index[-1].date()}", "T": len(X), "events": len(ev),
    "x_stage1": np.round(x1, 3).tolist(), "x_stage2": np.round(x2, 3).tolist(),
    "fit_rel_err": float(np.linalg.norm(B @ B.T - Omega) / np.linalg.norm(Omega)),
    "dec_window": f"{idx[wi[0]].date()}..{idx[wi[-1]].date()}",
    "fx_change_logpt": float(s1 - s0), "fx_change_pct": float((np.exp((s1 - s0) / 100) - 1) * 100),
    "contrib_rate_shocks": float(fx_rate), "contrib_fx_shock": float(fx_own),
    "contrib_by_shock": np.round(cc[-1, K - 1, :], 2).tolist(),
    "trend_part": float((s1 - s0) - fx_rate - fx_own),
}
irf = pd.DataFrame({f"{v}_to_e1": cum[:, i, 0] for i, v in enumerate(names)})
irf.to_csv(f"irf_e1_{FX}_{START[:4]}_{END[:4]}.csv")
pd.DataFrame(cc[:, K - 1, :], index=idx[wi], columns=[f"e{k+1}" for k in range(K)]).to_csv(f"hd_fx_{FX}_{DEC_START[:7]}_{DEC_END[:7]}.csv")
for k, v in out.items(): print(k, v)
print("IRF(e1) cumulative at h=0,20,60,250:")
print(irf.iloc[[0, 20, 60, 250]].round(3).to_string())
print("B (rows=vars, cols=shocks):"); print(pd.DataFrame(B, index=names, columns=[f"e{k+1}" for k in range(K)]).round(3).to_string())
