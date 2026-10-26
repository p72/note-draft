exec(open('/home/claude/work/load.py').read())
for d,src in [(r,'cr'),(n,'cn')]:
    d=d.copy(); d['date']=pd.PeriodIndex.from_fields(year=d.year,quarter=d.quarter,freq='Q')
    k[src]=d.set_index('date')['HouseholdConsumption']
k['cr_x']=None
print('nominal C check max diff:',(k.c-k.cn).abs().max())
k['P']=k.cn/k.cr
print('real Yd check:',(k.yd/k.P - k.yd_real).abs().max())
k['apc']=k.c/k.yd
L=np.log
d=pd.DataFrame(index=k.index)
d['dC_real']=100*(L(k.cr)-L(k.cr.shift(4)))
d['dYd_nom']=100*(L(k.yd)-L(k.yd.shift(4)))
d['dP']=100*(L(k.P)-L(k.P.shift(4)))
d['dYd_real']=d.dYd_nom-d.dP
d['dAPC']=100*(L(k.apc)-L(k.apc.shift(4)))
d['resid']=d.dC_real-(d.dYd_real+d.dAPC)
# Yd component contributions (share of yoy change, scaled to log change)
comp={'雇用者報酬':k.comp,'営業余剰・混合所得':k.op,'財産所得':k.prop,'社会給付':k.ben,'その他移転':k.oth,'税':-k.tax,'社会負担':-k.soc}
tot=k.yd-k.yd.shift(4)
for nm,s in comp.items(): d['c_'+nm]=(s-s.shift(4))/tot*d.dYd_nom
d['sr']=k.sr; d['apc']=100*k.apc
k.to_csv('/home/claude/work/levels.csv'); d.to_csv('/home/claude/work/decomp.csv')
print(d.dropna().resid.abs().max())
print(d.tail(10).round(2).T.to_string())
# period averages
d2=d.dropna().copy(); idx=d2.index.year
bins=[('1995-2007',1995,2007),('2008-2019',2008,2019),('2020-2021',2020,2021),('2022-2026H1',2022,2026)]
out=[]
for nm,a,b in bins:
    s=d2[(idx>=a)&(idx<=b)]
    out.append([nm]+s[['dC_real','dYd_nom','dP','dYd_real','dAPC']].mean().round(2).tolist())
pt=pd.DataFrame(out,columns=['期間','実質消費','名目可処分所得','消費デフレーター','実質可処分所得','消費性向']); print(pt.to_string())
pt.to_csv('/home/claude/work/period.csv',index=False)
# cumulative since 2021Q4
b=pd.Period('2021Q4','Q'); e=k.index[-1]
cum={x:100*(L(y[e])-L(y[b])) for x,y in [('実質消費',k.cr),('名目Yd',k.yd),('デフレーター',k.P),('実質Yd',k.yd/k.P),('APC',k.apc),('雇用者報酬名目',k.comp)]}
print('cum 2021Q4->',e,{a:round(v,2) for a,v in cum.items()})
print(k.loc['2019Q1':, ['sr']].T.round(1).to_string())
