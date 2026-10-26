import sys, pandas as pd, numpy as np, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
sys.path.insert(0,'ESRI_DATA_SKILL_DIR'); from scripts.esri_data import setup_japanese_font; setup_japanese_font()
N={'JPN':'日本','USA':'米国','GBR':'英国','DEU':'ドイツ','FRA':'フランス','ITA':'イタリア','CAN':'カナダ','KOR':'韓国','AUS':'豪州'}
R=pd.read_csv('decomp_recent_q.csv').query("base==2022").set_index('area').sort_values('real_C_pc')
I=pd.read_csv('income_recent_q.csv').set_index('area').sort_values('Yd_pc_pct')
fig,ax=plt.subplots(2,1,figsize=(9,12))
y=np.arange(len(R)); pos=np.zeros(len(R)); neg=np.zeros(len(R))
for nm,v,c in [('名目可処分所得',R.nomYd_pc,'#4C72B0'),('物価（消費デフレーター）',-R.prices,'#DD8452'),('平均消費性向',R.APC,'#55A868')]:
    v=v.values; b=np.where(v>=0,pos,neg); ax[0].barh(y,v,left=b,color=c,height=.6,label=nm); pos+=np.where(v>=0,v,0); neg+=np.where(v<0,v,0)
ax[0].plot(R.real_C_pc,y,'kD',ms=7,label='1人当たり実質消費')
for i,v in enumerate(R.real_C_pc): ax[0].text(v,i+.33,f'{v:.1f}',ha='center',fontsize=8)
ax[0].set_yticks(y); ax[0].set_yticklabels([N[a]+('＊' if a=='KOR' else '') for a in R.index])
ax[0].axvline(0,color='gray',lw=.8); ax[0].grid(axis='x',alpha=.3)
ax[0].legend(fontsize=8,loc='upper center',bbox_to_anchor=(0.5,-0.06),ncol=4,frameon=False)
ax[0].set_title('① 2022年→直近4四半期：1人当たり実質消費の分解（対数％）\n日本の消費は中位、ただし所得ではなく消費性向の上昇で支えている',fontsize=12)
y=np.arange(len(I)); pos=np.zeros(len(I)); neg=np.zeros(len(I))
for nm,c in [('雇用者報酬','#C44E52'),('営業余剰・混合所得','#937860'),('財産所得（純）','#8172B2'),('社会給付','#55A868'),('所得税等','#4C72B0'),('社会負担','#64B5CD'),('その他','#BBBBBB')]:
    v=I[nm].fillna(0).values; b=np.where(v>=0,pos,neg)
    ax[1].barh(y,v,left=b,color=c,height=.6,label=nm if nm not in ('所得税等','社会負担') else nm+'（控除）'); pos+=np.where(v>=0,v,0); neg+=np.where(v<0,v,0)
ax[1].plot(I.Yd_pc_pct,y,'kD',ms=7,label='1人当たり名目可処分所得')
for i,v in enumerate(I.Yd_pc_pct): ax[1].text(v+0.6,i-.12,f'{v:.1f}',fontsize=8)
ax[1].set_yticks(y); ax[1].set_yticklabels([N[a]+('†' if a in ('USA','ITA') else '') for a in I.index])
ax[1].axvline(0,color='gray',lw=.8); ax[1].grid(axis='x',alpha=.3)
ax[1].legend(fontsize=7.5,loc='upper center',bbox_to_anchor=(0.5,-0.06),ncol=4,frameon=False)
ax[1].set_title('② 2022年→直近4四半期：1人当たり名目可処分所得の項目別寄与（％）\n賃金の寄与は他国と大差ないが、日本は社会給付の伸びが小さい',fontsize=12)
for a in (ax[0],ax[1]):
    for t in a.get_yticklabels():
        if t.get_text().startswith('日本'): t.set_color('#C44E52'); t.set_fontweight('bold')
fig.text(.01,.004,'出典：OECD「Quarterly Sector Accounts」「Quarterly National Accounts」、日本は内閣府「家計可処分所得・家計貯蓄率四半期別速報」「GDP速報」（家計部門）より作成。\n季節調整値。直近4四半期は原則2025年7-9月期〜2026年4-6月期（フランスは2025年4-6月期〜2026年1-3月期）。\n＊韓国は四半期の所得データがないため2022年→2025年の年次。†米国・イタリアは一部項目が欠け、その他に含む。',fontsize=6.5)
plt.tight_layout(rect=(0,.05,1,1)); plt.savefig('02_chart_2022q.png',dpi=130)
