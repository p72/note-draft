import sys, pandas as pd, numpy as np, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
sys.path.insert(0,'/mnt/skills/plugins/esri-data'); from scripts.esri_data import setup_japanese_font; setup_japanese_font()
A=pd.read_csv('age_apc_w.csv',index_col=0); Aavg=pd.read_csv('apc_w_avg.csv',index_col=0).iloc[:,0]
W=pd.read_csv('age_w.csv',index_col=0); ss=pd.read_csv('shiftshare.csv'); cpi=pd.read_csv('cpi_y.csv',index_col=0).iloc[:,0]
fig,ax=plt.subplots(3,1,figsize=(9,13))
x=np.arange(A.shape[1]); lab=[c.replace('歳','') for c in A.columns]
for i,(y,c) in enumerate([(2019,'#BBBBBB'),(2022,'#8DA0CB'),(2025,'#4C72B0')]):
    ax[0].bar(x+(i-1)*.27,A.loc[y],.27,color=c,label=f'{y}年')
ax[0].set_xticks(x); ax[0].set_xticklabels(lab,fontsize=9); ax[0].set_ylim(40,90); ax[0].legend(fontsize=9); ax[0].grid(axis='y',alpha=.3)
ax[0].set_title('① 勤労者世帯の平均消費性向（世帯主年齢別、％）\n若い世代ほどコロナ後に低下したまま',fontsize=12)
# shift-share in real terms
rows=[]
for _,r in ss.iterrows():
    a,b=[int(v) for v in r['期間'].split('→')]; p=(cpi[b]/cpi[a]-1)*100
    rows.append((r['期間'],r['年齢構成要因'],r['年齢内要因']-p,r['平均消費支出変化%']-p,p))
xs=np.arange(len(rows))
ax[1].bar(xs-.2,[r[1] for r in rows],.4,color='#DD8452',label='年齢構成要因（高齢化）')
ax[1].bar(xs+.2,[r[2] for r in rows],.4,color='#4C72B0',label='年齢内要因（実質）')
ax[1].plot(xs,[r[3] for r in rows],'kD',ms=7,label='実質平均消費支出の変化')
for i,r in enumerate(rows): ax[1].text(i,r[3]+0.6,f'{r[3]:.1f}',ha='center',fontsize=9)
ax[1].axhline(0,color='gray',lw=.8); ax[1].set_xticks(xs); ax[1].set_xticklabels([r[0] for r in rows]); ax[1].legend(fontsize=8,loc='lower right'); ax[1].set_ylim(-18,1.5)
ax[1].set_title('② 1世帯当たり消費支出の変化の分解（二人以上の世帯、％）\n実質化はCPI総合',fontsize=12)
yrs=W.index; s65=100*W[['65～69歳','70歳以上']].sum(axis=1)
ax[2].plot(yrs,s65,'-o',ms=3,color='#DD8452',label='世帯主65歳以上の割合（二人以上世帯、左軸）')
a2=ax[2].twinx(); a2.plot(Aavg.index,Aavg.values,'-s',ms=3,color='#4C72B0',label='勤労者世帯の平均消費性向（右軸）')
h1,l1=ax[2].get_legend_handles_labels(); h2,l2=a2.get_legend_handles_labels(); ax[2].legend(h1+h2,l1+l2,fontsize=8,loc='lower left')
ax[2].set_ylabel('％'); a2.set_ylabel('％'); ax[2].grid(alpha=.3); ax[2].set_xlim(1999.5,2025.5)
ax[2].set_title('③ 高齢化は2017年頃から頭打ち、消費性向は2015年以降に低下\n（2018年に家計簿の改正あり、前後比較は要注意）',fontsize=12)
fig.text(0.01,0.003,'出典：総務省「家計調査（家計収支編）」年報 世帯主の年齢階級別、「消費者物価指数」より作成（e-Stat API）',fontsize=7)
plt.tight_layout(rect=(0,0.01,1,1)); plt.savefig('age_effect.png',dpi=130)
for r in rows: print([round(v,2) if isinstance(v,float) else v for v in r])
