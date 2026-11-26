"""日本版 Shapiro 方式インフレ分解（プロトタイプ）
入力（e-Stat API で取得し pickle 保存したもの）:
  data/kakei_0004023601.pkl : 家計調査 品目分類（2025年改定・金額）二人以上の世帯・全国、中分類（cdCat02=03, cdArea=00000）
  data/cpi_idx.pkl          : CPI 2020年基準 中分類指数（statsDataId 0003427113, 全国, cdTab=1）
手法: 46中分類ごとに価格・実質支出の月次対数差を VAR(12)+月ダミーで過去120か月ローリング推計し、
当月の予測誤差の符号が同じなら需要、逆なら供給に分類。前月までの12か月平均支出シェアで寄与を集計。
消費税増税月（2014年3・4月、2019年9・10月）は分類対象外。
"""
import pandas as pd, numpy as np
k = pd.read_pickle('data/kakei_0004023601.pkl')
c = pd.read_pickle('data/cpi_idx.pkl')
MAP = {  # 家計調査コード: CPIコード
 '010100000':'0003','010200000':'0008','010300000':'0013','010400000':'0016','010500000':'0021',
 '010600000':'0027','010700000':'0030','010800000':'0033','010900000':'0034','011000000':'0037',
 '011100000':'0041','011200000':'0042','020100000':'0165','020200000':'0051','030100000':'0056',
 '030200000':'0057','030300000':'0058','030400001':'0059','040100000':'0061','040200000':'0066',
 '040300000':'0070','040400000':'0073','040500000':'0077','040600000':'0081','050100000':'0084',
 '050200000':'0085','050300000':'0090','050400000':'0094','050500000':'0103','050600000':'0103',
 '050700000':'0098','050800000':'0106','060100000':'0108','060200001':'0108','060300000':'0109',
 '060400000':'0110','070100000':'0112','070200000':'0113','070300000':'0117','080100000':'0119',
 '080200000':'0120','080300000':'0121','090100000':'0123','090200000':'0128','090300000':'0134',
 '090400000':'0138','100100000':'0145'}
k['cpi'] = k['cat01_code'].map(MAP)
kk = k.dropna(subset=['cpi']); nom = kk.groupby([kk.index, 'cpi'])['value'].sum().unstack()  # 名目支出(円)
nom.index = pd.PeriodIndex(nom.index, freq='M')
P = c.pivot_table(index=c.index, columns='cat01_code', values='value')
P.index = pd.PeriodIndex(P.index, freq='M')
cats = sorted(nom.columns)
names = c.drop_duplicates('cat01_code').set_index('cat01_code')['cat01_name'].str[5:]
idx = nom.index.intersection(P.index)
idx = idx[idx >= pd.Period('2000-01','M')]
nom, Pc = nom.loc[idx, cats], P.loc[idx, cats]
real = nom / Pc
dp = 100*np.log(Pc).diff()
dq = 100*np.log(real).diff()
w = nom.div(nom.sum(1), axis=0).rolling(12).mean().shift(1)   # 前月までの12か月平均支出シェア

LAGS, WIN = 12, 120
tax = [pd.Period(m,'M') for m in ['2014-03','2014-04','2019-09','2019-10']]
res_p = pd.DataFrame(index=idx, columns=cats, dtype=float); res_q = res_p.copy()
months = pd.get_dummies(idx.month, prefix='m', drop_first=True).astype(float).set_index(idx)
for cat in cats:
    X = pd.concat({f'p{l}': dp[cat].shift(l) for l in range(1,LAGS+1)} | {f'q{l}': dq[cat].shift(l) for l in range(1,LAGS+1)}, axis=1)
    X = pd.concat([X, months], axis=1)
    for t in tax: X[f'tax{t}'] = (idx == t).astype(float)
    X['const'] = 1.0
    Y = pd.concat([dp[cat], dq[cat]], axis=1)
    ok = X.notna().all(1) & Y.notna().all(1)
    pos = np.where(ok)[0]
    for j in range(WIN, len(pos)):
        tr = pos[j-WIN:j]; t = pos[j]                       # 過去10年で推計→当月は予測誤差（リアルタイム版）
        Xt, Yt = X.iloc[tr].values, Y.iloc[tr].values
        keep = Xt.std(0) > 0; keep[-1] = True
        b = np.linalg.lstsq(Xt[:, keep], Yt, rcond=None)[0]
        xt = X.iloc[t].values[keep]
        e = Y.iloc[t].values - xt @ b
        if X.iloc[t][[f'tax{x}' for x in tax]].sum() > 0: e[:] = np.nan
        res_p.iloc[t, cats.index(cat)], res_q.iloc[t, cats.index(cat)] = e
demand = (np.sign(res_p) == np.sign(res_q)) & res_p.notna()
supply = (np.sign(res_p) != np.sign(res_q)) & res_p.notna()
contrib = w * dp
out = pd.DataFrame({'demand': (contrib*demand).sum(1, min_count=1),
                    'supply': (contrib*supply).sum(1, min_count=1),
                    'total':  contrib.where(res_p.notna()).sum(1),
                    'all':    contrib.sum(1, min_count=1)})
pd.to_pickle(dict(out=out, res_p=res_p, res_q=res_q, dp=dp, dq=dq, w=w, P=P, names=names, cats=cats, demand=demand, supply=supply), 'data/result.pkl')
y = out.rolling(12).sum()
print(y.loc['2021-01':].iloc[::3].round(2))
