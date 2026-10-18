"""製造業の就業者数を共通年=100で比較。既存の人数CSVを使用する。
1992基準のイタリアはBLS旧系列のみ（2012年終了）。OECDとの接続は行わない。
実行: JAPANESE_FONT=/path/to/font.otf python code/03_employment_index.py
依存: pandas, matplotlib
"""
from pathlib import Path
import os
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.lines import Line2D
BASE = Path(__file__).resolve().parent
font = os.environ.get('JAPANESE_FONT')
if font:
    font_manager.fontManager.addfont(font)
    plt.rcParams['font.family'] = font_manager.FontProperties(fname=font).get_name()
else:
    available = {f.name for f in font_manager.fontManager.ttflist}
    match = next((n for n in ['Noto Sans CJK JP','IPAexGothic','IPAGothic','Hiragino Sans','Yu Gothic'] if n in available),None)
    if not match: raise RuntimeError('日本語フォントをインストールするか JAPANESE_FONT を指定してください。')
    plt.rcParams['font.family'] = match
plt.rcParams['axes.unicode_minus'] = False
jp = pd.read_csv(BASE/'01_mfg_share.csv',index_col=0)
segments = {k:jp[f'製造業_{k}'].dropna() for k in ['第10回','第11回','第12-14回']}
assert segments['第10回'].idxmax() == 1992

def read(series):
    df=pd.read_csv(BASE/'international_raw'/f'{series}.csv',na_values='.')
    years=pd.to_datetime(df.iloc[:,0]).dt.year
    assert years.is_unique
    return pd.Series(pd.to_numeric(df.iloc[:,1]).values,index=years).sort_index()

countries={'韓国':read('LFEAMNTTKRA647N'),'米国':read('LFEAMNTTUSA647N')}
colors={'日本':'#24548a','韓国':'#ca6b18','イタリア':'#148572','米国':'#9c4079'}
output=[]
for base in [1992,1998]:
    data={**countries,'イタリア':read('ITAEMFGNA')*1000 if base==1992 else read('LFEAMNTTITA647N')}
    fig,ax=plt.subplots(figsize=(12,7.4))
    for suffix,style in [('第10回','-'),('第11回','--'),('第12-14回',':')]:
        s=segments[suffix]
        if suffix=='第11回': s=s.loc[2003:2006]
        s=s.reindex(range(s.index.min(),s.index.max()+1))
        index=s/segments['第10回'].loc[base]*100
        ax.plot(index.index,index,color=colors['日本'],ls=style if base==1992 else '-',lw=2.8,label='日本' if suffix=='第10回' else '_nolegend_')
        output.extend({'基準年':base,'国':'日本','系列':suffix,'年':int(y),'就業者数_人':n*10000,'指数':index.loc[y]} for y,n in s.items())
    for name in ['韓国','イタリア','米国']:
        s=data[name].dropna().loc[:2025]
        assert s.loc[base]>0 and (s>=0).all()
        index=s/s.loc[base]*100
        assert index.loc[base]==100
        # BLSのイタリアは1993年に対象年齢変更。境界を線でつながない。
        pieces=[index.loc[:1992],index.loc[1993:]] if name=='イタリア' and base==1992 else [index]
        for i,piece in enumerate(pieces):
            ax.plot(piece.index,piece,color=colors[name],lw=2.3,label=name if i==0 else '_nolegend_')
        end=int(index.index[-1]); val=index.iloc[-1]
        yoffset=8 if name=='米国' and base==1998 else 0
        ax.annotate(f'{name} {val:.1f}（{end}）',(end,val),xytext=(7,yoffset),textcoords='offset points',fontsize=10,color=colors[name],va='center')
        output.extend({'基準年':base,'国':name,'系列':'BLS旧系列' if name=='イタリア' and base==1992 else 'OECD','年':int(y),'就業者数_人':n,'指数':index.loc[y]} for y,n in s.items())
        print(base,name,'base persons',s.loc[base],'end',end,round(val,2),'2024',round(index.get(2024,float('nan')),2))
    jp_last=segments['第12-14回'].loc[2025]/segments['第10回'].loc[base]*100
    ax.annotate(f'日本 {jp_last:.1f}（2025）',(2025,jp_last),xytext=(7,-6 if base==1998 else 0),textcoords='offset points',fontsize=10,color=colors['日本'],va='center')
    if base == 1998:
        totals = {name:read(f'LFEMTTTT{code}A647N') for name,code in [('韓国','KR'),('イタリア','IT'),('米国','US')]}
        totals['日本'] = pd.concat([jp['全産業_旧表'].loc[:2006], jp['全産業_新表'].loc[2007:]])*10000
        for name,s in totals.items():
            s=s.loc[1998:2025].reindex(range(1998,int(s.loc[1998:2025].last_valid_index())+1))
            index=s/s.loc[1998]*100
            assert index.loc[1998]==100
            ax.plot(index.index,index,color=colors[name],ls=':',lw=2.5)
            end=int(index.last_valid_index());val=index.loc[end]
            offset=-4 if name=='イタリア' else (4 if name=='米国' else 0)
            ax.annotate(f'{name} 全体 {val:.1f}（{end}）',(end,val),xytext=(7,offset),textcoords='offset points',fontsize=9.5,color=colors[name],va='center')
            output.extend({'基準年':base,'国':name,'系列':'全就業者','年':int(y),'就業者数_人':n,'指数':index.loc[y]} for y,n in s.items())
            print('total',name,end,round(val,2))
    start=1970 if base==1992 else 1998
    ax.set_xlim(start,2033);ax.set_ylim(45,125) if base==1992 else ax.set_ylim(60,160)
    ax.set_xticks([1970,1980,1990,1992,2000,2010,2020,2025] if base==1992 else [1998,2000,2005,2010,2015,2020,2025])
    ax.axhline(100,color='#777777',lw=.9,ls='--',alpha=.7)
    ax.axvline(base,color='#888888',lw=.8,ls=':')
    ax.scatter([base],[100],color='#444444',s=25,zorder=4)
    ax.set_ylabel(f'製造業就業者数の指数（各国の{base}年＝100）' if base==1992 else f'就業者数の指数（各国・各系列の{base}年＝100）')
    ax.set_title(('製造業で働く「人数」の推移\n' if base==1992 else '製造業と全就業者の人数推移\n')+('日本の人数ピーク・1992年を各国とも100に' if base==1992 else '補足：4か国の足元までを比較（1998年＝100）'),fontsize=16,pad=18)
    country_legend=ax.legend(loc='upper left' if base==1998 else 'upper right',ncol=4,frameon=False,fontsize=11)
    if base==1998:
        ax.add_artist(country_legend)
        ax.legend(handles=[Line2D([0],[0],color='#444',lw=2.5,label='製造業'),Line2D([0],[0],color='#444',lw=2.5,ls=':',label='全就業者')],loc='upper left',bbox_to_anchor=(0,.94),ncol=2,frameon=False,fontsize=10)
    ax.grid(axis='y',alpha=.18);ax.spines[['top','right']].set_visible(False)
    if base==1992:
        notes=['日本の基準値は1,569万人。各国自身の1992年の人数で指数化（シェアではない）。',
               'イタリアはBLS旧系列で2012年まで。1993年の対象年齢変更をまたぐ水準差は未調整。',
               '日本の分類変更は線種で区別し、2011年は欠測。他国も分類・調査変更に注意。',
               '資料：日本＝労働力調査、韓国・米国＝OECD（FRED）、イタリア＝BLS（FRED）。']
    else:
        notes=['実線＝製造業、点線＝全就業者。同じ国は同じ色。各系列自身の1998年の人数＝100。',
               '日本の製造業は分類境界で線を分け、2011年は欠測。国ごとの分類・調査変更は未調整。',
               '資料：日本＝労働力調査、海外＝OECD Infra-Annual Labor Statistics（FRED）。']
    for i,line in enumerate(notes):fig.text(.08,.115-i*.027,line,fontsize=9)
    fig.tight_layout(rect=(0,.16,1,1))
    fig.savefig(BASE.parent/f'03_chart_count_{base}.png',dpi=170)
    plt.close(fig)
pd.DataFrame(output).to_csv(BASE/'03_employment_index.csv',index=False,encoding='utf-8-sig',float_format='%.6f')
