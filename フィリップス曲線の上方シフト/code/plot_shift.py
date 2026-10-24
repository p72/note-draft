# 物差し別のシフト幅（2022年4-6月期以降ダミー）を推計し、95%信頼区間つきで図示する
import sys, os; sys.path.insert(0,'/mnt/skills/plugins/estat-api')
from scripts.estat_api import setup_japanese_font; setup_japanese_font()
import pandas as pd, numpy as np, statsmodels.api as sm, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
here=os.path.dirname(os.path.abspath(__file__))
d=pd.read_csv(os.path.join(here,'panel2.csv'),index_col=0); d.index=pd.PeriodIndex(d.index,freq='Q')
D=['D_tax14','D_tax19','D_covid','D_shift']
rows=[]
for x,lab in [('cons_DI','消費者に近い需給\n（短観3業種DI）'),('gap_lead2','日銀の需給ギャップ\n（2四半期先行）')]:
    for a,sl in [('2004Q1','2004年〜'),('2013Q1','2013年〜')]:
        cols=[x,'imp_l24']+D; t=d.loc[a:,['core_exmob']+cols].dropna()
        m=sm.OLS(t.core_exmob,sm.add_constant(t[cols])).fit(cov_type='HAC',cov_kwds={'maxlags':4})
        rows.append(dict(x=lab,samp=sl,b=m.params.D_shift,se=m.bse.D_shift,p=m.pvalues.D_shift,n=int(m.nobs)))
r=pd.DataFrame(rows); r.to_csv(os.path.join(here,'shift_est.csv'),index=False); print(r.round(3))
fig,ax=plt.subplots(figsize=(9,5))
labs=list(dict.fromkeys(r.x)); col={'2004年〜':'#1f6fb4','2013年〜':'#e4572e'}
for i,lab in enumerate(labs):
    for j,(sl,off) in enumerate([('2004年〜',-0.12),('2013年〜',0.12)]):
        q=r[(r.x==lab)&(r.samp==sl)].iloc[0]
        ax.errorbar(i+off,q.b,yerr=1.96*q.se,fmt='o',ms=9,capsize=5,lw=2,color=col[sl],label=f'推計期間 {sl}2026年7-9月期' if i==0 else None)
        ax.annotate(f'{q.b:+.1f}',(i+off,q.b),xytext=(10,0),textcoords='offset points',va='center',fontsize=10,color='#333333')
ax.axhline(0,color='black',lw=0.9); ax.set_xticks(range(len(labs))); ax.set_xticklabels(labs,fontsize=11); ax.set_xlim(-0.6,1.6)
ax.set_ylabel('2022年4-6月期以降の上振れ幅（%ポイント）'); ax.grid(axis='y',alpha=0.3); ax.legend(frameon=False,fontsize=9,loc='upper left')
ax.set_title('物差しによって変わる「上方シフト」の大きさ',loc='left',fontsize=13)
fig.text(0.01,0.005,'注：欧米型コアCPI（携帯除く）前年比を、需給・輸入物価（2〜4期前）・消費税とコロナ期のダミー・2022年4-6月期以降のダミーで回帰したときの最後のダミーの係数。\n　　2つの物差しで同じ標本（共通の四半期）を使用。縦線は95%信頼区間（HAC標準誤差）で、0をまたがなければ統計的に有意。出所：総務省、日本銀行を基に作成',fontsize=7.5,color='#555555')
plt.tight_layout(rect=(0,0.07,1,1)); plt.savefig(os.path.join(here,'..','01_chart_shift.png'),dpi=150)
