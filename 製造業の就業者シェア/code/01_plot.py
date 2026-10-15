import sys; sys.path.insert(0,'/mnt/skills/plugins/estat-api')
from scripts.estat_api import read_stats_csv, setup_japanese_font
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
import pandas as pd
font=setup_japanese_font(); print('font',font)
def s(df,code):
    d=df[df.cat01_code==code].copy(); d['y']=d.time_name.str[:4].astype(int); return d.set_index('y')['value'].sort_index()
old=read_stats_csv('old.csv'); old10=read_stats_csv('old10.csv'); new=read_stats_csv('new.csv')
om=read_stats_csv('old_med.csv'); nm=read_stats_csv('new_med.csv')
tot_old=s(old,'000'); tot_new=s(new,'00')
m10=s(old10,'A009'); m11=s(old,'010'); m12=s(new,'10')
sh10=(m10/tot_old*100).dropna(); sh11=(m11/tot_old*100).dropna().loc[2003:2010]; sh12=(m12/tot_new*100).dropna()
med11=(s(om,'064')/tot_old*100).dropna().loc[2003:2010]; med12=(s(nm,'78')/tot_new*100).dropna()
ws12=(s(nm,'51')/tot_new*100).dropna()
out=pd.DataFrame({'製造業_第10回':m10,'製造業_第11回':m11,'製造業_第12-14回':m12,'全産業_旧表':tot_old,'全産業_新表':tot_new,
 'シェア_第10回':sh10,'シェア_第11回':sh11,'シェア_第12-14回':sh12,'医療福祉シェア_第11回':med11,'医療福祉シェア_第12-14回':med12})
out.round(2).to_csv('01_mfg_share.csv',encoding='utf-8-sig')
print(out[['製造業_第10回','製造業_第11回','製造業_第12-14回','シェア_第10回','シェア_第11回','シェア_第12-14回']].round(1).loc[[1953,1960,1965,1970,1973,1980,1985,1990,1992,1995,2000,2002,2003,2007,2009,2010,2012,2019,2025]])
fig,ax=plt.subplots(2,1,figsize=(11,9),sharex=True)
c='#1f4e79'
ax[0].plot(sh10.index,sh10,color=c,lw=2.2,label='製造業（第10回改定分類, 1953–2002）')
ax[0].plot(sh11.index,sh11,color=c,lw=2.2,ls='--',label='製造業（第11回改定, 2003–2010）')
ax[0].plot(sh12.index,sh12,color=c,lw=2.2,ls=':',marker='o',ms=3,label='製造業（第12〜14回改定, 2007–2025）')
ax[0].plot(med11.index,med11,color='#c00000',lw=1.8,ls='--',label='医療，福祉（第11回）')
ax[0].plot(med12.index,med12,color='#c00000',lw=1.8,ls=':',marker='o',ms=3,label='医療，福祉（第12〜14回）')
for y,v,t in [(sh10.idxmax(),sh10.max(),f'{sh10.idxmax()}年 ピーク {sh10.max():.1f}%'),(2025,sh12.loc[2025],f'2025年 {sh12.loc[2025]:.1f}%')]:
    ax[0].annotate(t,(y,v),xytext=(0,10),textcoords='offset points',ha='center',fontsize=10)
ax[0].set_ylim(7,29.5); ax[0].set_ylabel('就業者全体に占める割合（%）'); ax[0].set_title('製造業の就業者シェアの長期推移（年平均）'); ax[0].grid(alpha=.3); ax[0].legend(fontsize=8.5,loc='lower left')
ax[1].plot(m10.index,m10,color=c,lw=2.2,label='製造業 就業者数（第10回）')
ax[1].plot(m11.dropna().index,m11.dropna(),color=c,lw=2.2,ls='--',label='同（第11回）')
ax[1].plot(m12.index,m12,color=c,lw=2.2,ls=':',marker='o',ms=3,label='同（第12〜14回）')
ax[1].annotate(f'{m10.idxmax()}年 {m10.max():.0f}万人',(m10.idxmax(),m10.max()),xytext=(0,8),textcoords='offset points',ha='center',fontsize=10)
ax[1].set_ylim(680,1680); ax[1].set_ylabel('万人'); ax[1].set_title('製造業の就業者数'); ax[1].grid(alpha=.3); ax[1].legend(fontsize=8.5,loc='lower right')
fig.text(0.01,0.005,'資料：総務省統計局「労働力調査（基本集計）」e-Stat 表0002060057・0003007108より作成。産業分類改定で系列に段差あり。2011年は東日本大震災で全国値なし。',fontsize=8)
plt.tight_layout(rect=(0,0.02,1,1)); plt.savefig('../01_chart_share.png',dpi=150)
print('peak share',sh10.idxmax(),sh10.max(),'peak n',m10.idxmax(),m10.max())
print('med cross', med12.round(1).loc[[2007,2015,2019,2025]].to_dict(), 'ws', ws12.round(1).loc[[2007,2025]].to_dict())
