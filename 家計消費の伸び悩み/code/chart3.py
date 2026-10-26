import sys, pandas as pd, numpy as np, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
sys.path.insert(0,'/mnt/skills/plugins/esri-data'); from scripts.esri_data import setup_japanese_font; setup_japanese_font()
k=pd.read_csv('levels3.csv',index_col=0); k.index=pd.PeriodIndex(k.index,freq='Q')
fig,ax=plt.subplots(3,1,figsize=(9,13))
s=k.loc['2010Q1':]; x=np.arange(len(s)); xt=range(0,len(s),8); xl=[str(p.year) for p in s.index[::8]]
ax[0].plot(x,s.sr,'k-',lw=2,label='家計貯蓄率（実績）'); ax[0].plot(x,s.fitA,'--',color='#4C72B0',lw=1.6,label='推計値（資産/所得・消費者態度・物価）')
c=list(s.index).index(pd.Period('2020Q1','Q')); ax[0].axvspan(c-.5,c+7.5,color='gray',alpha=.15); ax[0].text(c+2.2,-2.3,'推計から除外（コロナ期）',fontsize=8)
ax[0].set_ylim(-3,21); ax[0].axhline(0,color='gray',lw=.8); ax[0].set_xticks(xt); ax[0].set_xticklabels(xl); ax[0].legend(fontsize=9); ax[0].grid(alpha=.3)
ax[0].set_title('① 家計貯蓄率：実績と推計値（季調、％）\n2026年は推計値を約2.5pt上回る',fontsize=12)
s=k.loc['2019Q1':]; x=np.arange(len(s)); xt=range(0,len(s),4); xl=[str(p.year) for p in s.index[::4]]
ax[1].bar(x,s.cum_exc.fillna(0)/1000,color='#55A868',label='超過貯蓄の累積（兆円、左軸）')
ax[1].set_ylabel('兆円'); a2=ax[1].twinx(); a2.plot(x,s.nw_y,'-o',ms=3,color='#C44E52',label='純金融資産÷可処分所得（倍、右軸）'); a2.set_ylabel('倍')
h1,l1=ax[1].get_legend_handles_labels(); h2,l2=a2.get_legend_handles_labels(); ax[1].legend(h1+h2,l1+l2,fontsize=8,loc='lower right')
ax[1].set_xticks(xt); ax[1].set_xticklabels(xl); ax[1].set_title('② コロナ期の超過貯蓄（2015〜19年平均の貯蓄率との差）と資産効果',fontsize=12)
s=k.loc['2024Q1':]; x=np.arange(len(s))
cr=100*np.log(k.cr).diff().loc['2024Q1':]; yr=100*np.log(k.yd/k.P).diff().loc['2024Q1':]
ax[2].bar(x-.2,yr,.4,color='#4C72B0',label='実質可処分所得'); ax[2].bar(x+.2,cr,.4,color='k',label='実質家計消費')
ax[2].axhline(0,color='gray',lw=.8); ax[2].set_xticks(x); ax[2].set_xticklabels([f'{p.year%100}Q{p.quarter}' for p in s.index]); ax[2].legend(fontsize=9)
ax[2].set_title('③ 前期比（％）：所得が伸びても消費は遅れて少しだけ反応',fontsize=12)
fig.text(0.01,0.003,'出典：内閣府「家計可処分所得・家計貯蓄率四半期別速報」「GDP速報」「消費動向調査」、日本銀行「資金循環統計」より作成',fontsize=7)
plt.tight_layout(rect=(0,0.01,1,1)); plt.savefig('saving_drivers.png',dpi=130)
