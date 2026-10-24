import sys, numpy as np, pandas as pd, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
sys.path.insert(0, '/mnt/skills/plugins/boj-api')
from scripts.boj_api import setup_japanese_font; setup_japanese_font()
b = pd.read_csv('boj.csv', index_col=0, parse_dates=True)
fx = b['FXERM07'].copy(); fx.index = fx.index.to_period('M')
fx[pd.Period('2026-10', 'M')] = 158.09          # 10月（21日まで）の日次平均
fx = fx.sort_index()
# 四半期平均ベース（推計と同じ定義）
fq = fx.groupby(fx.index.asfreq('Q')).mean(); fq[pd.Period('2026Q4','Q')] = 158.09
taus = {'大和2024年6月版（12.4%）': 12.4, '大和2025年版（13.2%）': 13.2, '再推計（13.5%）': 13.47}
line = {k: fq.shift(4) * (1 + t / 100) for k, t in taus.items()}
# 翌年分（基準となる前年値が既知の期間）まで延長
idx = pd.period_range('2021Q1', '2027Q4', freq='Q')
tbl = pd.DataFrame({k: [fq.get(q - 4, np.nan) * (1 + t / 100) for q in idx] for k, t in taus.items()}, index=idx)
tbl['実績'] = fq.reindex(idx)
ann = tbl.groupby(tbl.index.year).agg(['min', 'max']).round(1)
print(tbl.loc['2023Q1':].round(1).to_string()); print(ann.loc[2023:].to_string())
tbl.round(2).to_csv('threshold_yen_level.csv')

fig, ax = plt.subplots(figsize=(11, 5.5))
x = lambda ix: [p.year + (p.quarter - 1) / 4 + 0.125 for p in ix]
fm = fx.loc['2021-01':]
ax.plot([p.year + (p.month - 0.5) / 12 for p in fm.index], fm.values, color='black', lw=1.8, label='ドル円（月中平均）')
cols = ['#e67e22', '#c0392b', '#2e86c1']
for (k, t), c in zip(taus.items(), cols):
    s = tbl[k].loc['2022Q1':]
    ax.step(x(s.index), s.values, where='mid', color=c, lw=2, ls='--' if '再推計' in k else '-', label=f'閾値を超える水準：{k}')
ax.axvspan(2026 + 9.5/12, 2028, color='gray', alpha=0.08)
ax.text(2026.85, 128, '2026Q4以降の\n基準値は10月平均\n(158円)で仮置き', fontsize=9, color='gray')
for y, lab in [(2024.42, '2024年6月\nレポート'), (2025.9, '2025年\nレポート')]:
    ax.axvline(y, color='gray', lw=0.8, ls=':'); ax.text(y + 0.03, 182, lab, fontsize=9, color='gray', va='top')
ax.set_ylim(110, 185); ax.set_xlim(2021.9, 2028)
ax.set_ylabel('円/ドル'); ax.grid(alpha=0.3)
ax.set_title('「閾値を超える円安水準」＝ 前年同期のドル円 ×（1＋閾値）の推移（四半期）', fontsize=12)
ax.legend(fontsize=9, loc='lower right'); fig.tight_layout(); fig.savefig('fig_threshold_level.png', dpi=150)
