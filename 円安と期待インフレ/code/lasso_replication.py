import sys, numpy as np, pandas as pd
sys.path.insert(0, "/home/hatch/workspace/custom-skills/fred-data")
sys.path.insert(0, "/home/hatch/workspace/custom-skills/mof-jgb")
from scripts.fred_data import get_fred
from scripts.mof_jgb import get_yields

m = pd.read_csv("/home/hatch/workspace/bei-replication/merged_monthly.csv", parse_dates=["date"])
m["q"] = m["date"].dt.to_period("Q")
q_end = m[m["date"].dt.month.isin([3,6,9,12])].copy()
qdf = pd.DataFrame({"q": q_end["q"], "fx": q_end["fx"], "us2": q_end["us2"], "jpbei": q_end["BEI"]}).set_index("q")
qdf["logfx"] = np.log(qdf["fx"])

yd = get_yields("2014-12-01", "2026-07-31")
yme = yd.resample("M").last()
yq = yme[yme.index.month.isin([3,6,9,12])].copy()
yq.index = yq.index.to_period("Q")
qdf["jp2"] = yq[2].reindex(qdf.index)
qdf["spread3010"] = (yq[30] - yq[10]).reindex(qdf.index)

usbei = get_fred("T10YIE", start="2014-12-01", end="2026-08-31", frequency="m", aggregation_method="eop")
ub = pd.Series(usbei.values, index=usbei.index.to_period("Q")).groupby(level=0).last()
qdf["usbei"] = ub.reindex(qdf.index)

jit = pd.read_csv("/home/hatch/workspace/bei-replication/jitsuju_quarterly.csv", index_col=0)
jit.index = pd.PeriodIndex(jit.index, freq="Q")
qdf["jitsuju"] = jit["jitsuju_A"].reindex(qdf.index)
qdf["jitsuju_B"] = jit["jitsuju_B"].reindex(qdf.index)
qdf["fiscal"] = qdf["spread3010"] * (qdf.index >= pd.Period("2025Q4", freq="Q")).astype(float)

df = qdf.loc["2015Q1":"2026Q2"].dropna()
print(df.round(3).to_string())
print("n =", len(df))
df.to_csv("/home/hatch/workspace/bei-replication/lasso_dataset.csv")

# ---------- LASSO by coordinate descent ----------
def lasso_path(Xs, yc, n_lam=100, eps=1e-3):
    n, p = Xs.shape
    lam_max = np.max(np.abs(Xs.T @ yc)) / n
    lams = np.exp(np.linspace(np.log(lam_max), np.log(lam_max*eps), n_lam))
    betas = np.zeros((n_lam, p)); b = np.zeros(p)
    for i, lam in enumerate(lams):
        for _ in range(1000):
            b_old = b.copy()
            r = yc - Xs @ b
            for j in range(p):
                r += Xs[:, j] * b[j]
                rho = Xs[:, j] @ r / n
                b[j] = np.sign(rho) * max(abs(rho) - lam, 0.0)  # columns standardized to unit variance (ddof=0 -> X'X/n diag=1)
                r -= Xs[:, j] * b[j]
            if np.max(np.abs(b - b_old)) < 1e-8: break
        betas[i] = b
    return lams, betas

def run_lasso(data, jcol, seed, label):
    Xcols = ["us2", "jp2", "usbei", "jpbei", "fiscal", jcol]
    names = ["米2年金利", "日本2年金利", "米期待インフレ", "日本期待インフレ", "財政懸念", "実需"]
    X = data[Xcols].values.astype(float); y = data["logfx"].values.astype(float)
    mu, sd = X.mean(0), X.std(0); ym = y.mean()
    Xs, yc = (X - mu) / sd, y - ym
    lams, betas = lasso_path(Xs, yc)
    rng = np.random.RandomState(seed)
    fold = rng.randint(0, 5, len(data))
    mses = np.zeros(len(lams))
    for f in range(5):
        tr, te = fold != f, fold == f
        mu_f, sd_f, ym_f = X[tr].mean(0), X[tr].std(0), y[tr].mean()
        _, bf = lasso_path((X[tr]-mu_f)/sd_f, y[tr]-ym_f) if False else (None, None)
        # recompute path on train fold with same lambda grid (approx: use full-sample grid)
        Xtr, ytr = (X[tr]-mu_f)/sd_f, y[tr]-ym_f
        # path for train fold
        n_tr = tr.sum(); lam_max_f = np.max(np.abs(Xtr.T @ ytr))/n_tr
        lams_f = np.exp(np.linspace(np.log(lam_max_f), np.log(lam_max_f*1e-3), len(lams)))
        _, betas_f = lasso_path(Xtr, ytr)
        # map fold lambdas onto common grid by index (same relative grid)
        pred = ym_f + ((X[te]-mu_f)/sd_f) @ betas_f.T
        mses += ((y[te][:,None] - pred)**2).sum(0)
    mses /= len(data)
    i_min = int(np.argmin(mses))
    # SE at min across folds: recompute per-fold mse at i_min roughly via total (use sqrt(mse/5) approx not exact) -> use per-fold values
    # proper per-fold mse at each lambda:
    fold_mse = np.zeros((5, len(lams)))
    for f in range(5):
        tr, te = fold != f, fold == f
        mu_f, sd_f, ym_f = X[tr].mean(0), X[tr].std(0), y[tr].mean()
        Xtr, ytr = (X[tr]-mu_f)/sd_f, y[tr]-ym_f
        _, betas_f = lasso_path(Xtr, ytr)
        pred = ym_f + ((X[te]-mu_f)/sd_f) @ betas_f.T
        fold_mse[f] = ((y[te][:,None]-pred)**2).mean(0)
    se_min = fold_mse[:, i_min].std(ddof=1) / np.sqrt(5)
    thresh = mses[i_min] + se_min
    cand = [i for i in range(len(lams)) if mses[i] <= thresh]
    i_1se = min(cand)  # largest lambda = smallest index
    sel_min = [names[j] for j in range(6) if abs(betas[i_min][j]) > 1e-10]
    sel_1se = [names[j] for j in range(6) if abs(betas[i_1se][j]) > 1e-10]
    print(f"\n=== {label} (seed={seed}) ===")
    print(f"lambda_min={lams[i_min]:.4f} CV-MSE={mses[i_min]:.5f} selected: {sel_min}")
    print(f"lambda_1se={lams[i_1se]:.4f} (thresh {thresh:.5f}) selected: {sel_1se}")
    print("coef@1se (std):", {names[j]: round(float(betas[i_1se][j]),4) for j in range(6) if abs(betas[i_1se][j])>1e-10})
    return Xcols, names, sel_1se, i_1se, lams, betas

res = run_lasso(df, "jitsuju", 42, "実需=変種A（受取ベース調整）")
for seed in [1, 2026]:
    run_lasso(df, "jitsuju", seed, "実需=変種A seed感応")
run_lasso(df, "jitsuju_B", 42, "実需=変種B（ネットベース調整）")
