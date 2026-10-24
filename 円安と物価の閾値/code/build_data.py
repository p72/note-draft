import pandas as pd, numpy as np

# --- CPI 新コアコア（月次指数→四半期平均→前年比）
cpi = pd.read_csv('cpi.csv', index_col=0)
cpi.index = pd.PeriodIndex(cpi.index, freq='M')
cpi_q = cpi['value'].groupby(cpi.index.asfreq('Q')).agg(['mean', 'count'])
cpi_q = cpi_q.loc[cpi_q['count'] == 3, 'mean']

# --- BOJ: ドル円(17時・月中平均), 国内企業物価(消費税除く)
b = pd.read_csv('boj.csv', index_col=0, parse_dates=True)
b.index = b.index.to_period('M')
bq = b.groupby(b.index.asfreq('Q')).agg(['mean', 'count'])
fx_q = bq[('FXERM07', 'mean')][bq[('FXERM07', 'count')] == 3]
cg_q = bq[('PRCG20_1200000000', 'mean')][bq[('PRCG20_1200000000', 'count')] == 3]

# --- 賃金（毎勤 現金給与総額 5人以上 調査産業計 前年比・四半期）
def read_wage(path):
    v = pd.read_excel(path, sheet_name='TL', header=None)
    start = v.index[v[0].astype(str).str.contains('前年比')][0]
    rows = []
    for i in range(start, len(v)):
        try:
            y = int(v.iat[i, 0])
        except Exception:
            continue
        for q in range(4):
            rows.append((pd.Period(f'{y}Q{q+1}', 'Q'),
                         pd.to_numeric(v.iat[i, 4 + q], errors='coerce')))
    return pd.Series(dict(rows)).dropna()

w5, w30 = read_wage('wage.xls'), read_wage('wage30.xls')
# 5人以上は1991年から前年比あり → それ以前は30人以上で接続
wage = pd.concat([w30[w30.index < w5.index.min()], w5])

df = pd.DataFrame({
    'cpi': cpi_q.pct_change(4) * 100,
    'cgpi': cg_q.pct_change(4) * 100,
    'fx': fx_q.pct_change(4) * 100,      # プラス＝円安
    'wage': wage,
    'fx_level': fx_q,
})
df.to_csv('quarterly.csv')
print(df.loc['1989Q1':].head(6)); print(df.tail(8))

# --- 論文仕様の賃金：きまって支給する給与（30人以上）÷ 総実労働時間 ＝ 平均時給の前年比
kim, hrs = read_wage('kimatte30.xls'), read_wage('hours30.xls')
hourly = ((1 + kim / 100) / (1 + hrs / 100) - 1) * 100
df['wage_h'] = hourly
df.to_csv('quarterly.csv')
print(df[['wage', 'wage_h']].loc['1989Q1':'1990Q4']); print(df[['wage', 'wage_h']].tail(6))
