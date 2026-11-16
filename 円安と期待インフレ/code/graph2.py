import sys, numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, "/home/hatch/workspace/custom-skills/fred-data")
from scripts.fred_data import setup_japanese_font
JP = setup_japanese_font() is not None
df = pd.read_csv("/home/hatch/workspace/bei-replication/lasso_dataset_fitted.csv", index_col=0)
df.index = pd.PeriodIndex(df.index, freq="Q")
t = df.index.to_timestamp()
xs = ["us2", "jpbei", "jitsuju"]
X = np.column_stack([np.ones(len(df)), df[xs].astype(float).values])
beta, *_ = np.linalg.lstsq(X, df["logfx"].values, rcond=None)
base_i = df.index.get_loc("2021Q4")
base_fx = df["fx"].iloc[base_i]
contrib = {}
for j, x in enumerate(xs):
    contrib[x] = beta[j+1] * (df[x].values - df[x].values[base_i]) * base_fx  # yen
post = slice(base_i, None)
labels = {"us2": "米2年金利", "jpbei": "日本期待インフレ", "jitsuju": "実需"} if JP else {"us2":"US 2y","jpbei":"JP BEI","jitsuju":"Real demand"}
colors = {"us2": "#1f4e79", "jpbei": "#c00000", "jitsuju": "#548235"}
fig, axes = plt.subplots(2, 1, figsize=(11, 7.5))
ax = axes[0]
ax.plot(t, df["fx"], color="#1f4e79", lw=1.8, label="ドル円（実績、四半期末）" if JP else "USD/JPY actual")
ax.plot(t, df["fit"], color="#c00000", lw=1.4, ls="--", label="推計値（LASSO選択3変数のOLS）" if JP else "Fitted (LASSO 3 vars)")
ax.set_title("ドル円の実績と推計値（再現）2015〜2026年" if JP else "USD/JPY actual vs fitted (replication)", fontsize=13)
ax.set_ylabel("円／ドル" if JP else "JPY/USD"); ax.legend(fontsize=9, frameon=False, loc="upper left"); ax.grid(alpha=0.3)
ax = axes[1]
tt = t[post]; bottom_pos = np.zeros(len(tt)); bottom_neg = np.zeros(len(tt))
for x in xs:
    c = contrib[x][post]
    pos = np.where(c > 0, c, 0); neg = np.where(c < 0, c, 0)
    ax.bar(tt, pos, width=70, bottom=bottom_pos, color=colors[x], label=labels[x]); bottom_pos += pos
    ax.bar(tt, neg, width=70, bottom=bottom_neg, color=colors[x]); bottom_neg += neg
actual_chg = (df["fx"].values - base_fx)[post]
ax.plot(tt, actual_chg, color="black", lw=1.6, marker="o", ms=3, label="実績の変化" if JP else "Actual change")
ax.axhline(0, color="gray", lw=0.8)
ax.set_title("2021年末以降の円安に対する寄与分解（円）" if JP else "Contribution to yen depreciation since end-2021 (JPY)", fontsize=12)
ax.set_ylabel("円" if JP else "JPY"); ax.legend(fontsize=9, frameon=False, ncol=4, loc="upper left"); ax.grid(alpha=0.3)
fig.tight_layout(); fig.savefig("/home/hatch/workspace/bei-replication/lasso_replication.svg")
print("saved; final contribs:", {x: round(float(contrib[x][-1]),1) for x in xs}, "actual:", round(float(actual_chg[-1]),1))
