import pandas as pd, model2 as m
df = pd.read_csv('quarterly.csv', index_col=0); df.index = pd.PeriodIndex(df.index, freq='Q')
V = ['cgpi', 'fx', 'wage_h']
d = df.copy(); d['cpi'] = d['cpi_core']
out = pd.read_pickle('est2.pkl')
out['core2024'] = m.estimate(d, V, '1990Q1', '2023Q4', per_var=True)
m.summary(out['core2024'], '2024年版再現：コアCPI 1990Q1〜2023Q4')
# 推計終期を1年ずつずらした新コアコア版（閾値τの推移を見る）
for end in ['2023Q4', '2024Q4']:
    out[f'cc_{end}'] = m.estimate(df, V, '1990Q1', end, per_var=True)
    m.summary(out[f'cc_{end}'], f'新コアコア 〜{end}')
pd.to_pickle(out, 'est2.pkl')
