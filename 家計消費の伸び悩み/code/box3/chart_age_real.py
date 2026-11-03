import pandas as pd, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib import font_manager
for n in ['Noto Sans CJK JP','Noto Sans JP','IPAexGothic','Hiragino Sans','Yu Gothic','Meiryo']:
    if any(f.name==n for f in font_manager.fontManager.ttflist): plt.rcParams['font.family']=n; break
d=pd.read_csv('age_real_idx.csv',index_col=0); x=range(len(d))
st={'平均':dict(color='#1F2A5C',lw=3.5),'39歳以下':dict(color='#45A5E0',lw=1.5),'40～49歳':dict(color='#3060B0',lw=1.5,ls='--'),
    '50～59歳':dict(color='#1F2A5C',lw=1.5,marker='o',mfc='white',ms=6),'60～69歳':dict(color='#2BA89A',lw=3.5),'70歳以上':dict(color='#45A5E0',lw=1.5,ls='--',marker='D',mfc='black',mec='black',ms=5)}
fig,ax=plt.subplots(figsize=(10,7))
for k,s in st.items(): ax.plot(x,d[k],label=k,**s)
ax.axhline(100,color='black',lw=1.2); ax.set_ylim(85,120)
ax.set_xticks([i for i,p in enumerate(d.index) if p.endswith('Q1')]); ax.set_xticklabels([("21年" if p.startswith('2021') else p[2:4]) for p in d.index if p.endswith('Q1')],fontsize=12)
ax.legend(ncol=3,fontsize=12,loc='lower left',frameon=False)
ax.set_title('年齢階級別の実質消費（家計調査、二人以上の世帯）\n（季節調整済、2021/1Q＝100）',fontsize=14)
fig.text(.02,.01,'（出所）総務省「家計調査」（二人以上の世帯、世帯主の年齢階級別、月次）、「消費者物価指数」より作成\n（注）1. 消費支出÷世帯人員＝1人当たり。世帯主年齢の5歳階級別の単純平均（34歳以下は1区分）。\n　　 2. CPI（持家の帰属家賃を除く総合）で実質化し、四半期平均をSTLで季節調整。2026/3Qは7〜8月。',fontsize=9)
plt.tight_layout(rect=(0,.08,1,1)); plt.savefig('02_chart_age_kakei.png',dpi=130)
