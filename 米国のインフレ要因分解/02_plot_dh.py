"""Dupor・Hogan方式（ラグ6）の5成分を積み上げ棒グラフにする。
入力：02_data/analysis/sensitivity.csv（02_empirical_analysis.py の出力）
出力：02_chart_dh_lag6.png
"""
from pathlib import Path
import pandas as pd, numpy as np
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
import logging; logging.getLogger('matplotlib.font_manager').setLevel(logging.ERROR)
plt.rcParams['font.family'] = ['Noto Sans CJK JP', 'Hiragino Sans', 'Yu Gothic', 'sans-serif']
HERE = Path(__file__).resolve().parent
d = pd.read_csv(HERE/'02_data'/'analysis'/'sensitivity.csv'); out = HERE/'02_chart_dh_lag6.png'
x = d[d.specification=='lag6'].set_index('period').loc['2015-01':]
t = pd.PeriodIndex(x.index, freq='M').to_timestamp()
comps = [('drift','ドリフト（無ショック経路）','#b0b0b0'),
         ('current_demand','当期の需要ショック','#1f77b4'),('past_demand','過去の需要ショック','#9ecae1'),
         ('current_supply','当期の供給ショック','#e6550d'),('past_supply','過去の供給ショック','#fdae6b')]
fig, ax = plt.subplots(figsize=(12,6))
pos = np.zeros(len(x)); neg = np.zeros(len(x))
for c, lab, col in comps:
    v = x[c].fillna(0).values
    b = np.where(v>=0, pos, neg)
    ax.bar(t, v, width=25, bottom=b, color=col, label=lab)
    pos += np.where(v>=0, v, 0); neg += np.where(v<0, v, 0)
ax.plot(t, x['total'], color='k', lw=1.6, label='インフレ率（品目合計、12か月対数変化）')
ax.axhline(0, color='k', lw=0.6); ax.grid(alpha=0.3); ax.set_ylabel('%pt')
ax.set_title('日本のCPIインフレの動学的分解（セントルイス連銀＝Dupor・Hogan方式、ラグ6、12か月累積寄与）')
ax.legend(loc='upper left', fontsize=9, ncol=2)
fig.text(0.01, 0.01, '出所：総務省「消費者物価指数」「家計調査」（二人以上の世帯）より筆者推計。45分類、階差VAR(6)＋月ダミー、2000年1月～2026年9月の固定サンプル推計。\n全45分類で安定条件を満たす仕様。原著に合わせたラグ12は2分類が不安定なため診断値扱い。研究用の中間成果。', fontsize=7.5)
fig.tight_layout(rect=[0,0.05,1,1]); fig.savefig(out, dpi=150)
print(x.loc[['2022-12','2024-06','2025-09','2026-09'],[c for c,_,_ in comps]+['total']].round(2))
