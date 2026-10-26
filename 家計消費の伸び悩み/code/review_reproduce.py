"""保存済みCSVで査読数値と図2〜4を再現。原統計の再取得は行わない。"""
from pathlib import Path
import json
import re
import numpy as np
import pandas as pd
import statsmodels.api as sm
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import japanize_matplotlib  # noqa: F401

HERE = Path(__file__).resolve().parent
OUT = HERE.parent
k = pd.read_csv(HERE / 'levels3.csv', index_col=0)
k.index = pd.PeriodIndex(k.index, freq='Q')
# 取得した公式原本を加工CSVと照合（四半期・13系列）。
raw = pd.read_excel(HERE/'source/kakei_26q2.xlsx', sheet_name='季調系列 Seasonally adjusted series', header=None)
source_columns = ['op','comp','prop','tax','soc','ben','oth','yd','adj','c','s','_','sr','__','yd_real']
source_rows = []
year = None
for _, row in raw.iloc[8:].iterrows():
    label = str(row.iloc[0])
    ym = re.match(r'\s*(\d{4})/', label)
    if ym:
        year = int(ym.group(1))
    qm = re.search(r'(\d+)-\s*(\d+)\.', label)
    if not qm or pd.isna(pd.to_numeric(row.iloc[1], errors='coerce')):
        continue
    quarter = (int(qm.group(1))-1)//3+1
    source_rows.append([f'{year}Q{quarter}']+list(pd.to_numeric(row.iloc[1:16], errors='coerce')))
source = pd.DataFrame(source_rows, columns=['date']+source_columns).set_index('date')
source.index = pd.PeriodIndex(source.index, freq='Q')
assert source.index.equals(k.index)
for col in set(source_columns)-{'_', '__'}:
    np.testing.assert_allclose(source[col], k[col], rtol=0, atol=1e-6)

d = pd.read_csv(HERE / 'decomp.csv', index_col=0)
t = pd.read_csv(HERE / 'burden.csv')
a = t[t.year == 2019].set_index('age')
b = t[t.year == 2025].set_index('age')
np.testing.assert_allclose(d.dC_real, d.dYd_nom-d.dP+d.dAPC, atol=1e-9)
np.testing.assert_allclose(k.c, k.cn, atol=1e-6)
np.testing.assert_allclose(k.apc, k.c/k.yd)
# 公表貯蓄率は小数1桁、収支額は小数1桁に丸められている。
np.testing.assert_allclose(100*k.s/(k.yd+k.adj), k.sr, atol=.051)
np.testing.assert_allclose(k.s, k.yd+k.adj-k.c, atol=.21)

periods = []
for start, end in [('2021Q4', '2026Q2'), ('2019Q4', '2026Q2'), ('2026Q1', '2026Q2')]:
    r = 100*np.log(k.loc[end, ['cr','yd','P','apc']]/k.loc[start, ['cr','yd','P','apc']])
    periods.append({'期間': f'{start}→{end}', '実質消費': r.cr, '名目所得': r.yd,
                    '物価': r.P, '実質所得': r.yd-r.P, '消費性向': r.apc})
pd.DataFrame(periods).to_csv(HERE/'review_periods.csv', index=False)

xs = ['nw_y','CSI','pi','d14','d19','d24']
s = k.loc['1997Q4':].drop(pd.period_range('2020Q1','2021Q4',freq='Q')).dropna(subset=['sr']+xs)
m = sm.OLS(s.sr, sm.add_constant(s[xs])).fit(cov_type='HAC', cov_kwds={'maxlags':4})
fit = m.predict(sm.add_constant(k[xs], has_constant='add'))
np.testing.assert_allclose(fit.dropna(), k.loc[fit.dropna().index,'fitA'], atol=1e-8)
pd.DataFrame({'係数':m.params, 'HAC標準誤差':m.bse, 'p値':m.pvalues}).to_csv(HERE/'review_regression.csv')

# 名目の中点分解を共通CPIで厳密に実質化。物価項を独立表示する。
# g = A+B+丸め残差, r=P1/P0。実質変化率=(g-100(r-1))/r。
ss = pd.read_csv(HERE/'shiftshare.csv')
cpi = pd.read_csv(HERE/'cpi_y.csv', index_col=0).iloc[:,0]
rows = []
for _, v in ss.iterrows():
    y0,y1 = map(int, v['期間'].split('→'))
    r = cpi[y1]/cpi[y0]
    total = (100+v['平均消費支出変化%'])/r-100
    comp, within, price = v['年齢構成要因']/r, v['年齢内要因']/r, -100*(r-1)/r
    residual = total-comp-within-price
    assert abs(residual) < .02  # 入力の0.01pt丸めによる差
    rows.append([v['期間'], total, comp, within, price, residual])
real = pd.DataFrame(rows, columns=['期間','実質変化率','年齢構成','年齢内名目','共通物価','丸め残差'])
real.to_csv(HERE/'review_shiftshare.csv', index=False)

def finish(fig, name, source):
    fig.text(.02,.01, source, fontsize=8)
    fig.tight_layout(rect=(0,.04,1,1))
    fig.savefig(OUT/name, dpi=140)
    plt.close(fig)

fig, ax = plt.subplots(3,1, figsize=(10,12))
z=k.loc['2010Q1':]; x=z.index.to_timestamp()
ax[0].plot(x,z.sr,label='貯蓄率（実績）',color='black')
ax[0].plot(x,fit.loc[z.index],label='同一標本内の当てはめ値',ls='--')
ax[0].axvspan(pd.Timestamp('2020-01-01'),pd.Timestamp('2022-01-01'),alpha=.12,color='gray')
ax[0].set_title('① 静学的な貯蓄率回帰（％）：予測・因果効果ではない')
ax[0].legend()
z=k.loc['2019Q1':]; x=z.index.to_timestamp()
ax[1].bar(x,z.cum_exc.fillna(0)/1000,width=70,color='#55A868')
ax[1].set_title('② 基準貯蓄率を上回る貯蓄フローの累積（兆円）')
ax[1].set_ylabel('兆円')
z=k.loc['2024Q1':]; x=np.arange(len(z))
ax[2].bar(x-.2,100*np.log(k.yd/k.P).diff().loc[z.index],.4,label='実質可処分所得')
ax[2].bar(x+.2,100*np.log(k.cr).diff().loc[z.index],.4,label='実質家計消費')
ax[2].set_xticks(x,[str(i) for i in z.index],rotation=30)
ax[2].set_title('③ 所得と消費の前期比（対数％）：反応の遅れは未推定')
ax[2].legend()
for q in ax: q.axhline(0,color='gray',lw=.6); q.grid(axis='y',alpha=.2)
finish(fig,'01_chart_saving.png','出典：内閣府・日本銀行。保存済み levels3.csv から再計算。灰色は推定対象外の2020〜21年。')

fig,ax=plt.subplots(2,1,figsize=(10,9))
x=np.arange(len(a))
for i,(data,year) in enumerate([(a,2019),(b,2025)]):
    ax[0].bar(x+(i-.5)*.36,data['消費性向'],.36,label=str(year))
ax[0].set_xticks(x,a.index,rotation=20);ax[0].legend();ax[0].set_ylabel('％')
ax[0].set_title('① 二人以上の勤労者世帯：世帯主年齢別の平均消費性向')
x=np.arange(len(real))
for off,col,color in [(-.25,'年齢構成','#DD8452'),(0,'年齢内名目','#4C72B0'),(.25,'共通物価','#55A868')]:
    ax[1].bar(x+off,real[col],.25,label=col,color=color)
ax[1].plot(x,real['実質変化率'],'kD',label='実質変化率（合計）')
for i,v in enumerate(real['実質変化率']): ax[1].annotate(f'{v:.2f}％',(i,v),xytext=(0,-16),textcoords='offset points',ha='center')
ax[1].set_xticks(x,real['期間']);ax[1].set_ylabel('％・寄与度ポイント');ax[1].legend(fontsize=9,ncol=2)
ax[1].set_title('② 二人以上世帯の1世帯当たり消費：共通CPIによる厳密な実質化')
ax[1].axhline(0,color='gray',lw=.6)
finish(fig,'01_chart_age.png','出典：総務省。年齢構成・年齢内名目寄与を期末/期首CPI比で除し、共通物価項を別掲。\n2000・2010年始点は2018年の家計簿改正をまたぐ。名目分解の丸め残差は絶対値0.02pt未満。')

fig,ax=plt.subplots(3,1,figsize=(10,13));x=np.arange(len(a))
for off,col,label in [(-.2,'実質可処分','実質可処分所得'),(.2,'実質消費','実質消費')]:
    ax[0].bar(x+off,100*np.log(b[col]/a[col]),.4,label=label)
ax[0].set_title('① 2019→2025年の変化（対数％、同じ世帯の追跡ではない）');ax[0].legend()
# 負の純増も省略せず、残差を含め黒字率と照合する。
cols=['預貯金','保険','有価証券','住宅ローン返済','他借金']
change=b[cols]-a[cols]
change['その他']=b['黒字率']-a['黒字率']-change.sum(axis=1)
np.testing.assert_allclose(change.sum(axis=1),b['黒字率']-a['黒字率'])
positive=np.zeros(len(a));negative=positive.copy()
for col in change:
    v=change[col].values;bot=np.where(v>=0,positive,negative)
    ax[1].bar(x,v,bottom=bot,label=col)
    positive+=np.maximum(v,0);negative+=np.minimum(v,0)
ax[1].plot(x,b['黒字率']-a['黒字率'],'kD',label='黒字率の変化')
ax[1].set_title('② 黒字内訳の変化（可処分所得比の差、ポイント）');ax[1].legend(fontsize=8,ncol=4)
for off,data,year in [(-.2,a,2019),(.2,b,2025)]:ax[2].bar(x+off,data['負担率'],.4,label=str(year))
ax[2].set_title('③ 非消費支出÷実収入（％）：全階級で横ばいとは限らない');ax[2].legend()
for q in ax:q.set_xticks(x,a.index,rotation=20);q.axhline(0,color='gray',lw=.6);q.grid(axis='y',alpha=.2)
finish(fig,'01_chart_workers.png','出典：総務省・保存済み burden.csv。預貯金等は純増、住宅ローン等は純減。\nその他は黒字率との差額（財産純増・繰越純増等）。各比率の変化は同じ所得増の使途を追跡した値ではない。')
summary={'恒等式最大残差':float(d.resid.abs().max()),'原本照合四半期数':len(source),'原本照合系列数':13,'回帰標本数':int(m.nobs),'R2':m.rsquared,
         '2026Q2貯蓄率残差pt':float(k.loc['2026Q2','sr']-fit.loc['2026Q2']),
         '超過貯蓄累積2026Q2兆円':float(k.loc['2026Q2','cum_exc']/1000)}
(HERE/'review_checks.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(summary,ensure_ascii=False,indent=2));print(real.to_string(index=False))
