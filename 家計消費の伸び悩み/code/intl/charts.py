import sys, pandas as pd, numpy as np, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
sys.path.insert(0,'ESRI_DATA_SKILL_DIR'); from scripts.esri_data import setup_japanese_font; setup_japanese_font()
N={'JPN':'日本','USA':'米国','GBR':'英国','DEU':'ドイツ','FRA':'フランス','ITA':'イタリア','CAN':'カナダ','KOR':'韓国','AUS':'豪州'}
R=pd.read_csv('decomp_intl.csv'); I=pd.read_csv('income_decomp.csv'); P=pd.read_csv('panel.csv')
SRC='出典：OECD「Annual non-financial accounts by institutional sector」「Annual GDP and components」「Population」より作成。家計＋対家計民間非営利団体（S1M）、1人当たり、累積の対数変化率'
def bars(ax,per,title,three=False):
    g=R[R.period==per].set_index('area').sort_values('real_C_pc')
    y=np.arange(len(g)); lab=[N[a] for a in g.index]
    if three:
        parts=[('名目可処分所得',g.nomYd_pc,'#4C72B0'),('物価（消費デフレーター）',-g.prices,'#DD8452'),('平均消費性向',g.APC,'#55A868')]
    else:
        parts=[('実質可処分所得',g.realYd_pc,'#4C72B0'),('平均消費性向',g.APC,'#55A868')]
    pos=np.zeros(len(g)); neg=np.zeros(len(g))
    for nm,v,c in parts:
        v=v.values; b=np.where(v>=0,pos,neg); ax.barh(y,v,left=b,color=c,label=nm,height=.6)
        pos+=np.where(v>=0,v,0); neg+=np.where(v<0,v,0)
    ax.plot(g.real_C_pc,y,'kD',ms=7,label='1人当たり実質消費')
    for i,v in enumerate(g.real_C_pc): ax.text(v,i+.33,f'{v:.0f}',ha='center',fontsize=8)
    ax.set_yticks(y); ax.set_yticklabels(lab)
    for t in ax.get_yticklabels():
        if t.get_text()=='日本': t.set_color('#C44E52'); t.set_fontweight('bold')
    ax.axvline(0,color='gray',lw=.8); ax.grid(axis='x',alpha=.3); ax.legend(fontsize=8,loc='upper center',bbox_to_anchor=(0.5,-0.07),ncol=4,frameon=False); ax.set_title(title,fontsize=12)
# Fig A: long run
fig,ax=plt.subplots(figsize=(9,6)); bars(ax,'2000-2024','2000→2024年：1人当たり実質消費の分解（対数％）\n日本は所得がほとんど伸びず、消費性向の上昇で消費を支えた')
fig.text(.01,.005,SRC,fontsize=6.5); plt.tight_layout(rect=(0,.03,1,1)); plt.savefig('02_chart_longrun.png',dpi=130); plt.close()
# Fig B: 2019-2024 three parts
fig,ax=plt.subplots(figsize=(9,6)); bars(ax,'2019-2024','2019→2024年：1人当たり実質消費の分解（対数％）\n日本は物価上昇が小さめだったが、名目所得の伸びはさらに小さかった',three=True)
fig.text(.01,.005,SRC,fontsize=6.5); plt.tight_layout(rect=(0,.03,1,1)); plt.savefig('02_chart_recent.png',dpi=130); plt.close()
# Fig C: income components 2000-2024
g=I[I.period=='2000-2024'].set_index('area').sort_values('Yd_pc_pct')
cols=[('雇用者報酬','#C44E52'),('営業余剰・混合所得','#937860'),('財産所得（純）','#8172B2'),('社会給付','#55A868'),('所得税等','#4C72B0'),('社会負担','#64B5CD'),('その他','#BBBBBB')]
fig,ax=plt.subplots(figsize=(9,6)); y=np.arange(len(g)); pos=np.zeros(len(g)); neg=np.zeros(len(g))
for nm,c in cols:
    v=g[nm].fillna(0).values; b=np.where(v>=0,pos,neg); ax.barh(y,v,left=b,color=c,height=.6,label=nm if nm not in ('所得税等','社会負担') else nm+'（控除）')
    pos+=np.where(v>=0,v,0); neg+=np.where(v<0,v,0)
ax.plot(g.Yd_pc_pct,y,'kD',ms=7,label='1人当たり名目可処分所得')
for i,v in enumerate(g.Yd_pc_pct): ax.text(v+4,i-.1,f'{v:.0f}',fontsize=8)
ax.set_yticks(y); ax.set_yticklabels([N[a] for a in g.index])
for t in ax.get_yticklabels():
    if t.get_text()=='日本': t.set_color('#C44E52'); t.set_fontweight('bold')
ax.axvline(0,color='gray',lw=.8); ax.grid(axis='x',alpha=.3); ax.legend(fontsize=7.5,loc='upper center',bbox_to_anchor=(0.5,-0.07),ncol=4,frameon=False)
ax.set_title('2000→2024年：1人当たり名目可処分所得の増加率と項目別寄与（％）\n日本は雇用者報酬がほとんど増えていない',fontsize=12)
fig.text(.01,.005,'出典：OECD「Annual non-financial accounts by institutional sector」「Population」より作成。豪州は社会給付の内訳なし（その他に含む）',fontsize=6.5)
plt.tight_layout(rect=(0,.03,1,1)); plt.savefig('02_chart_income.png',dpi=130); plt.close()
# Fig D: index lines real Yd pc and real C pc, 2000=100
fig,axs=plt.subplots(1,2,figsize=(11,5),sharey=True)
for ax,(col,ttl) in zip(axs,[('ryd','1人当たり実質可処分所得'),('rc','1人当たり実質消費')]):
    ends=[]
    for a in N:
        d=P[P.area==a].set_index('TIME_PERIOD').loc[2000:2024]
        s=(d.Yd/d.P/d['pop']) if col=='ryd' else (d.Cr/d['pop'])
        s=100*s/s.loc[2000]
        if a=='JPN': ax.plot(s.index,s,color='#C44E52',lw=3,label='日本',zorder=5)
        else: ax.plot(s.index,s,color='#999999',lw=1); ends.append((s.iloc[-1],N[a]))
    ends.sort(); last=-1e9
    for v,nm in ends:
        yv=max(v,last+3.2); ax.text(2024.4,yv,nm,fontsize=7.5,va='center',color='#555555'); last=yv
    ax.set_title(ttl+'（2000年＝100）',fontsize=11); ax.grid(alpha=.3); ax.set_xlim(2000,2027)
axs[0].legend(fontsize=9,loc='upper left')
fig.suptitle('日本は所得も消費も最下位グループ、ただし消費は所得より伸びている',fontsize=12)
fig.text(.01,.005,'出典：OECDより作成。実質可処分所得は家計最終消費支出デフレーターで実質化。',fontsize=7)
plt.tight_layout(rect=(0,.03,1,.96)); plt.savefig('02_chart_index.png',dpi=130); plt.close()
