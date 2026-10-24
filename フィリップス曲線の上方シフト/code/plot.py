import sys; sys.path.insert(0,'/mnt/skills/plugins/estat-api')
from scripts.estat_api import setup_japanese_font
import pandas as pd, numpy as np, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
font=setup_japanese_font(); print('font',font)
d=pd.read_csv('panel.csv',index_col=0); d.index=pd.PeriodIndex(d.index,freq='Q')
d['y']=d.core_exmob; d.loc['2014Q2':'2015Q1','y']-=1.5
G=dict(pre=('2013Q1','2020Q1','#9a9a9a','2013年1-3月期〜2020年1-3月期'),
       art=('2020Q2','2023Q1','#e4572e','2020年4-6月期〜2023年1-3月期（記事時点）'),
       new=('2023Q2','2026Q3','#1f6fb4','2023年4-6月期〜2026年7-9月期（記事以降）'))
def ql(p): return f"{p.year}年{p.quarter*3-2}-{p.quarter*3}月期"
def panel(ax,x,xlabel,title,xlim,lab_off=(25,40)):
    for k,(a,b,c,lab) in G.items():
        s=d.loc[a:b,['y',x]].dropna()
        ax.scatter(s[x],s.y,s=42 if k!='pre' else 30,color=c,edgecolor='white',linewidth=1,zorder=3,label=lab)
        if k!='pre': pass
    # trajectory since 2020Q2
    s=d.loc['2020Q2':,['y',x]].dropna()
    ax.plot(s[x],s.y,color='#bbbbbb',lw=0.8,zorder=1)
    for a,b,c,ls in [('2013Q1','2020Q1','#555555','--'),('2020Q2','2023Q1','#e4572e','--'),('2020Q2','2026Q3','#1f6fb4','-')]:
        s=d.loc[a:b,['y',x]].dropna(); k=np.polyfit(s[x],s.y,1); r2=np.corrcoef(s[x],s.y)[0,1]**2
        xs=np.linspace(s[x].min(),s[x].max(),10); ax.plot(xs,np.polyval(k,xs),ls,color=c,lw=1.6,zorder=2)
        tx={('2013Q1','2020Q1'):'13年1-3月〜20年1-3月',('2020Q2','2023Q1'):'20年4-6月〜23年1-3月',('2020Q2','2026Q3'):'20年4-6月〜26年7-9月'}[(a,b)]
        yield_txt=f"{tx}: y={k[0]:.3f}x{'+' if k[1]>=0 else ''}{k[1]:.2f}  R²={r2:.2f}"
        ax._fits=getattr(ax,'_fits',[])+[(yield_txt,c)]
    for i,(t,c) in enumerate(ax._fits):
        ax.text(0.98,0.04+0.055*i,t,transform=ax.transAxes,ha='right',fontsize=8.5,color='#333333',
                bbox=dict(facecolor='white',edgecolor=c,boxstyle='round,pad=0.25',lw=1))
    last=d[['y',x]].dropna().iloc[-1]; lp=d[['y',x]].dropna().index[-1]
    ax.annotate(f"直近値\n{ql(lp)}\n({last[x]:.1f}, {last.y:.2f}%)",xy=(last[x],last.y),xytext=lab_off,textcoords='offset points',
                fontsize=9,arrowprops=dict(arrowstyle='->',color='#1f6fb4'),color='#1f6fb4')
    pk=d.loc['2023Q2':'2024Q1','y'].idxmax()
    ax.axhline(0,color='black',lw=0.8); ax.set_xlim(*xlim)
    ax.set_xlabel(xlabel); ax.set_ylabel('CPI 欧米型コア（携帯電話通信料除く）前年比、%')
    ax.set_title(title,fontsize=13,loc='left'); ax.grid(alpha=0.3); ax.legend(loc='upper left',fontsize=8.5,frameon=False)

fig,ax=plt.subplots(figsize=(9,6.5))
list(panel(ax,'cons_DI','消費者レベルの需給バランス（短観 需給判断DI 3業種加重平均、%ポイント）','修正フィリップス曲線（2026年7-9月期まで延長）',(-40,0)) or [])
fig.text(0.01,0.005,'注：CPIは総合から食料（酒類除く）・エネルギー・通信料（携帯電話）を除いた試算値の四半期平均。2014年4-6月〜15年1-3月は消費税率引き上げの影響（1.5%pt）を控除。\n　　横軸は短観（全規模）の国内製商品・サービス需給判断DI「小売」「対個人サービス」「宿泊・飲食サービス」をCPIウエイトで加重平均。出所：総務省、日本銀行を基に作成\n　　「記事」：末廣徹「やっぱり日本は｢デフレ｣に戻るのかもしれない」東洋経済オンライン、2023年6月14日（https://toyokeizai.net/articles/-/678868）\n　　同記事の図を最新データで延長',fontsize=7.5,color='#555555')
plt.tight_layout(rect=(0,0.085,1,1)); plt.savefig('fig1_modified_phillips.png',dpi=150)

fig,ax=plt.subplots(figsize=(9,6.5))
list(panel(ax,'gap_lead2','日銀 需給ギャップ（2四半期先行、%）','日銀の需給ギャップと欧米型コアCPIで作成したフィリップス曲線（同）',(-3,2.5),lab_off=(115,-80)) or [])
fig.text(0.01,0.005,'注：CPIは図1と同じ。需給ギャップは日本銀行推計（最新公表値、2026年4-6月期まで）を2四半期先行させてCPIと対応。\n　　需給ギャップは推計の改定で過去値が記事執筆時点から変わっている点に注意。出所：総務省、日本銀行を基に作成\n　　「記事」：末廣徹「やっぱり日本は｢デフレ｣に戻るのかもしれない」東洋経済オンライン、2023年6月14日（https://toyokeizai.net/articles/-/678868）\n　　同記事の図を最新データで延長',fontsize=7.5,color='#555555')
plt.tight_layout(rect=(0,0.085,1,1)); plt.savefig('fig2_boj_gap_phillips.png',dpi=150)
