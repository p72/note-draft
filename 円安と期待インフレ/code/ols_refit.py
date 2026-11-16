import numpy as np, pandas as pd
from math import erf, sqrt
df = pd.read_csv("/home/hatch/workspace/bei-replication/lasso_dataset.csv", index_col=0)
df.index = pd.PeriodIndex(df.index, freq="Q")

def ols(data, y, xs, hac=4):
    Xd = data[xs].astype(float).values; yd = data[y].astype(float).values
    X = np.column_stack([np.ones(len(data)), Xd]); names = ["const"]+xs
    beta, *_ = np.linalg.lstsq(X, yd, rcond=None); u = yd - X@beta
    n, k = X.shape; r2 = 1-(u@u)/(((yd-yd.mean())**2).sum()); adj = 1-(1-r2)*(n-1)/(n-k)
    Xi = np.linalg.inv(X.T@X); S = (X*u[:,None]).T@(X*u[:,None])
    for L in range(1, hac+1):
        w = 1-L/(hac+1); G = (X[L:]*u[L:,None]).T@(X[:-L]*u[:-L,None]); S += w*(G+G.T)
    se = np.sqrt(np.diag(Xi@S@Xi))
    print(f"n={n} R2={r2:.4f} adjR2={adj:.4f}")
    for i, nm in enumerate(names):
        t = beta[i]/se[i]; p = 2*(1-0.5*(1+erf(abs(t)/sqrt(2))))
        print(f"  {nm:10s} {beta[i]: .4f} (HAC se {se[i]:.4f}, t={t:.2f}, p={p:.3g})")
    return dict(zip(names, beta)), r2, adj, X@beta

print("=== OLS refit: logFX ~ US2y + JP BEI + Jitsuju(A), quarterly 2015Q1-2026Q2 ===")
b, r2, adj, fit = ols(df, "logfx", ["us2", "jpbei", "jitsuju"])
df["fit"] = np.exp(fit)
last = df.loc["2026Q2"]; base = df.loc["2021Q4"]
print(f"\n2026Q2: actual={last['fx']:.2f}  fitted={last['fit']:.2f}")
print(f"2021Q4: actual={base['fx']:.2f}  fitted={base['fit']:.2f}")
print("\nContribution decomposition 2021Q4 -> 2026Q2 (log pts and yen at 2021Q4 FX):")
tot_log = 0
for x, nm in [("us2","米2年金利"), ("jpbei","日本期待インフレ"), ("jitsuju","実需")]:
    c = b[x] * (last[x] - base[x]); tot_log += c
    print(f"  {nm}: beta {b[x]:+.3f} x delta {last[x]-base[x]:+.3f} -> {c:+.3f} log pts = {c*base['fx']:+.1f} yen")
print(f"  Sum of contributions: {tot_log:+.3f} log pts = {tot_log*base['fx']:+.1f} yen")
print(f"  Actual change: {last['logfx']-base['logfx']:+.3f} log pts ({base['fx']:.1f} -> {last['fx']:.1f} yen, +{last['fx']-base['fx']:.1f})")
print(f"  Fitted change: {np.log(last['fit'])-np.log(base['fit']):+.3f} log pts")
df.to_csv("/home/hatch/workspace/bei-replication/lasso_dataset_fitted.csv")

print("\n=== Robustness: Jitsuju B ===")
b2, r2b, adjb, fitb = ols(df, "logfx", ["us2", "jpbei", "jitsuju_B"])
print(f"2026Q2 fitted (B) = {np.exp(fitb[-1]):.2f}")
print("\n=== Robustness: full 6-var OLS (for reference) ===")
ols(df, "logfx", ["us2","jp2","usbei","jpbei","fiscal","jitsuju"])
