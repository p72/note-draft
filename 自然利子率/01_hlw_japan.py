"""
日本版 HLW（Holston-Laubach-Williams）型 自然利子率の簡易推計
- データ: ESRI QE 実質GDP（季調・年率）、e-Stat CPI 生鮮食品を除く総合、日銀 無担保コールO/N 月平均
- 推計: カルマンフィルタ + 最尤法（λg, λz は固定するHLWの1段簡略版）
"""
import numpy as np, pandas as pd
from scipy.optimize import minimize
from statsmodels.tsa.seasonal import STL

# ---------- データ整形 ----------
gdp = pd.read_csv("gdp.csv", parse_dates=["date"]).set_index("date")["value"]
gdp.index = gdp.index.to_period("Q")

cpi = pd.read_csv("cpi_core_nsa.csv")
cpi["period"] = pd.PeriodIndex(cpi["period"], freq="M")
cpi = cpi.set_index("period")["value"]
cpi_q = cpi.groupby(cpi.index.asfreq("Q")).mean()
cpi_q = cpi_q[cpi_q.index >= pd.Period("1990Q1")]
# 四半期の3か月がそろっていない期は落とす
cnt = cpi.groupby(cpi.index.asfreq("Q")).size()
cpi_q = cpi_q[cnt.reindex(cpi_q.index) == 3]

# 消費税率引き上げの影響を除去（日銀の試算値に基づく近似）
TAX = {"1997Q2": 1.5, "2014Q2": 2.0, "2019Q4": 1.0}
adj = pd.Series(1.0, index=cpi_q.index)
for q, eff in TAX.items():
    adj[adj.index >= pd.Period(q)] *= (1 + eff / 100)
lcpi = np.log(cpi_q / adj)
lcpi_sa = lcpi - STL(lcpi, period=4, robust=True).fit().seasonal
pi = 400 * lcpi_sa.diff()                      # 年率換算の四半期インフレ率(%)

call = pd.read_csv("call.csv", parse_dates=["date"]).set_index("date")["STRACLUCON"]
call.index = call.index.to_period("M")
i_q = call.groupby(call.index.asfreq("Q")).mean()

df = pd.DataFrame({"y": 100 * np.log(gdp), "pi": pi, "i": i_q}).dropna()
df["pie"] = df["pi"].rolling(4).mean()          # 期待インフレ（過去4期平均, HLW流）
df["r"] = df["i"] - df["pie"]                    # 事前実質金利
df["pi_lag24"] = df["pi"].shift(2).rolling(3).mean()
for k in (1, 2):
    df[f"y_l{k}"] = df["y"].shift(k); df[f"r_l{k}"] = df["r"].shift(k)
df["pi_l1"] = df["pi"].shift(1)
df["d_cv2"] = (df.index == pd.Period("2020Q2")).astype(float)
df["d_cv3"] = (df.index == pd.Period("2020Q3")).astype(float)
df["d_cv4"] = (df.index == pd.Period("2020Q4")).astype(float)
data = df.dropna().copy()
T = len(data)

# ---------- 状態空間 ----------
# s_t = [y*_t, y*_{t-1}, y*_{t-2}, g_{t-1}, g_{t-2}, z_{t-1}, z_{t-2}]
F = np.zeros((7, 7))
F[0, 0] = 1; F[0, 3] = 1
F[1, 0] = 1; F[2, 1] = 1
F[3, 3] = 1; F[4, 3] = 1
F[5, 5] = 1; F[6, 5] = 1
Rm = np.zeros((7, 3)); Rm[0, 0] = 1; Rm[0, 1] = 1; Rm[3, 1] = 1; Rm[5, 2] = 1

# 初期値: 最初の期のHP的なトレンド（単純な線形トレンドで代用）
y0 = df["y"].dropna()
gq0 = (y0.iloc[16] - y0.iloc[0]) / 16
x0_base = np.array([data["y_l1"].iloc[0] + gq0 * 0, data["y_l1"].iloc[0] - gq0,
                    data["y_l2"].iloc[0] - gq0, gq0, gq0, 0.0, 0.0])
P0 = np.diag([0.5, 0.5, 0.5, 0.05, 0.05, 1.0, 1.0])

Y = data[["y", "pi"]].values
NAMES = ["a1", "a2", "ar", "bpi", "by", "s1", "s2", "sys", "dcv2", "dcv3", "dcv4"]


def build(th, lam_g, lam_z):
    a1, a2, ar, bpi, by, s1, s2, sys_, d2, d3, d4 = th
    sg = lam_g * sys_
    sz = lam_z   # zショックの標準偏差を直接指定（日本はarが小さくHLW流のλz定義だとσzが過大になるため）
    Q = Rm @ np.diag([sys_**2, sg**2, sz**2]) @ Rm.T
    H = np.zeros((2, 7))
    H[0] = [1, -a1, -a2, -2 * ar, -2 * ar, -ar / 2, -ar / 2]
    H[1, 1] = -by
    X = data
    c = np.column_stack([
        a1 * X.y_l1 + a2 * X.y_l2 + ar / 2 * (X.r_l1 + X.r_l2) + d2 * X.d_cv2 + d3 * X.d_cv3 + d4 * X.d_cv4,
        bpi * X.pi_l1 + (1 - bpi) * X.pi_lag24 + by * X.y_l1,
    ])
    Rv = np.diag([s1**2, s2**2])
    return H, c, Q, Rv


def kalman(th, lam_g, lam_z, smooth=False):
    H, c, Q, Rv = build(th, lam_g, lam_z)
    x = x0_base.copy(); P = P0.copy()
    ll = 0.0
    xp_s, Pp_s, xf_s, Pf_s = [], [], [], []
    for t in range(T):
        # predict（t=0は初期値をそのまま予測値に）
        if t > 0:
            x = F @ x; P = F @ P @ F.T + Q
        xp_s.append(x.copy()); Pp_s.append(P.copy())
        v = Y[t] - c[t] - H @ x
        S = H @ P @ H.T + Rv
        Si = np.linalg.inv(S)
        K = P @ H.T @ Si
        x = x + K @ v; P = (np.eye(7) - K @ H) @ P
        xf_s.append(x.copy()); Pf_s.append(P.copy())
        ll += -0.5 * (np.log(np.linalg.det(S)) + v @ Si @ v + 2 * np.log(2 * np.pi))
    if not smooth:
        return ll, np.array(xf_s), np.array(Pf_s)
    # RTS スムーザー
    xs = np.array(xf_s); Ps = np.array(Pf_s)
    for t in range(T - 2, -1, -1):
        J = Pf_s[t] @ F.T @ np.linalg.inv(Pp_s[t + 1])
        xs[t] = xf_s[t] + J @ (xs[t + 1] - xp_s[t + 1])
        Ps[t] = Pf_s[t] + J @ (Ps[t + 1] - Pp_s[t + 1]) @ J.T
    return ll, np.array(xf_s), np.array(Pf_s), xs, Ps


# ゼロ金利期が長い日本では最尤法だけだと ar→0, σ1→0（ギャップが消える）に潰れるため、
# IS・フィリップス曲線の傾きと潜在GDPショックに緩い事前分布を置く（MAP推定）
PRIOR = {"ar": (-0.10, 0.05), "by": (0.10, 0.05), "sys": (0.40, 0.15), "s1": (0.60, 0.30)}
def log_prior(th):
    d = dict(zip(NAMES, th)); lp = 0.0
    for k, (m, s) in PRIOR.items():
        lp += -0.5 * ((d[k] - m) / s) ** 2
    return lp


def estimate(lam_g, lam_z):
    th0 = np.array([1.2, -0.3, -0.05, 0.4, 0.1, 0.8, 1.5, 0.5, -8, -3, -1])
    bnds = [(-2, 2), (-2, 2), (-1, -0.0025), (0, 1), (0.025, 1), (0.05, 5), (0.05, 10), (0.01, 3),
            (-20, 15), (-20, 15), (-20, 15)]
    f = lambda th: -kalman(th, lam_g, lam_z)[0] - log_prior(th)
    best = None
    for start in [th0, th0 * np.r_[1, 1, 2, 1, 0.5, 1, 1, 0.5, 1, 1, 1]]:
        res = minimize(f, start, method="L-BFGS-B", bounds=bnds, options={"maxiter": 3000})
        if best is None or res.fun < best.fun:
            best = res
    return best


def rstar_from(xs, Ps):
    # r*_{t-1} = 4 g_{t-1} + z_{t-1}（状態は1期ラグ）→ 時点合わせのため1期シフト
    rs = 4 * xs[:, 3] + xs[:, 5]
    var = 16 * Ps[:, 3, 3] + Ps[:, 5, 5] + 8 * Ps[:, 3, 5]
    g_ann = 4 * xs[:, 3]
    idx = data.index - 1
    return pd.DataFrame({"rstar": rs, "rstar_se": np.sqrt(np.maximum(var, 0)),
                         "g": g_ann, "z": xs[:, 5]}, index=idx)


if __name__ == "__main__":
    print("標本:", data.index[0], "〜", data.index[-1], "T =", T)
    out = {}
    grid = [(0.06, 0.10), (0.03, 0.05), (0.10, 0.05), (0.03, 0.20), (0.10, 0.20)]
    for lg, lz in grid:
        res = estimate(lg, lz)
        ll, xf, Pf, xs, Ps = kalman(res.x, lg, lz, smooth=True)
        rf = rstar_from(xf, Pf); rsm = rstar_from(xs, Ps)
        gap = data["y"].values - xs[:, 0]
        out[(lg, lz)] = dict(res=res, filt=rf, smooth=rsm, gap=pd.Series(gap, index=data.index))
        print(f"\nλg={lg}, σz={lz}  logL={-res.fun:.2f}  converged={res.success}")
        print("  ", dict(zip(NAMES, np.round(res.x, 3))))
        print("   r*(片側, 最新):", rf.index[-1], round(rf.rstar.iloc[-1], 2),
              "  r*(両側, 最新):", round(rsm.rstar.iloc[-1], 2),
              "  潜在成長率(両側, 最新):", round(rsm.g.iloc[-1], 2))
    pd.to_pickle(out, "results.pkl")
    pd.to_pickle(data, "data.pkl")
