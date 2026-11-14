"""miyamoto.py と同じ推計を関数化し、残差ブートストラップと仕様の感度を計算する。"""
import numpy as np, pandas as pd, sys
from scipy.optimize import minimize
from statsmodels.tsa.api import VAR
rng = np.random.default_rng(0)

def load(fx="fred_lead"):
    raw = pd.read_csv("us_daily_1994.csv", index_col=0, parse_dates=True)
    if fx == "fred_lead": raw["fx"] = raw.fx.dropna().shift(-1).reindex(raw.index)
    if fx == "yahoo":
        raw["fx"] = pd.read_csv("yahoo_jpy.csv", index_col=0, parse_dates=True).iloc[:, 0].reindex(raw.index)
    lv = pd.DataFrame({"i1": raw.i1, "i2": raw.i2, "i3": raw.i3, "i5": raw.i5, "s": np.log(raw.fx) * 100}).dropna()
    return lv

def estimate(X, ev_dates, p=2):
    K = X.shape[1]; res = VAR(X).fit(p, trend="c")
    U = res.resid.values; idx = res.resid.index
    Om = U.T @ U / len(U)
    ev = sorted({idx[idx >= d][0] for d in ev_dates if idx[0] <= d <= idx[-1] and (idx >= d).any()})
    UF = res.resid.loc[ev].values; BF = np.linalg.cholesky(UF.T @ UF / len(UF))
    tri = np.tril_indices(K)
    g = lambda x: ((BF * x) @ (BF * x).T)[tri] - Om[tri]
    def fit(W):
        best = None
        for x0 in [np.ones(K), np.full(K, .5)]:
            r = minimize(lambda x: g(x) @ W @ g(x), x0, method="BFGS")
            if best is None or r.fun < best.fun: best = r
        return best.x
    fit(np.eye(len(tri[0])))
    S = np.cov(np.array([np.outer(u, u)[tri] for u in U]).T)
    B = BF * fit(np.linalg.pinv(S))
    for k in range(K):
        if B[k, k] < 0: B[:, k] *= -1
    return res, B, U, idx

def decomp(res, B, U, idx, a, z, M=4, H=400):
    K = B.shape[0]; A = res.coefs; p = len(A)
    Psi = [np.eye(K)]
    for h in range(1, H + 1): Psi.append(sum(A[j] @ Psi[h - 1 - j] for j in range(min(p, h))))
    Th = np.array([P @ B for P in Psi]); E = np.linalg.solve(B, U.T).T
    wi = np.where((idx >= a) & (idx <= z))[0]; tot = np.zeros(K)
    for j, t in enumerate(wi):
        h = min(len(wi) - 1 - j, H)       # 打ち切りは H まで（それ以上の応答は0に収束している）
        tot += Th[:h + 1].sum(axis=0)[K - 1] * E[t]
    irf = Th.cumsum(axis=0)[:, :, 0]
    return tot[:M].sum(), tot[M], irf[60, K - 1] / irf[60, 0]

def run(fx="fred_lead", start="1995-01-01", end="2023-09-15", a="2021-01-01", z="2023-09-15", unsched=True, p=2, nboot=0):
    lv = load(fx); X = lv.diff().dropna().loc[start:end]
    ev = pd.to_datetime(open("fomc_dates.txt").read().split())
    if not unsched:
        U_ = pd.to_datetime(["1998-10-15", "2001-01-03", "2001-04-18", "2001-09-17", "2008-01-22", "2008-10-08", "2020-03-03", "2020-03-15"])
        ev = ev[~ev.isin(U_)]
    res, B, U, idx = estimate(X, ev, p)
    rate, own, ratio = decomp(res, B, U, idx, a, z)
    w = X.loc[a:z, "s"]; act = w.sum()
    out = {"fx": fx, "start": start, "end": end, "window": f"{a}..{z}", "unsched": unsched, "p": p,
           "fx_change": act, "rate_shocks": rate, "fx_shock": own, "fx_per_1pp_1y_h60": ratio}
    if nboot:
        # 層別の残差ブートストラップ：FOMC日の残差はFOMC日の間で、それ以外はそれ以外の日の間で引き直す
        # 再推計した係数（A_b, B_b）を実際のデータに当てはめて、実際の歴史の分解を計算する
        draws, ratios = [], []
        c = res.params.values[0]; A = res.coefs; Y0 = X.values[:p]
        is_ev = idx.isin([idx[idx >= d][0] for d in ev if idx[0] <= d <= idx[-1]])
        pos_ev, pos_ne = np.where(is_ev)[0], np.where(~is_ev)[0]
        for bi in range(nboot):
            pick = np.empty(len(U), dtype=int)
            pick[pos_ev] = rng.choice(pos_ev, len(pos_ev)); pick[pos_ne] = rng.choice(pos_ne, len(pos_ne))
            Ub = U[pick]; Y = list(Y0)
            for t in range(len(U)):
                Y.append(c + sum(A[j] @ Y[-1 - j] for j in range(p)) + Ub[t])
            Xb = pd.DataFrame(np.array(Y), index=X.index, columns=X.columns)
            try:
                rb, Bb, _, _ = estimate(Xb, ev, p)
            except Exception:
                continue
            # 実際のデータの残差（再推計した係数による）
            cb = rb.params.values[0]; Ab = rb.coefs; Xa = X.values
            Ua = np.array([Xa[t] - cb - sum(Ab[j] @ Xa[t - 1 - j] for j in range(p)) for t in range(p, len(Xa))])
            r, _, q = decomp(rb, Bb, Ua, X.index[p:], a, z)
            draws.append(r); ratios.append(q)
        qd = np.percentile(draws, [5, 16, 50, 84, 95]); qr = np.percentile(ratios, [5, 50, 95])
        out.update({"boot_n": len(draws), "rate_p5": qd[0], "rate_p16": qd[1], "rate_p50": qd[2], "rate_p84": qd[3], "rate_p95": qd[4],
                    "ratio_p5": qr[0], "ratio_p50": qr[1], "ratio_p95": qr[2]})
    return out

if __name__ == "__main__":
    rows = []
    nb = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    specs = [dict(nboot=nb), dict(start="1996-11-01"), dict(unsched=False), dict(p=1), dict(p=5),
             dict(fx="yahoo", start="1996-11-01"), dict(fx="fred")]
    for s in specs: rows.append(run(**s)); print({k: (round(v, 2) if isinstance(v, float) else v) for k, v in rows[-1].items()})
    pd.DataFrame(rows).round(3).to_csv("miyamoto_sensitivity.csv", index=False)
