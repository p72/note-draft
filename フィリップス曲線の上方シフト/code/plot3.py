import sys; sys.path.insert(0,'/mnt/skills/plugins/estat-api')
from scripts.estat_api import setup_japanese_font; setup_japanese_font()
import pandas as pd, numpy as np, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
d=pd.read_csv('panel3.csv',index_col=0); d.index=pd.PeriodIndex(d.index,freq='Q')
s=d.loc['2004Q1':]; t=s.index.to_timestamp()
fig,ax=plt.subplots(figsize=(10,5.5))
for a,b,lab in [('2014Q2','2015Q1','消費税'),('2019Q4','2022Q1','消費税・無償化・コロナ・携帯値下げ')]:
    ax.axvspan(pd.Period(a).to_timestamp(),pd.Period(b).to_timestamp(how='end'),color='#eeeeee',zorder=0)
    ax.text(pd.Period(a).to_timestamp(),4.6,lab,fontsize=8,color='#777777')
ax.plot(t,s.gsvc,color='#e4572e',lw=2,label='一般サービス物価（家賃・携帯・宿泊除く）前年比')
ax.plot(t,s.wage,color='#1f6fb4',lw=2,label='所定内給与（一般労働者）前年比')
ax.axhline(0,color='black',lw=0.8); ax.set_ylim(-1.5,5); ax.grid(alpha=0.3)
ax.set_ylabel('%'); ax.set_title('サービス物価と賃金',loc='left',fontsize=13); ax.legend(frameon=False,fontsize=9,loc='upper left',bbox_to_anchor=(0,0.93))
for y,lab,c in [(s.gsvc.iloc[-1],f'{s.gsvc.iloc[-1]:.1f}%','#e4572e'),(s.wage.iloc[-1],f'{s.wage.iloc[-1]:.1f}%','#1f6fb4')]:
    ax.annotate(lab,(t[-1],y),xytext=(6,0),textcoords='offset points',color=c,fontsize=9,va='center')
fig.text(0.01,0.005,'注：サービス物価は総務省CPI（2025年基準）の外食と他のサービスから、通信料（携帯電話）・宿泊料を除いた試算値（四半期平均）。網掛けは制度要因で振れの大きい期間。\n　　賃金は厚労省「毎月勤労統計」所定内給与・一般労働者・5人以上（26年7-9月期は7・8月平均）。出所：総務省、厚生労働省を基に作成',fontsize=7.5,color='#555555')
plt.tight_layout(rect=(0,0.06,1,1)); plt.savefig('fig5_svc_wage.png',dpi=150)

r=pd.read_csv('lagcoef.csv')
fig,axs=plt.subplots(1,2,figsize=(11,5),sharey=True)
for ax,di,ttl in [(axs[0],False,'需給DIなし'),(axs[1],True,'需給DIあり')]:
    for a,c,lab in [('2004Q1','#1f6fb4','2004年〜'),('2013Q1','#e4572e','2013年〜')]:
        q=r[(r.DI==di)&(r.start==a)]; off=-0.08 if a=='2004Q1' else 0.08
        ax.errorbar(q.lag+off,q.coef,yerr=1.96*q.se,fmt='o',color=c,capsize=3,ms=6,label=lab)
    ax.axhline(0,color='black',lw=0.8); ax.set_title(ttl,fontsize=11,loc='left'); ax.grid(alpha=0.3); ax.set_xticks(range(9))
    ax.set_xlabel('賃金のラグ（四半期）')
axs[0].set_ylabel('賃金1%ptあたりのサービス物価への効果（%pt）'); axs[0].legend(frameon=False,fontsize=9)
fig.suptitle('賃金→サービス物価の係数（ラグ別、95%信頼区間）',x=0.01,ha='left',fontsize=13)
fig.text(0.01,0.005,'注：被説明変数は一般サービス物価（家賃・携帯・宿泊除く）前年比。各点は賃金のラグを1つずつ入れた別々の回帰。消費税・無償化・コロナ期ダミーと\n　　2022年4-6月期以降のシフトダミーを含む。HAC標準誤差。出所：総務省、厚生労働省、日本銀行を基に作成',fontsize=7.5,color='#555555')
plt.tight_layout(rect=(0,0.07,1,0.95)); plt.savefig('fig6_wage_lags.png',dpi=150)
