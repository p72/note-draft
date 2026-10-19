import sys, json, pandas as pd, numpy as np, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt, matplotlib.ticker
sys.path.insert(0,'/mnt/skills/plugins/oecd-data'); from scripts.jp_font import setup_japanese_font
font=setup_japanese_font(); print(font)
def fr(s):
    d=pd.DataFrame(json.load(open(f'{s}.json'))['observations']); d['v']=pd.to_numeric(d.value,errors='coerce'); d['y']=d.date.str[:4].astype(int)
    d['q']=d.date.str[5:7]; g=d.groupby('y').v; r=g.mean()[g.count()==4]
    p=d[d.q.isin(['01','04','07'])].groupby('y').v.mean(); r[2023]=r[2022]*p[2023]/p[2022]; return r
mon=fr('LCEAMN03KRQ661S'); hrs=fr('HOHWMN03KRQ661N')
ear=pd.read_csv('hou_ear.csv').set_index('TIME_PERIOD').OBS_VALUE.sort_index()   # = monthly earnings index (mfg)
cpi=pd.read_csv('cpi.csv').set_index('TIME_PERIOD').OBS_VALUE.sort_index()
hw=pd.read_csv('hours.csv'); hw=hw[hw.WORKER_STATUS=='_T'].set_index('TIME_PERIOD').OBS_VALUE.sort_index()
yrs=range(1994,2026)
# monthly earnings: MEI to 2023, extend with HOU_EAR growth
m=mon.reindex(yrs).copy()
for y in [2024,2025]: m[y]=m[y-1]*ear[y]/ear[y-1]
h=hrs.reindex(yrs).copy()
for y in [2024,2025]: h[y]=h[y-1]*hw[y]/hw[y-1]
df=pd.DataFrame({'nom_m':m,'hrs':h,'cpi':cpi.reindex(yrs)})
df['nom_h']=df.nom_m/df.hrs; df['real_m']=df.nom_m/df.cpi; df['real_h']=df.nom_h/df.cpi
idx=df/df.loc[1994]*100
idx['yoy']=df.real_h.pct_change()*100
idx.round(2).to_csv('kor_result.csv'); print(idx.round(1).to_string())
fig,(a,b)=plt.subplots(2,1,figsize=(11,8.2),gridspec_kw={'height_ratios':[2.3,1]},sharex=True)
X=list(yrs); core=[y for y in X if y<=2023]; ext=[2023,2024,2025]
def line(col,**k):
    a.plot(core,idx.loc[core,col],**k); k2=dict(k); k2.pop('label',None); k2['ls']=':'; a.plot(ext,idx.loc[ext,col],**k2)
line('nom_h',color='gray',ls='--',lw=1.6,label='1時間あたり名目賃金')
line('real_m',color='#E8692E',lw=2,label='1人あたり実質賃金（月額）')
line('hrs',color='#1FA67A',lw=1.6,label='総実労働時間（1人あたり）')
line('real_h',color='#2878D6',lw=3,label='1時間あたり実質賃金')
for col in ['nom_h','real_h','real_m','hrs']:
    v=idx.loc[2025,col]; a.annotate(f'{v:.1f}',(2025,v),xytext=(6,0),textcoords='offset points',va='center',fontsize=10)
v=idx.loc[2023,'real_h']; a.annotate(f'2023: {v:.1f}',(2023,v),xytext=(-10,14),textcoords='offset points',ha='right',fontsize=9,color='#2878D6')
a.axhline(100,color='#aaa',lw=1); a.axvspan(2023,2025.6,color='#f2f2f2',zorder=0)
a.text(2024.3,a.get_ylim()[1]*0.02 if False else 95,'延長\n(参考)',ha='center',fontsize=9,color='#777')
a.set_yscale('log'); a.set_yticks([80,100,150,200,250,300,400,600]); a.set_yticklabels(['80','100','150','200','250','300','400','600']); a.yaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
a.set_ylabel('1994年＝100（対数目盛）'); a.set_title('韓国：1人1時間あたり実質賃金の推移（製造業, 1994年＝100）',loc='left',fontsize=15)
a.legend(loc='upper left',frameon=False,fontsize=10); a.grid(axis='y',color='#e5e5e5'); a.spines[['top','right']].set_visible(False)
yy=idx.yoy.loc[1995:]; cols=['#2878D6' if v>=0 else '#E04848' for v in yy]
bars=b.bar(yy.index,yy.values,color=cols,width=0.7)
for y in [2024,2025]: bars[y-1995].set_hatch('///'); bars[y-1995].set_facecolor('white'); bars[y-1995].set_edgecolor(cols[y-1995])
b.axhline(0,color='#555',lw=1); b.set_title('1時間あたり実質賃金の前年比',loc='left'); b.set_ylabel('前年比（%）')
b.grid(axis='y',color='#e5e5e5'); b.spines[['top','right']].set_visible(False)
b.set_xticks(range(1994,2026,2)); plt.setp(b.get_xticklabels(),rotation=45)
fig.text(0.01,0.005,'出所：OECD Main Economic Indicators（韓国 雇用労働部「事業体労働力調査」ベース：製造業 月平均賃金・月労働時間, FRED経由）、OECD CPI（総合）。時給＝月額賃金÷月労働時間。\n'
 '2024-25年（点線・斜線）は参考値：月額賃金はOECD製造業賃金指数(DF_HOU_EAR)、労働時間はOECD年間実労働時間(全就業者)の前年比で延長。',fontsize=8,color='#555')
plt.tight_layout(rect=(0,0.04,1,1)); plt.savefig('korea_real_hourly_wage.png',dpi=150)
