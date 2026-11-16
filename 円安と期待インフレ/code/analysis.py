import sys, numpy as np, pandas as pd
sys.path.insert(0, "/home/hatch/workspace/custom-skills/fred-data")
from scripts.fred_data import get_fred, describe_series, source_note

bei = pd.read_csv("/home/hatch/workspace/bei-replication/bei_monthly.csv", parse_dates=["date"])
bei["ym"] = bei["date"].dt.to_period("M")
print("BEI months:", len(bei), bei["ym"].min(), "->", bei["ym"].max())
allm = pd.period_range("2015-01","2026-07", freq="M")
print("missing months:", [str(p) for p in allm if p not in set(bei["ym"])])

fx = get_fred("DEXJPUS", start="2014-12-01", end="2026-08-31", frequency="m", aggregation_method="eop")
us2 = get_fred("DGS2", start="2014-12-01", end="2026-08-31", frequency="m", aggregation_method="eop")
print(describe_series(fx)); print(describe_series(us2))
dfx = pd.DataFrame({"fx": fx}); dfx["ym"]=dfx.index.to_period("M")
du = pd.DataFrame({"us2": us2}); du["ym"]=du.index.to_period("M")
df = bei.merge(dfx, on="ym", how="inner").merge(du, on="ym", how="inner").sort_values("ym")
df["logfx"] = np.log(df["fx"])
print(df[["ym","BEI","fx","us2"]].head(3)); print(df[["ym","BEI","fx","us2"]].tail(3)); print("merged n=", len(df))
df.to_csv("/home/hatch/workspace/bei-replication/merged_monthly.csv", index=False)

def ols(data, y, xs, label, hac=3):
    import numpy as _np
    Xd = data[xs].astype(float).values; yd = data[y].astype(float).values
    X = _np.column_stack([_np.ones(len(data)), Xd]); names=["const"]+xs
    beta, res, *_ = _np.linalg.lstsq(X, yd, rcond=None)
    u = yd - X@beta; n, k = X.shape
    r2 = 1 - (u@u)/(((yd-yd.mean())**2).sum()); adj = 1-(1-r2)*(n-1)/(n-k)
    # Newey-West
    XtX_inv = _np.linalg.inv(X.T@X)
    S = (X*u[:,None]).T@(X*u[:,None])
    for L in range(1, hac+1):
        w = 1 - L/(hac+1)
        G = (X[L:]*u[L:,None]).T@(X[:-L]*u[:-L,None])
        S += w*(G+G.T)
    cov = XtX_inv@S@XtX_inv; se = _np.sqrt(_np.diag(cov))
    from math import erf, sqrt
    print(f"\n### {label}  n={n}  R2={r2:.3f} adjR2={adj:.3f}")
    params={}
    for i,name in enumerate(names):
        t = beta[i]/se[i]; p = 2*(1-0.5*(1+erf(abs(t)/sqrt(2))))
        params[name]=beta[i]
        print(f"  {name:8s} {beta[i]: .4f}  (HAC se {se[i]:.4f}, t={t:.2f}, p={p:.3g})")
    class R: pass
    r=R(); r.params=params; return r

full = df.copy()
pre = df[df["ym"] <= "2021-12"]; post = df[df["ym"] >= "2022-01"]
r1 = ols(full, "logfx", ["BEI"], "LEVEL full 2015-2026: logFX ~ JP BEI")
r2 = ols(full, "logfx", ["BEI","us2"], "LEVEL full: logFX ~ JP BEI + US2y")
r3 = ols(pre, "logfx", ["BEI","us2"], "LEVEL 2015-2021: logFX ~ JP BEI + US2y")
r4 = ols(post, "logfx", ["BEI","us2"], "LEVEL 2022-2026: logFX ~ JP BEI + US2y")
r5 = ols(pre, "logfx", ["BEI"], "LEVEL 2015-2021: logFX ~ JP BEI only")
r6 = ols(post, "logfx", ["BEI"], "LEVEL 2022-2026: logFX ~ JP BEI only")

for c in ["logfx","BEI","us2"]:
    full[c+"_d"] = full[c].diff()
    full[c+"_d12"] = full[c].diff(12)
d1 = full.dropna()
ols(d1, "logfx_d", ["BEI_d"], "DIFF monthly full: dlogFX ~ dBEI")
ols(d1, "logfx_d", ["BEI_d","us2_d"], "DIFF monthly full: dlogFX ~ dBEI + dUS2y")
ols(d1[d1["ym"]<="2021-12"], "logfx_d", ["BEI_d","us2_d"], "DIFF monthly 2015-2021")
ols(d1[d1["ym"]>="2022-01"], "logfx_d", ["BEI_d","us2_d"], "DIFF monthly 2022-2026")
d12 = full.dropna(subset=["logfx_d12","BEI_d12","us2_d12"])
ols(d12, "logfx_d12", ["BEI_d12","us2_d12"], "DIFF 12m full: d12logFX ~ d12BEI + d12US2y")

# correlations
print("\nCorr level:", full[["logfx","BEI","us2"]].corr().round(3).to_string())
print("Corr diff :", d1[["logfx_d","BEI_d","us2_d"]].corr().round(3).to_string())

# fitted at end from level model r2
last = full.iloc[-1]
fit = r2.params["const"] + r2.params["BEI"]*last["BEI"] + r2.params["us2"]*last["us2"]
print(f"\nLast month {last['ym']}: actual FX={last['fx']:.2f}, BEI={last['BEI']:.3f}, US2y={last['us2']:.2f}")
print(f"Level model (BEI+US2y, full sample) fitted FX at last month = {np.exp(fit):.1f}")
fit1 = r1.params["const"] + r1.params["BEI"]*last["BEI"]
print(f"BEI-only level model fitted FX at last month = {np.exp(fit1):.1f}")
# 2021-12 -> 2026-07 decomposition with r2
base = full[full["ym"]=="2021-12"].iloc[0]
print(f"\n2021-12: FX={base['fx']:.1f} BEI={base['BEI']:.3f} US2y={base['us2']:.2f}")
print(f"Change 2021-12->last: dlogFX={last['logfx']-base['logfx']:.3f} (FX {base['fx']:.0f}->{last['fx']:.0f})")
print(f"  BEI contribution (level model): {r2.params['BEI']*(last['BEI']-base['BEI']):.3f} log pts")
print(f"  US2y contribution: {r2.params['us2']*(last['us2']-base['us2']):.3f} log pts")
print("\nSOURCE NOTE:", source_note(fx, us2))
