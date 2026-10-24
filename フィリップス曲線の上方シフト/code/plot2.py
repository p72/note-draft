import sys; sys.path.insert(0,'/mnt/skills/plugins/estat-api')
from scripts.estat_api import setup_japanese_font; setup_japanese_font()
import pandas as pd, numpy as np, statsmodels.api as sm, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
d=pd.read_csv('panel2.csv',index_col=0); d.index=pd.PeriodIndex(d.index,freq='Q')
D=['D_tax14','D_tax19','D_covid']; X=['cons_DI','wage_l1','imp_l24']
s=d.loc['2013Q1':,['core_exmob']+X+D+['D_shift']].dropna()
m=sm.OLS(s.core_exmob,sm.add_constant(s.drop(columns='core_exmob'))).fit(cov_type='HAC',cov_kwds={'maxlags':4})
base=s.loc['2013Q1':'2019Q3',X].mean()
fitted=m.fittedvalues; 
c=pd.DataFrame({'需給DI（短観3業種）':m.params['cons_DI']*(s.cons_DI-base.cons_DI),
                '賃金（所定内・一般、前期）':m.params['wage_l1']*(s.wage_l1-base.wage_l1),
                '輸入物価（2〜4期前）':m.params['imp_l24']*(s.imp_l24-base.imp_l24),
                'シフトダミー（2022年4-6月期〜）':m.params['D_shift']*s.D_shift,
                '説明できない残差':m.resid})
c=c+0; ref=m.params['const']+(m.params[X]*base).sum()   # 平時の水準
p=c.loc['2021Q1':]; act=s.core_exmob.loc['2021Q1':]
fig,ax=plt.subplots(figsize=(10,6))
cols=['#e4572e','#7a5195','#2a9d8f','#9a9a9a','#f2c14e']
x=np.arange(len(p)); pos=np.zeros(len(p)); neg=np.zeros(len(p))
for col,cc in zip(p.columns,cols):
    v=p[col].values; bot=np.where(v>=0,pos,neg)
    ax.bar(x,v,bottom=bot,color=cc,width=0.75,label=col,edgecolor='white',linewidth=0.6)
    pos+=np.where(v>=0,v,0); neg+=np.where(v<0,v,0)
ax.plot(x,act.values-ref,color='black',marker='o',ms=4,lw=1.6,label=f'実績（平時水準 {ref:.2f}% からの乖離）')
ax.axhline(0,color='black',lw=0.8)
ax.set_xticks(x); ax.set_xticklabels([f"{q.year%100:02d}Q{q.quarter}" if q.quarter in (1,3) else '' for q in p.index],fontsize=9)
ax.set_ylabel('%ポイント（2013〜19年の平時水準からの乖離）')
ax.set_title('欧米型コアCPI（携帯除く）の上振れ要因分解',loc='left',fontsize=13)
ax.set_ylim(-1.3,3.1); ax.legend(fontsize=8.5,frameon=False,loc='upper left',ncol=2); ax.grid(axis='y',alpha=0.3)
fig.text(0.01,0.005,f'注：2013年1-3月期〜26年7-9月期の回帰（HAC標準誤差）に基づく寄与。平時水準＝2013年1-3月〜19年7-9月期の説明変数平均での理論値。\n　　21〜22年は携帯値下げ除去の近似誤差とコロナ期ダミーの影響を受けるので幅を持って見ること。出所：総務省、厚生労働省、日本銀行を基に作成',fontsize=7.5,color='#555555')
plt.tight_layout(rect=(0,0.05,1,1)); plt.savefig('fig3_decomp.png',dpi=150)
print('ref',ref); print(p.loc['2023Q2':].round(2).to_string())

r=pd.read_csv('rolling.csv',index_col=0); r.index=pd.PeriodIndex(r.index,freq='Q')
fig,ax=plt.subplots(figsize=(10,5.5)); t=r.index.to_timestamp()
ax.fill_between(t,r.pos-1.96*r.se,r.pos+1.96*r.se,color='#1f6fb4',alpha=0.15,label='95%信頼区間')
ax.plot(t,r.pos,color='#1f6fb4',lw=2,label='DI＝−15・輸入物価0%のときの理論インフレ率')
ax.axvline(pd.Timestamp('2023-04-01'),color='#e4572e',ls='--',lw=1); ax.text(pd.Timestamp('2023-06-01'),0.05,'東洋経済の記事\n（2023年6月）',color='#e4572e',fontsize=9)
ax.axhline(0,color='black',lw=0.8); ax.set_ylim(-0.8,2.2)
ax.set_title('フィリップス曲線の「位置」の推移（10年ローリング回帰）',loc='left',fontsize=13)
ax.set_ylabel('欧米型コアCPI（携帯除く）前年比、%'); ax.set_xlabel('推計窓の最終期'); ax.grid(alpha=0.3); ax.legend(fontsize=9,frameon=False,loc='upper left')
fig.text(0.01,0.005,'注：40四半期の窓で CPI ＝ a ＋ b×需給DI ＋ c×輸入物価（2〜4期前）＋ 消費税・コロナ期ダミー を推計し、DI＝−15・輸入物価0%での理論値を表示。\n　　値が上がる＝曲線が上方シフト。出所：総務省、日本銀行を基に作成\n　　「記事」：末廣徹「やっぱり日本は｢デフレ｣に戻るのかもしれない」東洋経済オンライン、2023年6月14日（https://toyokeizai.net/articles/-/678868）',fontsize=7.5,color='#555555')
plt.tight_layout(rect=(0,0.08,1,1)); plt.savefig('fig4_rolling.png',dpi=150)
