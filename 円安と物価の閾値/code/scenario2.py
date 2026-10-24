import sys
import numpy as np, pandas as pd, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
sys.path.insert(0, '/mnt/skills/plugins/boj-api')
from scripts.boj_api import setup_japanese_font

setup_japanese_font()
df = pd.read_csv('quarterly.csv', index_col=0)
df.index = pd.PeriodIndex(df.index, freq='Q')
lvl = df['fx_level'].dropna()
est = pd.read_pickle('est2.pkl')
Q = lambda s: pd.Period(s, 'Q')
DAIWA = dict(lin=0.047, lo=0.031, hi=0.055, tau=13.2, eff={155: 0.12, 160: 0.22, 165: 0.41, 170: 0.63})


def pt(e):
    p = e['nl'].params
    return dict(lin=e['lin'].params['fx_b'], lo=p['fx_b'], hi=p['fx_b'] + p['fx_g'], tau=e['taus']['fx'])


def path(last_actual, fill, X, end):
    s = lvl.loc[:last_actual].copy(); t = Q(last_actual) + 1
    while t <= Q(end):
        s[t] = fill.get(str(t), X); t += 1
    return (s / s.shift(4) - 1) * 100


def effect(c, f):
    """大和方式：その四半期のドル円前年比 × パススルー率（閾値超なら β+γ）→ 年平均"""
    return float((np.where(f > c['tau'], c['hi'], c['lo']) * f).mean()), float((c['lin'] * f).mean())


def run(e, last_actual, fill, year, scen, end):
    c = pt(e); yrs = pd.period_range(f'{year}Q1', f'{year}Q4', freq='Q')
    res, paths = {}, {}
    for X in scen:
        p = path(last_actual, fill, X, end); paths[X] = p
        nl, li = effect(c, p.loc[yrs])
        dw, _ = effect(DAIWA, p.loc[yrs])
        res[X] = dict(nl=nl, lin=li, daiwa_coef=dw, fx_avg=p.loc[yrs].mean(), fx_peak=p.loc[yrs].max())
    return pd.DataFrame(res).T, paths, c


def figure(title, c, res, paths, last_actual, year, fname, colors, show_daiwa=True):
    fig, ax = plt.subplots(1, 3, figsize=(15, 5.3), gridspec_kw={'width_ratios': [1, 1.25, 1.1]})
    a = ax[0]
    a.bar(0, c['lin'], color='#b9d7b5', edgecolor='gray', width=0.6)
    a.bar(1, c['lo'], color='#a8443f', edgecolor='gray', width=0.6)
    a.bar(1, c['hi'] - c['lo'], bottom=c['lo'], color='white', edgecolor='#d88', hatch='///', width=0.6)
    a.annotate('', xy=(1, c['hi'] * 0.97), xytext=(1, c['lo'] * 1.05),
               arrowprops=dict(arrowstyle='simple,head_width=0.8,tail_width=0.4', fc='#fff27a', ec='#aa9'))
    a.text(0, c['lin'] + 0.0008, f"{c['lin']:.3f}", ha='center', va='bottom')
    a.text(1.08, c['hi'] + 0.0008, f"{c['hi']:.3f}", ha='left', va='bottom')
    a.text(1, c['lo'] / 2, f"{c['lo']:.3f}\n(閾値未満)", ha='center', va='center', fontsize=9,
           bbox=dict(facecolor='white', edgecolor='none'))
    if show_daiwa:
        a.scatter([0, 1, 1], [DAIWA['lin'], DAIWA['lo'], DAIWA['hi']], facecolor='white', edgecolor='#c0392b',
                  s=45, zorder=5, label='大和総研')
        a.legend(fontsize=9, loc='upper left')
    a.set_xticks([0, 1]); a.set_xticklabels(['線形モデル', '非線形モデル'])
    a.set_ylim(0, 0.065); a.set_title('（パススルー率、%pt）', fontsize=11)

    a = ax[1]
    act = df['fx'].loc['2022Q1':last_actual]
    a.plot([p.year + (p.quarter - 1) / 4 for p in act.index], act.values, color='black', lw=2, label='実績')
    for X, col in zip(paths, colors):
        p = paths[X].loc[last_actual:]
        a.plot([q.year + (q.quarter - 1) / 4 for q in p.index], p.values, '--', color=col, lw=1.8, label=f'{X}円')
    a.axhline(c['tau'], color='#8b1a1a', ls=':', lw=1.5)
    a.text(2022.6, c['tau'] + 1, f"閾値（{c['tau']:.1f}%）", color='#8b1a1a',
           bbox=dict(facecolor='white', edgecolor='#8b1a1a', boxstyle='round'))
    a.axhline(0, color='black', lw=0.8); a.legend(ncol=2, fontsize=9)
    a.set_title('ドル円レート（前年比、%）', fontsize=11)

    a = ax[2]
    xs = list(res.index)
    a.bar(range(len(xs)), res['nl'], color=colors, edgecolor='black')
    for i, v in enumerate(res['nl']):
        a.text(i + 0.12, max(v, 0) + 0.008, f'{v:.2f}', ha='left', va='bottom')
    a.scatter(range(len(xs)), res['lin'], color='black', marker='_', s=400, zorder=3, label='線形モデル')
    if show_daiwa:
        dv = [DAIWA['eff'].get(x, np.nan) for x in xs]
        a.scatter(range(len(xs)), dv, facecolor='white', edgecolor='#c0392b', s=45, zorder=4, label='大和総研（公表値）')
    a.set_xticks(range(len(xs))); a.set_xticklabels([f'{x}円' for x in xs])
    a.axhline(0, color='black', lw=0.8); a.legend(fontsize=9, loc='upper left')
    a.set_title(f'円安シナリオ別 {year}年の物価押し上げ（%pt）', fontsize=11)
    fig.suptitle(title, fontsize=13); fig.tight_layout(); fig.savefig(fname, dpi=150)


if __name__ == '__main__':
    c4 = ['#f0a050', '#7cc35a', '#4f86e0', '#e24aa0']
    # 再現：2025Q4 実績、2026年は X 円で横ばい
    r1, p1, c1 = run(est['daiwa'], '2025Q4', {}, 2026, [155, 160, 165, 170], '2026Q4')
    figure('図表3の再推計（推計期間1990Q1–2025Q3、佐々木・山本・中島(2023)の定式化）',
           c1, r1, p1, '2025Q4', 2026, 'fig2_replica.png', c4)
    # 更新：2026Q3 実績、2026Q4=158円（10月平均）、2027年は X 円で横ばい
    r2, p2, c2 = run(est['update'], '2026Q3', {'2026Q4': 158.0}, 2027, [155, 160, 165, 170, 180], '2027Q4')
    figure('データ更新版（推計期間1990Q1–2026Q2、2027年の円安シナリオ）',
           c2, r2, p2, '2026Q3', 2027, 'fig2_update.png', c4 + ['#8e44ad'], show_daiwa=False)
    # 2026年（実績＋10月水準）
    f = path('2026Q3', {'2026Q4': 158.0}, 158.0, '2026Q4').loc['2026Q1':'2026Q4']
    print('2026年実績ベース', [round(x, 1) for x in f], effect(c2, f))
    print(pd.concat({'2026年(再現)': r1, '2027年(更新)': r2}).round(3))
    pd.concat({'replica_2026': r1, 'update_2027': r2}).to_csv('scenario2_results.csv')
