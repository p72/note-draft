"""佐々木・山本・中島（2023, 日銀WP 23-J-5）の(1)式に沿った閾値モデル
  y_t = c + Σ_i β_i x_{i,t-h_i} + Σ_i γ_i x_{i,t-h_i}·I[x_{i,t-h_i} > d_i σ_i] + (ダミー) + ε_t
  - y: 新コアコアCPI前年比、x: 企業物価・ドル円・賃金(平均時給)の前年比
  - 各変数は単一ラグ h（論文=共通h、大和=変数ごとにh）を AIC で 1〜4 から選択
  - d_i = 0.5,…,2.0 のグリッドで RMSE 最小、σ_i は推計期間内の標準偏差
  - 閾値未満のパススルー = β、閾値超過時パススルー = β+γ
  - 論文は消費税調整済みCPIを使用。ここでは消費税等のダミーで代替
"""
import itertools
import numpy as np, pandas as pd
import statsmodels.api as sm

KGRID = np.round(np.arange(0.5, 2.01, 0.1), 1)


def dummies(idx, use=True):
    d = pd.DataFrame(index=idx)
    if not use:
        return d
    def rng(a, b):
        return ((idx >= pd.Period(a, 'Q')) & (idx <= pd.Period(b, 'Q'))).astype(float)
    d['tax1989'] = rng('1989Q2', '1990Q1')
    d['tax1997'] = rng('1997Q2', '1998Q1')
    d['tax2014'] = rng('2014Q2', '2015Q1')
    d['tax2019'] = rng('2019Q4', '2020Q3')   # 消費増税＋幼保無償化
    d['mobile'] = rng('2021Q2', '2022Q1')    # 携帯電話通信料の引き下げ
    return d


def design(df, vars_, h, taus, use_dummy=True):
    X = {}
    for v in vars_:
        x = df[v].shift(h[v])
        X[f'{v}_b'] = x
        if taus is not None:
            X[f'{v}_g'] = x * (x > taus[v]).astype(float)
    X = pd.DataFrame(X).join(dummies(df.index, use_dummy))
    X = X.loc[:, X.abs().sum() > 0]          # 推計期間外のダミーは落とす（後で loc するので仮）
    return sm.add_constant(X)


def fit(df, vars_, h, taus, start, end, use_dummy=True):
    X = design(df, vars_, h, taus, use_dummy).loc[start:end]
    X = X.loc[:, (X != 0).any()]
    y = df['cpi'].loc[start:end]
    return sm.OLS(y, X, missing='raise').fit(cov_type='HAC', cov_kwds={'maxlags': 4})


def grid(df, vars_, h, start, end, sd, use_dummy=True):
    y = df['cpi'].loc[start:end].values
    D = sm.add_constant(dummies(df.index, use_dummy)).loc[start:end]
    D = D.loc[:, (D != 0).any()].values
    xs = {v: df[v].shift(h[v]).loc[start:end].values for v in vars_}
    best = None
    for ks in itertools.product(KGRID, repeat=len(vars_)):
        cols = [D]
        for v, k in zip(vars_, ks):
            x = xs[v]; cols.append(np.column_stack([x, x * (x > k * sd[v])]))
        X = np.hstack(cols)
        beta = np.linalg.lstsq(X, y, rcond=None)[0]
        ssr = ((y - X @ beta) ** 2).sum()
        if best is None or ssr < best[0]:
            best = (ssr, ks, X.shape[1])
    n = len(y)
    aic = n * np.log(best[0] / n) + 2 * best[2]
    return best[1], aic


def estimate(df, vars_, start, end, per_var=True, use_dummy=True):
    sd = df.loc[start:end, vars_].std()
    combos = itertools.product(range(1, 5), repeat=len(vars_)) if per_var else [(k,) * len(vars_) for k in range(1, 5)]
    best = None
    for hs in combos:
        h = dict(zip(vars_, hs))
        ks, aic = grid(df, vars_, h, start, end, sd, use_dummy)
        if best is None or aic < best[0]:
            best = (aic, h, ks)
    _, h, ks = best
    d = dict(zip(vars_, ks))
    taus = {v: d[v] * sd[v] for v in vars_}
    lin = fit(df, vars_, h, None, start, end, use_dummy)
    nl = fit(df, vars_, h, taus, start, end, use_dummy)
    return dict(vars=vars_, h=h, d=d, sd=sd.to_dict(), taus=taus, lin=lin, nl=nl, start=start, end=end)


def summary(e, label):
    nl, lin = e['nl'], e['lin']
    rows = []
    for v in e['vars']:
        b, g = nl.params[f'{v}_b'], nl.params[f'{v}_g']
        tg = nl.t_test(f'{v}_b + {v}_g = 0')
        rows.append(dict(変数=v, ラグh=e['h'][v], d=e['d'][v], 閾値=round(e['taus'][v], 2),
                         線形=round(lin.params[f'{v}_b'], 4), 線形p=round(lin.pvalues[f'{v}_b'], 3),
                         閾値未満β=round(b, 4), βp=round(nl.pvalues[f'{v}_b'], 3),
                         閾値以上γ=round(g, 4), γp=round(nl.pvalues[f'{v}_g'], 3),
                         超過時β_γ=round(b + g, 4), 和p=round(float(tg.pvalue), 3)))
    t = pd.DataFrame(rows).set_index('変数')
    print(f'\n===== {label}  {e["start"]}〜{e["end"]}  n={int(nl.nobs)}  '
          f'AIC 線形{lin.aic:.1f}/非線形{nl.aic:.1f}  R2 {lin.rsquared:.3f}/{nl.rsquared:.3f}')
    print(t.to_string())
    return t


if __name__ == '__main__':
    df = pd.read_csv('quarterly.csv', index_col=0)
    df.index = pd.PeriodIndex(df.index, freq='Q')
    V = ['cgpi', 'fx', 'wage_h']
    out = {}
    # (A) 論文ベースライン再現チェック：1991–2019、共通h
    out['paper'] = estimate(df, V, '1991Q1', '2019Q4', per_var=False)
    summary(out['paper'], '(A) 論文再現：共通ラグ')
    # (B) 大和総研の条件：1990Q1–2025Q3、変数ごとにh
    out['daiwa'] = estimate(df, V, '1990Q1', '2025Q3', per_var=True)
    summary(out['daiwa'], '(B) 大和条件：変数別ラグ')
    # (B') 大和条件だが共通h
    out['daiwa_common'] = estimate(df, V, '1990Q1', '2025Q3', per_var=False)
    summary(out['daiwa_common'], "(B') 大和期間・共通ラグ")
    # (C) データ更新：〜2026Q2
    out['update'] = estimate(df, V, '1990Q1', '2026Q2', per_var=True)
    summary(out['update'], '(C) 更新：〜2026Q2・変数別ラグ')
    pd.to_pickle(out, 'est2.pkl')
