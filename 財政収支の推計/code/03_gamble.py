# -*- coding: utf-8 -*-
"""
小黒一正ほか『財政破綻後』図2-1「財政ギャンブル失敗の確率」の近似再現と現在版への更新

原典: 小黒一正 (2009)「ギャンブルとしての財政赤字に関する一考察」『日本経済研究』No.60, pp.19-35
      (手法は Ball, Elmendorf & Mankiw (1998) "The Deficit Gamble" に倣う)

モデル:
  債務残高比率の遷移式   b_t = X_t * b_{t-1} - pb
  X_t = (1 + r_t) / (1 + g_t)   (r: 実効金利の近似としての長期金利、g: 名目GDP成長率)
  log X は AR(1):  logX_t = mu + rho * (logX_{t-1} - mu) + e_t,  e_t ~ N(0, sigma_e^2)
  基礎的財政収支 pb と初期債務 b0 は期間を通じて固定。5000本の経路で4指標の到達確率を数える。

4指標 (原図の定義):
  (1) 20年後に債務比率が初期値の1.5倍以上
  (2) 30年後に初期値の2倍以上
  (3) 10年後に300%超
  (4) 50年後に400%超

X過程のパラメータについて:
  国別の歴史データ (長期金利: FRED/OECD IRLTLT01 年平均、名目GDP: 世界銀行、1960-2016年) から
  X を作ると、国別仕様では原図を再現できない (平均絶対誤差 0.133-0.152、03_history_specs.py)。
  4か国プールの歴史値 (logX 平均 +0.0013、標準偏差 0.0278) から組んだAR(1)過程でも誤差は 0.041 に留まる。
  mu=0、rho=0.3、イノベーション標準偏差 0.03 (定常標準偏差 約0.031) の「共通過程」に較正すると
  原図16指標との平均絶対誤差 0.0061、最大誤差 0.0346 まで近似できる (20万本では 0.0065/0.0303、
  別シードの5000本では 0.0055)。非自明な10指標に限ると 0.0097。
  すなわち原図の国間差は、国別の r-g 過程を持ち込まなくても初期条件の差だけで説明できる。
  ただしこの較正は原図の数値からの逆算を含む。小黒 (2009) のパラメータ表による確認は未了である。
  乱数シードは全か国・全ケース共通 (777、共通乱数)。logX の初期値は平均 mu に置く。

初期条件の出典:
  A: 原図公表値 (小黒のアゴラ記事 2018-01-07 が示す2016年値)
  B: IMF WEO 2026年10月号の2016年値 (現行系列。日本の債務定義は旧系列から遡及改定されている)
  C: IMF WEO 2026年10月号の2025年値 (推計値。2026年は見通しのため基準年に使わない)
  D: 同2024年値 (頑健性チェック用)
  債務 = GGXWDG_NGDP、基礎的収支 = GGXONLB_NGDP、いずれも対GDP比 (%)。
  WEOは新データポータルのSDMX API (api.imf.org/external/sdmx/2.1/data/WEO/...) から取得した。

実行: python3 03_gamble.py   (numpy のみ)
"""
import numpy as np

MU, RHO, INNOV = 0.0, 0.3, 0.03  # 共通X過程 (logX の AR(1)) -- 較正値

# (初期債務比率, 基礎的収支) いずれも対GDP比の小数表記
INIT = {
    "A_2016_原図公表値": {
        "Germany": (0.680, +0.018), "Japan": (2.400, -0.039),
        "UK": (0.900, -0.013), "US": (1.070, -0.023)},
    "B_2016_WEO現行系列": {
        "Germany": (0.681, +0.0206), "Japan": (2.021, -0.0253),
        "UK": (0.872, -0.0167), "US": (1.075, -0.0237)},
    "C_2025_WEO最新": {
        "Germany": (0.627, -0.0206), "Japan": (2.048, -0.0051),
        "UK": (1.021, -0.0267), "US": (1.244, -0.0388)},
    "D_2024_WEO_頑健性": {
        "Germany": (0.614, -0.0192), "Japan": (2.136, -0.0154),
        "UK": (0.994, -0.0398), "US": (1.223, -0.0463)},
}

# 原図 (図2-1) の転記値
ORIGINAL = {
    "Germany": (0.0, 0.0, 0.0, 0.0),
    "Japan": (0.2132, 0.0512, 0.2434, 0.6530),
    "UK": (0.1954, 0.0542, 0.0, 0.0006),
    "US": (0.3946, 0.1578, 0.0, 0.0070),
}


def simulate(b0, pb, nsim=5000, seed=777, years=50):
    """債務比率の経路を nsim 本生成し、4指標の到達確率を返す。"""
    rng = np.random.default_rng(seed)
    logx = np.empty((nsim, years))
    prev = np.full(nsim, MU)
    for t in range(years):
        prev = MU + RHO * (prev - MU) + rng.normal(0.0, INNOV, size=nsim)
        logx[:, t] = prev
    x = np.exp(logx)
    b = np.empty((nsim, years + 1))
    b[:, 0] = b0
    for t in range(1, years + 1):
        b[:, t] = x[:, t - 1] * b[:, t - 1] - pb
    return (float(np.mean(b[:, 20] >= 1.5 * b0)),
            float(np.mean(b[:, 30] >= 2.0 * b0)),
            float(np.mean(b[:, 10] >= 3.0)),
            float(np.mean(b[:, 50] >= 4.0)))


def main():
    for label, init in INIT.items():
        print(f"--- {label}")
        errs = []
        for country, (b0, pb) in init.items():
            p = simulate(b0, pb)
            print(f"  {country:8s} b0={b0*100:6.1f}%  pb={pb*100:+.2f}%  -> "
                  f"{p[0]:.4f} {p[1]:.4f} {p[2]:.4f} {p[3]:.4f}")
            if label.startswith("A_"):
                errs += [abs(a - b) for a, b in zip(p, ORIGINAL[country])]
        if errs:
            print(f"  原図との平均絶対誤差 = {np.mean(errs):.4f}、最大誤差 = {np.max(errs):.4f}")


if __name__ == "__main__":
    main()
