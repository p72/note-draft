import sys, pandas as pd, numpy as np, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
sys.path.insert(0,'ESRI_DATA_SKILL_DIR'); from scripts.esri_data import setup_japanese_font; setup_japanese_font()
N={'JPN':'日本','USA':'米国','GBR':'英国','DEU':'ドイツ','FRA':'フランス','ITA':'イタリア'}
cf=pd.read_csv('cofog.csv'); p65=pd.read_csv('pop65.csv',index_col=0); p65.columns=p65.columns.astype(int)
P=pd.read_csv('panel.csv'); P['defl']=P.C/P.Cr; defl=P.pivot(index='TIME_PERIOD',columns='area',values='defl')
pen=cf[(cf.TRANSACTION=='D62')&(cf.EXPENDITURE=='GF1002')].pivot(index='TIME_PERIOD',columns='REF_AREA',values='OBS_VALUE')
pen['USA']=pd.read_csv('us_socsec.csv',index_col=0).iloc[:,0]*1e3
R=pd.read_csv('pension_intl.csv')
fig,ax=plt.subplots(2,1,figsize=(9,11)); ends=[]
for a,n in N.items():
    yrs=range(2012,2025); s=pd.Series({y:pen.loc[y,a]/p65.loc[a,y]/defl.loc[y,a] for y in yrs}); s=100*s/s[2012]
    if a=='JPN': ax[0].plot(s.index,s,color='#C44E52',lw=3,label=n)
    else: ax[0].plot(s.index,s,color='#999999',lw=1.2); ends.append((s[2024],n))
ends.sort(); last=-1e9
for v,n in ends:
    yv=max(v,last+1.8); ax[0].text(2024.2,yv,n,fontsize=8,va='center',color='#555555'); last=yv
ax[0].axhline(100,color='gray',lw=.8); ax[0].grid(alpha=.3); ax[0].set_xlim(2012,2025.6); ax[0].legend(fontsize=9,loc='upper left')
ax[0].set_title('① 65歳以上1人当たり実質公的老齢給付（2012年＝100）\n日本の目減りが最も大きく、2012年から約2割減',fontsize=12)
g=R[(R.period=='2019-2024')&(R.area.isin(N))].set_index('area').sort_values('real'); y=np.arange(len(g))
ax[1].barh(y-.2,g.nominal,.4,color='#4C72B0',label='名目の伸び（65歳以上1人当たり）'); ax[1].barh(y+.2,g.prices,.4,color='#DD8452',label='物価（家計消費デフレーター）')
ax[1].plot(g.real,y,'kD',ms=7,label='実質の伸び')
for i,v in enumerate(g.real): ax[1].text(max(g.nominal.iloc[i],g.prices.iloc[i])+0.6,i,f'実質 {v:+.1f}',va='center',fontsize=8)
ax[1].set_yticks(y); ax[1].set_yticklabels([N[a] for a in g.index]); ax[1].axvline(0,color='gray',lw=.8); ax[1].grid(axis='x',alpha=.3)
for t in ax[1].get_yticklabels():
    if t.get_text()=='日本': t.set_color('#C44E52'); t.set_fontweight('bold')
ax[1].legend(fontsize=8,loc='upper center',bbox_to_anchor=(0.5,-0.06),ncol=3,frameon=False); ax[1].set_xlim(-12,30)
ax[1].set_title('② 2019→2024年：65歳以上1人当たり公的老齢給付の伸び（対数％）\n日本は名目でほとんど増えず、物価に大きく負けた',fontsize=12)
fig.text(.01,.004,'出典：OECD「Annual government expenditure by function (COFOG)」（一般政府、10.2 老齢、現金給付D62）、米国はFRED（BEA, Social security benefits）、\n65歳以上人口は World Bank（SP.POP.65UP.TO）、物価は OECD の家計最終消費支出デフレーター。米国は障害・遺族年金を含む。',fontsize=6.5)
plt.tight_layout(rect=(0,.035,1,1)); plt.savefig('02_chart_pension.png',dpi=130)
