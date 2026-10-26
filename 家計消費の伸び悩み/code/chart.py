import sys, pandas as pd, numpy as np, matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
sys.path.insert(0,'/mnt/skills/plugins/esri-data')
from scripts.esri_data import setup_japanese_font
print('font',setup_japanese_font())
d=pd.read_csv('decomp.csv',index_col=0); k=pd.read_csv('levels.csv',index_col=0)
d.index=pd.PeriodIndex(d.index,freq='Q'); k.index=pd.PeriodIndex(k.index,freq='Q')
fig,ax=plt.subplots(4,1,figsize=(9,17))
# 1 decomposition
s=d.loc['2012Q1':]; x=np.arange(len(s)); lab=[str(p) if p.quarter==1 else '' for p in s.index]
parts=[('名目可処分所得',s.dYd_nom,'#4C72B0'),('消費デフレーター（物価）',-s.dP,'#DD8452'),('平均消費性向',s.dAPC,'#55A868')]
pos=np.zeros(len(s)); neg=np.zeros(len(s))
for nm,v,c in parts:
    v=v.values; b=np.where(v>=0,pos,neg); ax[0].bar(x,v,bottom=b,color=c,label=nm,width=0.8)
    pos+=np.where(v>=0,v,0); neg+=np.where(v<0,v,0)
ax[0].plot(x,s.dC_real.values,'k-o',ms=3,label='実質家計消費（前年比）')
ax[0].axhline(0,color='gray',lw=.8); ax[0].set_xticks(x); ax[0].set_xticklabels([l[:4] for l in lab],fontsize=8)
ax[0].set_ylim(-15,15); ax[0].set_title('① 実質家計消費の前年比分解（対数％ポイント）\n実質消費 ＝ 名目可処分所得 − 物価 ＋ 消費性向',fontsize=12)
ax[0].legend(fontsize=8,loc='lower left',ncol=2); ax[0].text(x[33],-13.5,'※2020年は±15で切り落とし',fontsize=7)
# 2 cumulative index 2021Q4=100
s=k.loc['2019Q1':]; base='2021Q4'
for nm,v,c in [('実質家計消費',s.cr,'k'),('実質可処分所得',s.yd/s.P,'#4C72B0'),('名目可処分所得',s.yd,'#8172B2'),('消費デフレーター',s.P,'#DD8452'),('名目雇用者報酬',s.comp,'#C44E52')]:
    ax[1].plot(range(len(s)),100*v/v[base],label=nm,color=c,lw=2 if nm.startswith('実質') else 1.3)
ax[1].axvline(list(s.index).index(pd.Period(base,'Q')),color='gray',ls='--',lw=.8)
ax[1].set_xticks(range(0,len(s),4)); ax[1].set_xticklabels([str(p.year) for p in s.index[::4]])
ax[1].set_title('② 2021年10-12月期＝100 の推移（季調）',fontsize=12); ax[1].legend(fontsize=8); ax[1].grid(alpha=.3)
# 3 Yd component contributions
s=d.loc['2019Q1':]; x=np.arange(len(s)); pos=np.zeros(len(s)); neg=np.zeros(len(s))
cols=['#C44E52','#937860','#8172B2','#55A868','#BBBBBB','#4C72B0','#64B5CD']
for (nm),c in zip(['雇用者報酬','営業余剰・混合所得','財産所得','社会給付','その他移転','税','社会負担'],cols):
    v=s['c_'+nm].values; b=np.where(v>=0,pos,neg); ax[2].bar(x,v,bottom=b,color=c,label=nm if nm not in('税','社会負担') else nm+'（控除）')
    pos+=np.where(v>=0,v,0); neg+=np.where(v<0,v,0)
ax[2].plot(x,s.dYd_nom.values,'k-o',ms=3,label='名目可処分所得（前年比）'); ax[2].axhline(0,color='gray',lw=.8)
ax[2].set_xticks(x[::4]); ax[2].set_xticklabels([str(p.year) for p in s.index[::4]])
ax[2].set_title('③ 名目可処分所得の前年比 項目別寄与度（％ポイント）',fontsize=12); ax[2].legend(fontsize=7,ncol=2,loc='upper left')
# 4 saving rate
s=k; ax[3].plot(range(len(s)),s.sr,color='#4C72B0'); ax[3].axhline(0,color='gray',lw=.8)
ax[3].set_xticks(range(0,len(s),8)); ax[3].set_xticklabels([str(p.year) for p in s.index[::8]],fontsize=8)
ax[3].set_ylim(-3,22); ax[3].grid(alpha=.3); ax[3].set_title('④ 家計貯蓄率（季調、％） 1994年〜',fontsize=12)
fig.text(0.01,0.003,'出典：内閣府「家計可処分所得・家計貯蓄率四半期別速報（2026年4-6月期）」「2026年4-6月期GDP2次速報」より作成',fontsize=7)
plt.tight_layout(rect=(0,0.01,1,1)); plt.savefig('consumption_decomp.png',dpi=130)
