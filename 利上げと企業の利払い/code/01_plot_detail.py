import sys, pandas as pd, numpy as np, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
sys.path.insert(0,'<estat-api スキルのディレクトリ>')
from scripts.estat_api import setup_japanese_font; setup_japanese_font()
o=pd.read_pickle('detail.pkl')
c=pd.read_csv('ratio.csv',index_col=0)['call']; c.index=pd.PeriodIndex(c.index,freq='Q')
ts=lambda s:s.index.to_timestamp(how='end')
src='出所：財務省「法人企業統計調査」（e-Stat）、日本銀行。後方4四半期合計ベース（負債は4期平均）。直近2026年4-6月期'
# --- size
sz={'25':('大企業（資本金10億円以上）','#c0392b'),'24':('中堅（1億〜10億円）','#e67e22'),'19':('中小（1千万〜1億円）','#2c7fb8')}
fig,ax=plt.subplots(3,1,figsize=(11,13),gridspec_kw={'height_ratios':[3,2,2]})
for k,(n,col) in sz.items():
    s=o[('104',k)]
    ax[0].plot(ts(s.loc['1970':]),s.gross.loc['1970':].clip(upper=250),color=col,lw=1.8,label=n)
    ax[1].plot(ts(s.loc['1986':]),s.net.loc['1986':],color=col,lw=1.6,label=n)
    t=s.loc['2012':]; ax[2].plot(ts(t),t.eff,color=col,lw=2,label=n)
a2=ax[0].twinx(); cc=c.loc['1970':]; a2.plot(ts(cc),cc,'k--',lw=1.1,label='コールレート（右軸）'); a2.set_ylim(-2,14); a2.set_ylabel('%')
ax[0].set_ylim(-20,140*2); ax[0].set_ylim(-17.5,245)
ax[0].set_title('規模別：支払利息等 ÷ 経常利益（%）'); ax[1].set_title('規模別：純利払い（支払利息等−受取利息等）÷ 経常利益（%）')
ax[2].set_title('規模別：実効借入金利（支払利息等 ÷ 有利子負債、%）2012年〜')
cc=c.loc['2012':]; ax[2].plot(ts(cc),cc,'k--',lw=1.1,label='コールレート')
h,l=ax[0].get_legend_handles_labels(); h2,l2=a2.get_legend_handles_labels(); ax[0].legend(h+h2,l+l2,fontsize=9,loc='upper right')
for a in ax: a.grid(alpha=.3); a.axhline(0,color='gray',lw=.8); a.set_ylabel('%')
ax[1].legend(fontsize=9); ax[2].legend(fontsize=9)
fig.suptitle('日本の法人企業：規模別の利払い負担（全産業・除く金融保険業）',fontsize=13)
fig.text(.01,.005,src,fontsize=8); plt.tight_layout(rect=(0,.015,1,.98)); plt.savefig('../01_chart_size.png',dpi=140); plt.close()
# --- industry
names={'108':'製造業','144':'非製造業','107':'建設業','135':'電気業','142':'情報通信業','134':'運輸・郵便','129':'卸売・小売','130':'不動産業','156':'宿泊・飲食','137':'サービス業','115':'化学','118':'鉄鋼','123':'自動車'}
rows=[]
for k,n in names.items():
    s=o[(k,'26')]
    rows.append(dict(n=n,g19=s.gross.loc['2019Q4'],g26=s.gross.iloc[-1],op26=s.op.iloc[-1],net=s.net.iloc[-1],
        effmin=s.eff.loc['2020Q1':].min(),eff26=s.eff.iloc[-1],de=s.debt_ebit.iloc[-1]))
t=pd.DataFrame(rows).sort_values('de')
fig,ax=plt.subplots(1,3,figsize=(14,7),sharey=True)
y=np.arange(len(t))
ax[0].barh(y-.2,t.g19,.4,color='#bbb',label='2019年10-12月期'); ax[0].barh(y+.2,t.g26,.4,color='#c0392b',label='2026年4-6月期')
ax[0].set_title('支払利息等 ÷ 経常利益（%）'); ax[0].legend(fontsize=9)
ax[1].barh(y-.2,t.effmin,.4,color='#bbb',label='2020年以降の最低'); ax[1].barh(y+.2,t.eff26,.4,color='#2c7fb8',label='2026年4-6月期')
ax[1].set_title('実効借入金利（%）'); ax[1].legend(fontsize=9)
ax[2].barh(y,t.de,.6,color='#8e44ad'); ax[2].set_title('有利子負債 ÷ 営業利益（倍）\n＝金利+1%ptで営業利益の何%が飛ぶか')
for i,v in enumerate(t.de): ax[2].text(v+.3,i,f'{v:.1f}倍',va='center',fontsize=9)
for i,(a,b) in enumerate(zip(t.g19,t.g26)): ax[0].text(max(a,b)+.5,i,f'{b:.1f}',va='center',fontsize=8)
ax[0].set_yticks(y); ax[0].set_yticklabels(t.n)
for a in ax: a.grid(axis='x',alpha=.3)
fig.suptitle('業種別の利払い負担と金利感応度（全規模）— 上ほど借金依存＝利上げに弱い',fontsize=13)
fig.text(.01,.005,src,fontsize=8)
plt.tight_layout(rect=(0,.02,1,.96)); plt.savefig('../01_chart_industry.png',dpi=140)
print(t.round(2).to_string())
