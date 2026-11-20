# -*- coding: utf-8 -*-
"""
歴史データから構築した X = (1+r)/(1+g) による仕様比較 (記事 第2節・表2の再現)

入力: ../03_x_history.csv
  (長期金利: FRED経由のOECD長期金利 IRLTLT01 年平均、名目GDP成長率: 世界銀行の名目GDPから計算。
   日本の長期金利は1989年開始のため標本が短い)
比較する仕様 (いずれも原図の2016年初期条件・5000本・seed=777 で原図16指標との誤差を測る):
  1. ar1_country     : 国別に logX のAR(1)を推計し、国別の過程でシミュレーション
  2. iid_normal      : 国別に X を正規分布 (歴史平均・標準偏差) から独立抽出
  3. bootstrap       : 国別の歴史 X を復元抽出
  4. ar1_pooled_hist : 4か国プールの歴史値 (mu=0.0013, rho=0.588, innov=0.0225) の共通過程
較正した共通過程 (mu=0, rho=0.3, innov=0.03) 本体は 03_gamble.py を参照。
実行: python3 03_history_specs.py   (numpy, pandas)
"""
import numpy as np, pandas as pd, os

HERE = os.path.dirname(os.path.abspath(__file__))
ORIGINAL = {"Germany": (0.0,0.0,0.0,0.0), "Japan": (0.2132,0.0512,0.2434,0.6530),
            "UK": (0.1954,0.0542,0.0,0.0006), "US": (0.3946,0.1578,0.0,0.0070)}
INIT = {"Germany": (0.68,0.018), "Japan": (2.40,-0.039), "UK": (0.90,-0.013), "US": (1.07,-0.023)}
COUNTRIES = ["Germany","Japan","UK","US"]

def metrics_from_x(x, b0, pb):
    nsim = x.shape[0]
    b = np.empty((nsim, 51)); b[:,0] = b0
    for t in range(1, 51): b[:,t] = x[:,t-1]*b[:,t-1] - pb
    return (float(np.mean(b[:,20]>=1.5*b0)), float(np.mean(b[:,30]>=2*b0)),
            float(np.mean(b[:,10]>=3.0)), float(np.mean(b[:,50]>=4.0)))

def ar1_draws(mu, rho, innov, nsim, seed, years=50):
    rng = np.random.default_rng(seed)
    logx = np.empty((nsim, years)); prev = np.full(nsim, mu)
    for t in range(years):
        prev = mu + rho*(prev-mu) + rng.normal(0.0, innov, size=nsim); logx[:,t] = prev
    return np.exp(logx)

def report(label, results):
    errs = [abs(a-b) for c in COUNTRIES for a,b in zip(results[c], ORIGINAL[c])]
    print(f"--- {label}  MAE={np.mean(errs):.4f} MAX={np.max(errs):.4f}")
    for c in COUNTRIES: print(f"   {c:8s} {np.round(results[c],4)}")

def main():
    df = pd.read_csv(os.path.join(HERE, "..", "03_x_history.csv"))
    df = df[df["year"] <= 2016]
    xs = {c: df[df["country"]==c].sort_values("year")["X"].to_numpy() for c in COUNTRIES}

    print("=== 表2: 歴史 X の要約")
    params = {}
    for c in COUNTRIES:
        x = xs[c]; lx = np.log(x)
        y, xl = lx[1:], lx[:-1]
        A = np.vstack([np.ones_like(xl), xl]).T
        (a, rho), *_ = np.linalg.lstsq(A, y, rcond=None)
        resid = y - A @ np.array([a, rho])
        innov = float(resid.std(ddof=2)); mu = float(a/(1-rho))
        params[c] = (mu, float(rho), innov)
        print(f"   {c:8s} mean={x.mean():.4f} sd={x.std(ddof=1):.4f} n={len(x)}"
              f"  AR(1): mu={mu:+.4f} rho={rho:+.3f} innov={innov:.4f}")

    nsim, seed = 5000, 777
    report("ar1_country (国別AR(1))",
           {c: metrics_from_x(ar1_draws(*params[c], nsim, seed), *INIT[c]) for c in COUNTRIES})

    res = {}
    for c in COUNTRIES:
        rng = np.random.default_rng(seed)
        res[c] = metrics_from_x(rng.normal(xs[c].mean(), xs[c].std(ddof=1), size=(nsim,50)), *INIT[c])
    report("iid_normal (国別・正規iid)", res)

    res = {}
    for c in COUNTRIES:
        rng = np.random.default_rng(seed)
        res[c] = metrics_from_x(rng.choice(xs[c], size=(nsim,50), replace=True), *INIT[c])
    report("bootstrap (国別・復元抽出)", res)

    report("ar1_pooled_hist (mu=0.0013, rho=0.588, innov=0.0225)",
           {c: metrics_from_x(ar1_draws(0.0013, 0.588, 0.0225, nsim, seed), *INIT[c]) for c in COUNTRIES})

if __name__ == "__main__":
    main()
