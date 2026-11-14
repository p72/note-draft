"""全期間（1995年1月〜2026年11月）で推計した構造VARによる、2021年以降のドル円の要因分解の図。"""
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
plt.rcParams["font.family"] = "Noto Sans CJK JP"
import miyamoto_boot as mb
lv = mb.load("fred_lead"); X = lv.diff().dropna().loc["1995-01-01":"2026-11-05"]
ev = pd.to_datetime(open("fomc_dates.txt").read().split()).append(pd.to_datetime(open("speech_dates.txt").read().split())).sort_values()
res, B, U, idx = mb.estimate(X, ev)
K = X.shape[1]; M = K - 1; A = res.coefs; H = 400
Psi = [np.eye(K)]
for h in range(1, H + 1): Psi.append(sum(A[j] @ Psi[h - 1 - j] for j in range(min(2, h))))
Th = np.array([P @ B for P in Psi]); E = np.linalg.solve(B, U.T).T
wi = np.where(idx >= "2021-01-01")[0]; T = len(wi)
d = np.zeros((T, K))
for t in range(T):
    for j in range(max(0, t - H), t + 1):
        d[t] += Th[t - j][K - 1] * E[wi[j]]
cum = d.cumsum(axis=0)
out = pd.DataFrame({"米金利ショック": cum[:, :M].sum(1), "その他（ドル円固有のショック）": cum[:, M]}, index=idx[wi])
out["実績（期首からの変化）"] = X.s.loc[idx[wi[0]]:].cumsum().values
out.to_csv("miyamoto_hd_2021_2026.csv")
fig, ax = plt.subplots(figsize=(11, 5.5))
ax.plot(out.index, out["実績（期首からの変化）"], color="k", lw=1.2, label="ドル円の実績（2021年1月からの累積、対数ポイント）")
ax.plot(out.index, out["米金利ショック"], color="tab:blue", label="米国の金利ショックの寄与")
ax.plot(out.index, out["その他（ドル円固有のショック）"], color="tab:red", label="ドル円固有のショックの寄与（日本側の要因などを含む）")
for dd, t in [("2023-09-15", "論文の推計期間の終わり"), ("2025-10-21", "高市政権"), ("2026-02-27", "イラン戦争")]:
    ax.axvline(pd.Timestamp(dd), color="gray", lw=.8, ls="--"); ax.text(pd.Timestamp(dd) + pd.Timedelta(days=8), ax.get_ylim()[0] + 1, t, fontsize=8)
ax.axhline(0, color="k", lw=.5); ax.set_ylabel("対数ポイント")
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.08), ncol=2, fontsize=8, frameon=False)
ax.set_title("宮本（2025）の構造VARを公表データで再現・延長した要因分解（2021年1月〜2026年11月）")
fig.text(.01, .005, "出典：FRB（Gürkaynak-Sack-Wright のゼロクーポン金利1〜5年）、FRED（DEXJPUS）、FOMCの公表日、Glick and Leduc (2018) のスピーチ等の日より作成。VARトレンド（定数項）による部分は図示していない", fontsize=8)
fig.tight_layout(rect=(0, .03, 1, 1)); fig.savefig("01_chart_miyamoto.png", dpi=140)
print(out.iloc[[0, -1]].round(2)); print(out.loc["2023-09-15":"2023-09-15"].round(2)); print(out.loc["2025-09-30":"2025-09-30"].round(2)); print(out.loc["2026-02-27":"2026-02-27"].round(2))
