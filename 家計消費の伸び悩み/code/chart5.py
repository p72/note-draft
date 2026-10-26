import sys, pandas as pd, numpy as np, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
sys.path.insert(0,'/mnt/skills/plugins/esri-data'); from scripts.esri_data import setup_japanese_font; setup_japanese_font()
t=pd.read_csv('burden.csv'); g=['34歳以下','35～39歳','40～44歳','45～49歳','50～54歳','55～59歳','60～64歳','平均']
a=t[t.year==2019].set_index('age').loc[g]; b=t[t.year==2025].set_index('age').loc[g]
lab=[s.replace('歳','') for s in g]; x=np.arange(len(g))
fig,ax=plt.subplots(3,1,figsize=(9,14))
d=lambda c:100*np.log(b[c]/a[c])
ax[0].bar(x-.2,d('実質可処分'),.4,color='#4C72B0',label='実質可処分所得'); ax[0].bar(x+.2,d('実質消費'),.4,color='k',label='実質消費支出')
ax[0].axhline(0,color='gray',lw=.8); ax[0].set_xticks(x); ax[0].set_xticklabels(lab); ax[0].legend(fontsize=9); ax[0].grid(axis='y',alpha=.3)
ax[0].set_title('① 2019→2025年の変化（勤労者世帯、対数％）\n30〜40代は所得が増えたのに消費は減った',fontsize=12)
comp=[('預貯金','#4C72B0'),('保険','#55A868'),('有価証券','#8172B2'),('住宅ローン返済','#DD8452')]
g2=['34歳以下','35～39歳','40～44歳','45～49歳','平均']; xx=np.arange(len(g2))
for off,src,alpha,yl in [(-.2,a,.45,'2019'),(.2,b,1,'2025')]:
    bot=np.zeros(len(g2))
    for nm,c in comp:
        vals=src.loc[g2,nm].clip(lower=0).values
        ax[1].bar(xx+off,vals,.38,bottom=bot,color=c,alpha=alpha,label=nm if yl=='2025' else None); bot+=vals
    for i,vv in enumerate(src.loc[g2,'黒字率']): ax[1].text(xx[i]+off,bot[i]+.8,f'{yl[2:]}年\n{vv:.0f}',ha='center',fontsize=7)
ax[1].set_xticks(xx); ax[1].set_xticklabels([s.replace('歳','') for s in g2]); ax[1].set_ylim(0,60); ax[1].legend(fontsize=8,ncol=4,loc='upper right')
ax[1].set_title('② 黒字の使い道（可処分所得比、％）　左＝2019年（薄）、右＝2025年\n増えた黒字はほぼ預貯金へ（数字は黒字率）',fontsize=12)
ax[2].bar(x-.2,a['負担率'],.4,color='#BBBBBB',label='2019年'); ax[2].bar(x+.2,b['負担率'],.4,color='#C44E52',label='2025年')
ax[2].set_xticks(x); ax[2].set_xticklabels(lab); ax[2].set_ylim(0,25); ax[2].legend(fontsize=9); ax[2].grid(axis='y',alpha=.3)
ax[2].set_title('③ 税・社会保険料の負担率（非消費支出÷実収入、％）\nほぼ横ばい',fontsize=12)
fig.text(0.01,0.003,'出典：総務省「家計調査（家計収支編）」年報 二人以上の世帯のうち勤労者世帯・世帯主の年齢階級別、「消費者物価指数」より作成',fontsize=7)
plt.tight_layout(rect=(0,0.01,1,1)); plt.savefig('worker_surplus.png',dpi=130)
