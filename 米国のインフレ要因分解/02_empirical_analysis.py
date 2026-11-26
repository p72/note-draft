"""Reproducible diagnostics; unstable estimates are retained with explicit flags.
This does not replace the publication gate in 02_dupor_hogan_jp.py.
"""
import importlib.util
import json
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('dh', HERE/'02_dupor_hogan_jp.py')
dh = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dh)
OUT = HERE/'02_data'/'analysis'
DATES = ['2022-12','2023-04','2024-06','2025-01','2025-09','2026-09']
COLS = dh.COLS + ['current_unclear','past_unclear']


def unclear_path(y, info, out, lag, threshold):
    """Allocate both innovations and all propagation to a third shock group."""
    e = info['residual']; A = info['A']
    scale = e[:info['nfit']].std(axis=0, ddof=1)
    unclear = (np.abs(e) <= threshold*scale).any(axis=1) if threshold else np.zeros(len(e),bool)
    supply = e[:,0]*e[:,1] < 0
    masks = [~unclear & ~supply, ~unclear & supply, unclear]
    result = np.full((len(y),7), np.nan)
    result[lag:,0] = out[lag:,0]
    for group, mask in enumerate(masks):
        path = np.zeros_like(y)
        for t in range(lag,len(y)):
            current = e[t-lag] if mask[t-lag] else np.zeros(2)
            past = sum(A[j-1]@path[t-j] for j in range(1,lag+1))
            path[t] = current+past
            ci, pi = [(1,3),(2,4),(5,6)][group]
            result[t,ci] = current[0]; result[t,pi] = past[0]
    np.testing.assert_allclose(result[lag:].sum(axis=1),y[lag:,0],atol=1e-8)
    return result, unclear


def estimate(nominal, price, lag=12, seasonal=True, threshold=0, weights='geometric', fit_end=None):
    idx = nominal.index[1:]
    dp = 100*np.log(price).diff().iloc[1:]
    dq = 100*np.log(nominal/price).diff().iloc[1:]
    share = nominal.div(nominal.sum(axis=1),axis=0)
    w = (np.sqrt(share*share.shift(1)) if weights=='geometric' else share.rolling(12).mean().shift(1)).iloc[1:]
    components, matched, diagnostics, items = [], [], [], {}
    for cat in price.columns:
        y = np.column_stack([dp[cat],dq[cat]])
        base,rho,info = dh.decompose(y,lag,idx.month if seasonal else False,fit_end=fit_end,details=True)
        arr, unclear = unclear_path(y,info,base,lag,threshold)
        z = pd.DataFrame(arr,index=idx,columns=COLS).mul(w[cat],axis=0)
        components.append(z); items[cat]=z
        e=info['residual']; m=np.full((len(y),3),np.nan)
        sup=e[:,0]*e[:,1]<0
        for j, mask in enumerate([~sup & ~unclear,sup & ~unclear,unclear]):
            m[lag:,j]=y[lag:,0]*mask
        matched.append(pd.DataFrame(m,index=idx,columns=['shapiro_demand','shapiro_supply','shapiro_unclear']).mul(w[cat],axis=0))
        row=dict(category=cat,spectral_radius=rho,stable=rho<1,nfit=info['nfit'],regressors=info['rank'],unclear_fraction=float(unclear.mean()))
        for j,name in enumerate(['price','quantity']):
            a=e[:info['nfit'],j]; a=a-a.mean(); n=len(a)
            acf=np.array([np.dot(a[h:],a[:-h])/np.dot(a,a) for h in range(1,25)])
            # Descriptive portmanteau statistic; no VAR parameter correction/p-value claim.
            row[name+'_acf1']=acf[0]; row[name+'_acf12']=acf[11]
            row[name+'_Q24']=n*(n+2)*np.sum(acf**2/(n-np.arange(1,25)))
            if fit_end is not None:
                row[name+'_oos_rmse']=np.sqrt(np.mean(e[info['nfit']:,j]**2))
                actual=y[fit_end:,j]; naive=y[fit_end-12:-12,j]
                row[name+'_seasonal_naive_rmse']=np.sqrt(np.mean((actual-naive)**2))
        diagnostics.append(row)
    monthly=sum(components); sm=sum(matched)
    total=(w*dp).sum(axis=1,min_count=price.shape[1])
    good=monthly.notna().all(axis=1)
    error=float((monthly.sum(axis=1).loc[good]-total.loc[good]).abs().max())
    np.testing.assert_allclose(monthly.sum(axis=1).loc[good],total.loc[good],atol=1e-8)
    monthly['total']=total.where(good)
    annual=monthly.join(sm).rolling(12,min_periods=12).sum()
    annual['demand']=annual.current_demand+annual.past_demand
    annual['supply']=annual.current_supply+annual.past_supply
    annual['unclear']=annual.current_unclear+annual.past_unclear
    annual['excess']=annual.demand+annual.supply+annual.unclear
    return annual,pd.DataFrame(diagnostics),pd.concat(items,axis=1),error


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    nominal,price=dh.load_panel(HERE/'02_data'/'raw')
    variants=[]
    for lag in [3,6,12]:
        variants.append((f'lag{lag}',nominal,price,dict(lag=lag)))
    variants += [('no_seasonal',nominal,price,dict(seasonal=False)),
                 ('lagged_weights',nominal,price,dict(weights='lagged')),
                 ('pre2020_fit',nominal,price,dict(fit_end=int((nominal.index[1:]<pd.Period('2020-01')).sum())))]
    for cutoff in [.1,.15,.3]:
        for lag in [3,6,12]:
            variants.append((f'lag{lag}_unclear_{cutoff}',nominal,price,dict(lag=lag,threshold=cutoff)))
    for years in [5,10,15]:
        variants.append((f'last_{years}y',nominal.iloc[-12*years-1:],price.iloc[-12*years-1:],{}))
    results,diags,summaries=[],[],[]
    for name,n,p,options in variants:
        annual,diag,items,error=estimate(n,p,**options)
        annual['specification']=name;results.append(annual)
        diag['specification']=name;diags.append(diag)
        summaries.append(dict(specification=name,unstable=int((~diag.stable).sum()),max_radius=diag.spectral_radius.max(),max_additivity_error=error,start=str(n.index[0]),end=str(n.index[-1])))
        if name=='lag12':
            items.to_csv(OUT/'baseline_items_monthly.csv',float_format='%.10g')
        print(name,summaries[-1],flush=True)
    combined=pd.concat(results).rename_axis('period').reset_index()
    combined.to_csv(OUT/'sensitivity.csv',index=False,float_format='%.10g')
    pd.concat(diags).to_csv(OUT/'diagnostics.csv',index=False,float_format='%.10g')
    pd.DataFrame(summaries).to_csv(OUT/'specifications.csv',index=False)
    combined[combined.period.astype(str).isin(DATES)].to_csv(OUT/'six_dates.csv',index=False,float_format='%.10g')
    baseline=combined[combined.specification=='lag12'].set_index('period')
    old=pd.read_csv(HERE/'01_jp_decomp_12m.csv',index_col=0)
    old.index=pd.PeriodIndex(old.index,freq='M')
    baseline.join(old.add_prefix('published_')).to_csv(OUT/'published_comparison.csv',float_format='%.10g')
    print(baseline.loc[pd.PeriodIndex(DATES,freq='M'),['drift','demand','supply','total','shapiro_demand','shapiro_supply']].round(4))
    # A chart explicitly labelled diagnostic because baseline contains unstable VARs.
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(2,1,figsize=(11,8),sharex=True)
    for name in ['lag3','lag6','lag12']:
        z=combined[combined.specification==name].set_index('period').loc['2015-01':]
        for ax,col in zip(axes,['demand','supply']):
            ax.plot(z.index.to_timestamp(),z[col],label=name)
            ax.set_ylabel(col+' (12-month log pp)'); ax.axhline(0,color='gray',lw=.5);ax.legend()
    axes[0].set_title('Diagnostic estimates: lag12 includes 2 unstable category VARs')
    fig.tight_layout();fig.savefig(OUT/'lag_comparison.png',dpi=160);plt.close(fig)

if __name__=='__main__':
    main()
