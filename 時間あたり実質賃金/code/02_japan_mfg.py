import sys, pandas as pd, numpy as np, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
sys.path.insert(0,'/mnt/skills/plugins/oecd-data'); from scripts.jp_font import setup_japanese_font
setup_japanese_font()
def yoy(fn):
    d=pd.read_excel(fn,'E',header=None,engine='xlrd').iloc[93:]
    d=d[pd.to_numeric(d[0],errors='coerce').notna()]; d.index=d[0].astype(int)
    return pd.to_numeric(d[1],errors='coerce'), pd.to_numeric(d[2],errors='coerce')
(nA,nH),(hA,hH),(rA,rH)=yoy('nom.bin'),yoy('hrs.bin'),yoy('real.bin')
yrs=range(1994,2026)
def chain(g):
    s=pd.Series(100.0,index=yrs)
    for y in yrs[1:]: s[y]=s[y-1]*(1+g[y]/100)
    return s
nom,hrs,real=chain(nA),chain(hA),chain(rA)
df=pd.DataFrame({'nom_h':nom/hrs*100,'real_m':real,'hrs':hrs,'real_h':real/hrs*100})
df['yoy']=df.real_h.pct_change()*100
ref=df.loc[2025,'real_h']*(1+rH[2026]/100)/(1+hH[2026]/100); ref_yoy=(ref/df.loc[2025,'real_h']-1)*100
print(df.round(1).to_string()); print('2026H1 ref',round(ref,1),round(ref_yoy,2), 'nomH1',nH[2026],'hrsH1',hH[2026],'realH1',rH[2026])
df.round(2).to_csv('jpn_mfg_result.csv')
fig,(a,b)=plt.subplots(2,1,figsize=(11,8.2),gridspec_kw={'height_ratios':[2.3,1]},sharex=True)
X=list(yrs)
a.plot(X,df.nom_h,color='gray',ls='--',lw=1.6,label='1時間あたり名目賃金')
a.plot(X,df.real_m,color='#E8692E',lw=2,label='1人あたり実質賃金（月額）')
a.plot(X,df.hrs,color='#1FA67A',lw=1.6,label='総実労働時間（1人あたり）')
a.plot(X,df.real_h,color='#2878D6',lw=3,label='1時間あたり実質賃金')
a.plot([2025,2026],[df.real_h[2025],ref],color='#2878D6',ls=':',lw=2)
a.plot([2026],[ref],'o',mfc='white',mec='#2878D6',mew=2.5,ms=9,label='2026年1-6月（参考値）')
a.annotate(f'{ref:.1f}',(2026,ref),xytext=(8,0),textcoords='offset points',va='center',fontsize=10)
offs={'nom_h':0,'real_h':0,'real_m':6,'hrs':-6}
for c in ['nom_h','real_h','real_m','hrs']:
    v=df.loc[2025,c]; a.annotate(f'{v:.1f}',(2025,v),xytext=(8,offs[c]),textcoords='offset points',va='center',fontsize=10)
a.axhline(100,color='#aaa',lw=1)
a.set_ylabel('1994年＝100'); a.set_title('日本：1人1時間あたり実質賃金の推移（製造業, 1994年＝100）',loc='left',fontsize=15)
a.legend(loc='lower left',frameon=False,fontsize=10,ncol=2); a.grid(axis='y',color='#e5e5e5'); a.spines[['top','right']].set_visible(False)
yy=df.yoy.loc[1995:]; b.bar(yy.index,yy.values,color=['#2878D6' if v>=0 else '#E04848' for v in yy],width=0.7)
b.bar([2026],[ref_yoy],width=0.7,color='white',edgecolor='#2878D6' if ref_yoy>=0 else '#E04848',hatch='///')
b.axhline(0,color='#555',lw=1); b.set_title('1時間あたり実質賃金の前年比',loc='left'); b.set_ylabel('前年比（%）')
b.grid(axis='y',color='#e5e5e5'); b.spines[['top','right']].set_visible(False)
b.set_xticks(range(1994,2027,2)); plt.setp(b.get_xticklabels(),rotation=45)
fig.text(0.01,0.005,'出所：厚生労働省「毎月勤労統計調査」長期時系列表（事業所規模5人以上・製造業・就業形態計）。実質化は消費者物価指数（持家の帰属家賃を除く総合）。\n'
 '公表前年比を連鎖して指数化（サンプル入替による指数水準の段差を回避）。時給＝現金給与総額÷総実労働時間。2026年は1-6月の前年同期比を2025年値に適用した参考値。',fontsize=8,color='#555')
plt.tight_layout(rect=(0,0.04,1,1)); plt.savefig('japan_mfg_real_hourly_wage.png',dpi=150)
