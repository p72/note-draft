import sys, pandas as pd, numpy as np, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
sys.path.insert(0,'/mnt/skills/plugins/esri-data'); from scripts.esri_data import setup_japanese_font; setup_japanese_font()
t=pd.read_csv('csi_age.csv'); ann=pd.read_csv('csi_age_ann.csv',index_col=0)
A=['29歳以下','30～39歳','40～49歳','50～59歳','60～69歳','70歳以上']; lab=[a.replace('歳','') for a in A]
fig,ax=plt.subplots(3,1,figsize=(9,13)); x=np.arange(len(A))
its=[('消費者態度指数','k'),('暮らし向き','#4C72B0'),('収入の増え方','#55A868'),('雇用環境','#8172B2'),('買い時判断','#DD8452')]
for i,(it,c) in enumerate(its):
    v=[t[(t.age==a)&(t.item==it)]['Δ19→25'].iloc[0] for a in A]
    ax[0].bar(x+(i-2)*.16,v,.16,color=c,label=it)
ax[0].axhline(0,color='gray',lw=.8); ax[0].set_xticks(x); ax[0].set_xticklabels(lab); ax[0].legend(fontsize=8,ncol=3,loc='lower right'); ax[0].grid(axis='y',alpha=.3)
ax[0].set_ylim(-13,2); ax[0].set_title('① 消費者意識指標の変化 2019→2025年（年平均、ポイント）\n若い世帯ほど「暮らし向き」が悪化、「収入の増え方」はほぼ不変',fontsize=12)
for a,c,ls in [('30～39歳','#C44E52','-'),('60～69歳','#4C72B0','-')]:
    ax[1].plot(ann.index,ann[f'{a}|暮らし向き'],ls,marker='o',ms=3,color=c,label=f'{a} 暮らし向き')
    ax[1].plot(ann.index,ann[f'{a}|収入の増え方'],'--',marker='s',ms=3,color=c,label=f'{a} 収入の増え方')
ax[1].legend(fontsize=8,ncol=2); ax[1].grid(alpha=.3); ax[1].set_xlim(2013.5,2026.5)
ax[1].set_title('② 30代と60代の比較（年平均、2026年は1〜9月）',fontsize=12)
pe=pd.DataFrame({'2019':[21.1,17.1,21.2,21.8,25.9,26.4],'2025':[45.2,46.3,47.9,52.2,54.9,51.3]},index=A)
ax[2].bar(x-.2,pe['2019'],.4,color='#BBBBBB',label='2019年'); ax[2].bar(x+.2,pe['2025'],.4,color='#C44E52',label='2025年')
ax[2].set_xticks(x); ax[2].set_xticklabels(lab); ax[2].legend(fontsize=9); ax[2].grid(axis='y',alpha=.3)
ax[2].set_title('③ 1年後に物価が5％以上上がると予想する世帯の割合（％）\n若い世帯のほうがむしろ低い',fontsize=12)
fig.text(0.01,0.003,'出典：内閣府「消費動向調査」長期時系列表（二人以上の世帯、世帯主の年齢階級別、原数値）2026年9月調査分より作成（e-Stat）',fontsize=7)
plt.tight_layout(rect=(0,0.01,1,1)); plt.savefig('mind_age.png',dpi=130)
