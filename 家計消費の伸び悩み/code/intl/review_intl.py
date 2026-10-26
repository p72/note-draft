"""保存された原表CSVから同一定義の年次比較・年金図を再計算する。"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager

def _setup_jp_font():
    """環境内の日本語フォント（Noto CJK など）を探して設定する。見つからなければ既定フォントのまま。"""
    for name in ['Noto Sans CJK JP', 'Noto Sans JP', 'IPAexGothic', 'IPAGothic', 'Hiragino Sans', 'Yu Gothic', 'Meiryo']:
        if any(f.name == name for f in font_manager.fontManager.ttflist):
            plt.rcParams['font.family'] = name
            return name
    return None

_setup_jp_font()

HERE = Path(__file__).resolve().parent
OUT = HERE.parent.parent
N = {'JPN':'日本','USA':'米国','GBR':'英国','DEU':'ドイツ','FRA':'フランス','ITA':'イタリア','CAN':'カナダ','KOR':'韓国','AUS':'豪州'}
t = pd.read_csv(HERE/'table14.csv')
c = pd.read_csv(HERE/'table1_p3.csv')
pop = pd.read_csv(HERE/'pop.csv')
assert set(t.SECTOR) == {'S1M'}
assert set(t.UNIT_MULT) == set(c.UNIT_MULT) == {6}
assert set(pop.UNIT_MULT) == {3}

def pivot(df):
    assert not df.duplicated(['TIME_PERIOD','REF_AREA']).any()
    return df.pivot(index='TIME_PERIOD', columns='REF_AREA', values='OBS_VALUE').reindex(columns=N)

def transaction(tr, entry):
    return pivot(t[(t.TRANSACTION==tr)&(t.ACCOUNTING_ENTRY==entry)])

Y = transaction('B6G','C')
C = pivot(c[(c.SECTOR=='S1M')&(c.PRICE_BASE=='V')])
R = pivot(c[(c.SECTOR=='S1M')&(c.PRICE_BASE=='LR')])
POP = pivot(pop)
P = C/R
D1 = transaction('D1','C')
components = {'雇用者報酬':D1, '営業余剰・混合所得':transaction('B2A3G','C'),
              '財産所得（純）':transaction('D4','C')-transaction('D4','D'),
              '社会給付':transaction('D62','C'), '所得税等':-transaction('D5','D'),
              '社会負担':-transaction('D61','D')}
rows, incomes = [], []
for a,b in [(2000,2024),(2019,2024),(2021,2024),(2022,2024)]:
    for country in N:
        values = [x.loc[[a,b],country] for x in [Y,C,R,POP,D1]]
        assert all(v.notna().all() and (v>0).all() for v in values), (a,b,country)
        growth = lambda x: 100*np.log(x.loc[b,country]/x.loc[a,country])
        yn = growth(Y)-growth(POP)
        prices = growth(P)
        cr = growth(R)-growth(POP)
        apc = growth(C)-growth(Y)
        rows.append(dict(area=country, period=f'{a}-{b}',real_C_pc=cr, nomYd_pc=yn,
                         prices=prices,realYd_pc=yn-prices,APC=apc,
                         nomComp_pc=growth(D1)-growth(POP),resid=cr-yn+prices-apc))
        y0 = Y.loc[a,country]/POP.loc[a,country]
        inc = dict(area=country,period=f'{a}-{b}',Yd_pc_pct=100*((Y.loc[b,country]/POP.loc[b,country])/y0-1))
        for name,series in components.items():
            vals=series.loc[[a,b],country]
            inc[name]=100*(vals[b]/POP.loc[b,country]-vals[a]/POP.loc[a,country])/y0 if vals.notna().all() else np.nan
        inc['その他']=inc['Yd_pc_pct']-sum(v for key,v in inc.items() if key in components and pd.notna(v))
        inc['欠測項目']=';'.join(key for key in components if pd.isna(inc[key]))
        incomes.append(inc)
D=pd.DataFrame(rows); I=pd.DataFrame(incomes)
assert D.resid.abs().max()<1e-9
old=pd.read_csv(HERE/'decomp_intl.csv')
check=old.merge(D,on=['area','period'],suffixes=('_old','_new'))
for col in ['real_C_pc','nomYd_pc','prices','realYd_pc','APC']:
    np.testing.assert_allclose(check[col+'_old'],check[col+'_new'],atol=1e-9)
oldi=pd.read_csv(HERE/'income_decomp.csv'); checki=oldi.merge(I,on=['area','period'],suffixes=('_old','_new'))
for col in ['Yd_pc_pct',*components,'その他']:
    np.testing.assert_allclose(checki[col+'_old'],checki[col+'_new'],atol=1e-9,equal_nan=True)
np.testing.assert_allclose(I[list(components)+['その他']].sum(axis=1),I.Yd_pc_pct,atol=1e-9)
D.to_csv(HERE/'review_annual_decomp.csv',index=False)
I.to_csv(HERE/'review_annual_income.csv',index=False)

# 年金指標の分子・分母を別々に再計算。受給者平均や制度改定率とは異なる。
cf=pd.read_csv(HERE/'cofog.csv')
cf=cf[(cf.TRANSACTION=='D62')&(cf.EXPENDITURE=='GF1002')&(cf.SECTOR=='S13')]
assert set(cf.UNIT_MULT)=={6}
pen=pivot(cf)
p65=pd.read_csv(HERE/'pop65.csv',index_col=0);p65.columns=p65.columns.astype(int)
us=pd.read_csv(HERE/'us_socsec.csv',index_col=0).iloc[:,0]
pen['USA']=us*1000
main=['JPN','FRA','DEU','GBR','ITA']
refs=['USA','AUS']
pr=[]; indices=[]
for country in main+refs:
    years=list(range(2012,2025))
    z=pen.loc[years,country]/p65.loc[country,years].values/P.loc[years,country]
    assert z.notna().all() and (z>0).all()
    for y,value in (100*z/z.loc[2012]).items():
        indices.append(dict(area=country,year=y,index=value))
    for a,b in [(2012,2019),(2019,2024),(2022,2024)]:
        total=100*np.log(pen.loc[b,country]/pen.loc[a,country])
        ageing=100*np.log(p65.loc[country,b]/p65.loc[country,a])
        price=100*np.log(P.loc[b,country]/P.loc[a,country])
        pr.append(dict(area=country,period=f'{a}-{b}',total_nom=total,pop65=ageing,prices=price,
                       nominal=total-ageing,real=total-ageing-price,
                       group='主比較' if country in main else '参考（範囲・内訳要確認）'))
PR=pd.DataFrame(pr);IDX=pd.DataFrame(indices)
oldp=pd.read_csv(HERE/'pension_intl.csv');z=oldp.merge(PR,on=['area','period'],suffixes=('_old','_new'))
for col in ['total_nom','pop65','prices','nominal','real']:
    np.testing.assert_allclose(z[col+'_old'],z[col+'_new'],atol=1e-9)
PR.to_csv(HERE/'review_pension.csv',index=False)
IDX.to_csv(HERE/'review_pension_index.csv',index=False)

def finish(fig,name,source):
    fig.text(.02,.008,source,fontsize=8)
    fig.tight_layout(rect=(0,.055,1,.98))
    fig.savefig(OUT/name,dpi=140)
    plt.close(fig)

def stacked(ax,g,parts,total):
    pos=np.zeros(len(g));neg=pos.copy(); y=np.arange(len(g))
    for name,v,color in parts:
        v=np.asarray(v);ax.barh(y,v,left=np.where(v>=0,pos,neg),label=name,color=color)
        pos+=np.maximum(v,0);neg+=np.minimum(v,0)
    ax.plot(g[total],y,'kD',label='合計')
    ax.set_yticks(y,[N[x]+('＊' if x=='AUS' and total=='Yd_pc_pct' else '') for x in g.index])
    ax.axvline(0,color='gray',lw=.7);ax.grid(axis='x',alpha=.2)
    for lab in ax.get_yticklabels():
        if lab.get_text()=='日本':lab.set_color('#C44E52');lab.set_fontweight('bold')
    ax.legend(fontsize=8,ncol=4,loc='upper center',bbox_to_anchor=(.5,-.08))

fig,ax=plt.subplots(2,1,figsize=(10,12))
g=D.query("period=='2022-2024'").set_index('area').sort_values('real_C_pc')
stacked(ax[0],g,[('総可処分所得（名目）',g.nomYd_pc,'#4C72B0'),('物価',-g.prices,'#DD8452'),('消費性向',g.APC,'#55A868')],'real_C_pc')
ax[0].set_title('① 2022→2024年：1人当たり実質消費の分解（対数％）\n9か国とも年次・家計＋非営利団体・総可処分所得で統一')
g=I.query("period=='2022-2024'").set_index('area').sort_values('Yd_pc_pct')
colors=['#C44E52','#937860','#8172B2','#55A868','#4C72B0','#64B5CD','#BBBBBB']
stacked(ax[1],g,[(name,g[name].fillna(0),color) for name,color in zip([*components,'その他'],colors)],'Yd_pc_pct')
ax[1].set_title('② 同期間の1人当たり総可処分所得の項目別寄与（％ポイント）\n社会給付は年金以外も含む。税・社会負担は控除項目')
finish(fig,'02_chart_2022annual.png','出典：保存済みOECD年次原表から再計算。上段は対数変化、下段は通常の増減率への寄与。\n＊豪州の社会給付は原表で欠測のため「その他」に含む（ゼロを意味しない）。')

fig,ax=plt.subplots(3,1,figsize=(10,14))
for country in main:
    v=IDX[IDX.area==country]
    ax[0].plot(v.year,v['index'],label=N[country],lw=2.8 if country=='JPN' else 1.5)
v=IDX[IDX.area=='USA'];ax[0].plot(v.year,v['index'],'--',color='gray',label='米国（参考：障害・遺族を含む）')
ax[0].axhline(100,color='gray',lw=.6);ax[0].legend(ncol=3,fontsize=9)
ax[0].set_title('① 実質老齢現金給付総額÷65歳以上人口（2012年＝100）\n受給者の平均年金額ではない。日本も2024年には前年比で上昇')
g=PR.query("period=='2019-2024' and group=='主比較'").set_index('area').sort_values('real')
y=np.arange(len(g))
ax[1].barh(y-.2,g.nominal,.4,label='名目の伸び（65歳以上人口当たり）')
ax[1].barh(y+.2,g.prices,.4,label='家計消費デフレーター上昇')
ax[1].plot(g.real,y,'kD',label='実質変化')
ax[1].set_yticks(y,[N[x] for x in g.index]);ax[1].legend(fontsize=9,ncol=3,loc='upper center',bbox_to_anchor=(.5,-.08),frameon=False)
ax[1].axvline(0,color='gray',lw=.6)
ax[1].set_title('② 2019→2024年：名目給付の伸びと物価（対数％）')
g=PR[PR.area=='JPN'].set_index('period');x=np.arange(len(g))
for off,col,sign,label in [(-.25,'total_nom',1,'名目給付総額'),(0,'pop65',-1,'65歳以上人口（控除）'),(.25,'prices',-1,'物価（控除）')]:
    ax[2].bar(x+off,sign*g[col],.25,label=label)
ax[2].plot(x,g.real,'kD',label='実質・65歳以上人口当たり')
ax[2].set_xticks(x,g.index);ax[2].axhline(0,color='gray',lw=.6);ax[2].legend(fontsize=9,ncol=2)
ax[2].set_title('③ 日本：給付総額・人口・物価の分解（対数％・寄与度）')
for a in ax:a.grid(alpha=.2)
finish(fig,'02_chart_pension.png','出典：OECD COFOG・家計消費デフレーター、World Bank 65歳以上人口。米国はFRED。\n主比較は日仏独英伊。豪州は給付内訳の比較可能性が未確認のため参考CSVに全数値を保存。')

j=IDX[IDX.area=='JPN'].set_index('year')['index']
summary={'longrun_rows_verified':len(check),'income_rows_verified':len(checki),'pension_rows_verified':len(z),
         'max_identity_residual':float(D.resid.abs().max()),'japan_pension_2024_yoy_pct':float(100*(j.loc[2024]/j.loc[2023]-1)),
         'japan_2022_2024':D.query("area=='JPN' and period=='2022-2024'").iloc[0].to_dict()}
(HERE/'review_checks.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(summary,ensure_ascii=False,indent=2))
print(D.query("period=='2022-2024'").round(2).to_string(index=False))
print(I.query("period=='2022-2024'").round(2).to_string(index=False))
