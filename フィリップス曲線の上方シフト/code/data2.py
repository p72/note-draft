import pandas as pd, numpy as np, io
b=open('dl/wage.bin','rb').read()
v=pd.read_excel(io.BytesIO(b),sheet_name='TL',header=None,engine='xlrd')
blk=v.iloc[94:169]
rows=[]
for _,r in blk.iterrows():
    try: yr=int(str(r[0])[:4])
    except: continue
    for qi in range(4):
        val=pd.to_numeric(r[4+qi],errors='coerce')
        if np.isnan(val):  # monthly fallback
            ms=pd.to_numeric(pd.Series([r[8+qi*3+k] for k in range(3)]),errors='coerce').dropna()
            val=ms.mean() if len(ms)>=2 else np.nan
        rows.append((pd.Period(f'{yr}Q{qi+1}'),val))
w=pd.Series(dict(rows),name='wage').dropna()
im=pd.read_csv('import.csv',index_col=0,parse_dates=True)['import_yoy']; im.index=im.index.to_period('M')
imq=im.groupby(im.index.asfreq('Q')).mean()
ex=pd.read_csv('exp.csv',index_col=0,parse_dates=True)['exp1y']; ex.index=ex.index.to_period('Q')
d=pd.read_csv('panel.csv',index_col=0); d.index=pd.PeriodIndex(d.index,freq='Q')
d=d.join(w).join(imq.rename('imp')).join(ex)
d['wage_l1']=d.wage.shift(1)
d['imp_l24']=d.imp.shift(2).rolling(3).mean()   # t-2..t-4
d['exp_l1']=d.exp1y.shift(1)
q=d.index
d['D_tax14']=((q>=pd.Period('2014Q2'))&(q<=pd.Period('2015Q1'))).astype(int)
d['D_tax19']=((q>=pd.Period('2019Q4'))&(q<=pd.Period('2020Q3'))).astype(int)
d['D_covid']=((q>=pd.Period('2020Q2'))&(q<=pd.Period('2021Q4'))).astype(int)
d['D_shift']=(q>=pd.Period('2022Q2')).astype(int)
d.to_csv('panel2.csv')
print(d[['core_exmob','cons_DI','wage','imp','exp1y']].loc['2021Q4':].round(2).to_string())
print(d[['wage']].loc['2004Q1':'2005Q1'].T)
