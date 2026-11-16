import sys, numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, "/home/hatch/workspace/custom-skills/fred-data")
from scripts.fred_data import setup_japanese_font
font = setup_japanese_font()
JP = font is not None
df = pd.read_csv("/home/hatch/workspace/bei-replication/merged_monthly.csv", parse_dates=["date"])
df["logfx"] = np.log(df["fx"])
# OLS level fit BEI+US2y
X = np.column_stack([np.ones(len(df)), df["BEI"], df["us2"]])
beta, *_ = np.linalg.lstsq(X, df["logfx"], rcond=None)
df["fit_fx"] = np.exp(X@beta)
print("level coefs const, BEI, US2y:", beta.round(4))

# d12 with HAC lag 12
def ols_hac(data, y, xs, hac):
    Xd = data[xs].astype(float).values; yd = data[y].astype(float).values
    X = np.column_stack([np.ones(len(data)), Xd])
    b, *_ = np.linalg.lstsq(X, yd, rcond=None); u = yd - X@b
    n,k = X.shape; r2 = 1-(u@u)/(((yd-yd.mean())**2).sum())
    Xi = np.linalg.inv(X.T@X); S = (X*u[:,None]).T@(X*u[:,None])
    for L in range(1, hac+1):
        w = 1-L/(hac+1); G = (X[L:]*u[L:,None]).T@(X[:-L]*u[:-L,None]); S += w*(G+G.T)
    se = np.sqrt(np.diag(Xi@S@Xi))
    print(f"d12 HAC{hac}: n={n} R2={r2:.3f} " + ", ".join(f"{nm}={b[i]:.4f}(se {se[i]:.4f}, t={b[i]/se[i]:.2f})" for i,nm in enumerate(["const"]+xs)))
for c in ["logfx","BEI","us2"]: df[c+"_d12"] = df[c].diff(12)
ols_hac(df.dropna(), "logfx_d12", ["BEI_d12","us2_d12"], 12)

t_fx = "ドル円（月末、左軸）" if JP else "USD/JPY month-end (L)"
t_bei = "日本のBEI 10年（月末、自前計算、右軸）" if JP else "Japan BEI 10y (R)"
fig, axes = plt.subplots(2, 1, figsize=(11, 7.5))
ax = axes[0]
ax.plot(df["date"], df["fx"], color="#1f4e79", lw=1.8, label=t_fx)
ax.plot(df["date"], df["fit_fx"], color="#1f4e79", lw=1.0, ls="--", label=("推計値（BEI+米2年金利、水準回帰）" if JP else "Fitted (BEI+US2y)"))
ax2 = ax.twinx()
ax2.plot(df["date"], df["BEI"], color="#c00000", lw=1.6, label=t_bei)
ax2.set_ylabel("BEI (%)", color="#c00000"); ax.set_ylabel("JPY/USD" if not JP else "円／ドル")
ax.set_title("USD/JPY vs Japan BEI (10y), 2015-2026" if not JP else "ドル円と日本の期待インフレ（BEI 10年）2015〜2026年", fontsize=13)
h1,l1 = ax.get_legend_handles_labels(); h2,l2 = ax2.get_legend_handles_labels()
ax.legend(h1+h2, l1+l2, loc="upper left", fontsize=9, frameon=False)
ax.grid(alpha=0.3)
ax = axes[1]
pre = df[df["date"]<"2022-01-01"]; post = df[df["date"]>="2022-01-01"]
ax.scatter(pre["BEI"], pre["fx"], s=18, color="#7f7f7f", label="2015-2021")
ax.scatter(post["BEI"], post["fx"], s=18, color="#c00000", label="2022-2026")
for sub, col in [(pre,"#7f7f7f"),(post,"#c00000")]:
    b,*_ = np.linalg.lstsq(np.column_stack([np.ones(len(sub)), sub["BEI"]]), sub["fx"], rcond=None)
    xs = np.linspace(sub["BEI"].min(), sub["BEI"].max(), 10)
    ax.plot(xs, b[0]+b[1]*xs, color=col, lw=1.2, ls="--")
ax.set_xlabel("Japan BEI 10y (%)" if not JP else "日本のBEI 10年（%）")
ax.set_ylabel("JPY/USD" if not JP else "ドル円（円）")
ax.set_title("BEI vs USD/JPY scatter by period" if not JP else "BEIとドル円の散布図（期間別）", fontsize=12)
ax.legend(fontsize=9, frameon=False); ax.grid(alpha=0.3)
fig.tight_layout()
fig.savefig("/home/hatch/workspace/bei-replication/bei_usdjpy.svg", )
print("saved png")
