"""Official-index comparison and independent rerun of the unchanged 01 script."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import numpy as np
import pandas as pd
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('dh',HERE/'02_dupor_hogan_jp.py')
dh=importlib.util.module_from_spec(spec);spec.loader.exec_module(dh)
OUT=HERE/'02_data'/'analysis'

def main():
    nominal,price=dh.load_panel(HERE/'02_data'/'raw')
    # Verify the archived acquisition files as well as the normalized CSV input.
    audit={}
    for table,sub,name in [('0004023601','raw','kakei'),('0003427113','raw','cpi'),
                           ('0003427113','official','official'),('0004023601','coverage','consumption')]:
        raw=dh.load_saved_table(HERE/'02_data'/sub,table)
        normalized=pd.read_csv(HERE/'02_data'/sub/(name+'.csv'),index_col=0,dtype={'cat01_code':str})
        normalized.index=pd.PeriodIndex(normalized.index,freq='M')
        pd.testing.assert_frame_equal(raw[['cat01_code','value']],normalized[['cat01_code','value']],check_names=False)
        audit[name]=dict(monthly_rows=len(raw),start=str(raw.index.min()),end=str(raw.index.max()))
    official=pd.read_csv(HERE/'02_data'/'official'/'official.csv',index_col=0,dtype={'cat01_code':str})
    official.index=pd.PeriodIndex(official.index,freq='M')
    op=official.pivot(columns='cat01_code',values='value')
    coverage=pd.read_csv(HERE/'02_data'/'coverage'/'consumption.csv',index_col=0)
    coverage.index=pd.PeriodIndex(coverage.index,freq='M')
    base=pd.read_csv(OUT/'sensitivity.csv');base=base[base.specification=='lag12'].set_index('period')
    base.index=pd.PeriodIndex(base.index,freq='M')
    comp=base[['total']].copy()
    for cat in ['0001','0163']:
        comp['official_log_'+cat]=100*np.log(op[cat]).diff(12)
        comp['official_pct_'+cat]=100*op[cat].pct_change(12,fill_method=None)
        comp['gap_log_'+cat]=comp.total-comp['official_log_'+cat]
    comp['household_spending_coverage']=nominal.sum(axis=1)/coverage.value.reindex(nominal.index)
    comp.to_csv(OUT/'official_comparison.csv',float_format='%.10g')
    # Mapping names are part of the audit, not inferred from numeric codes.
    k=pd.read_csv(HERE/'02_data'/'raw'/'kakei.csv',dtype={'cat01_code':str})
    c=pd.read_csv(HERE/'02_data'/'raw'/'cpi.csv',dtype={'cat01_code':str})
    m=pd.DataFrame(list(dh.MAP.items()),columns=['kakei_code','cpi_code'])
    for source,prefix in [(k,'kakei'),(c,'cpi')]:
        names=source.drop_duplicates('cat01_code').set_index('cat01_code').cat01_name
        m[prefix+'_name']=m[prefix+'_code'].map(names)
    m.to_csv(HERE/'02_data'/'processed'/'mapping.csv',index=False)
    with TemporaryDirectory() as tmp:
        folder=Path(tmp);(folder/'data').mkdir()
        for name,target in [('kakei','kakei_0004023601'),('cpi','cpi_idx')]:
            f=pd.read_csv(HERE/'02_data'/'raw'/(name+'.csv'),index_col=0,dtype={'cat01_code':str})
            f.index=pd.PeriodIndex(f.index,freq='M');f.to_pickle(folder/'data'/(target+'.pkl'))
        subprocess.run([sys.executable,str(HERE/'01_shapiro_jp.py')],cwd=folder,check=True,stdout=subprocess.DEVNULL)
        old=pd.read_pickle(folder/'data'/'result.pkl')['out'].rolling(12).sum()
    published=pd.read_csv(HERE/'01_jp_decomp_12m.csv',index_col=0)
    published.index=pd.PeriodIndex(published.index,freq='M')
    delta=old.reindex(published.index)[published.columns]-published
    delta.to_csv(OUT/'shapiro_reproduction_error.csv',float_format='%.10g')
    old.to_csv(OUT/'shapiro_reproduced.csv',float_format='%.10g')
    audit['shapiro_max_abs_error_vs_rounded_csv']=float(delta.abs().max().max())
    assert audit['shapiro_max_abs_error_vs_rounded_csv']<=.000501
    z=comp.loc['2015-01':].dropna()
    audit['official_since_2015']={cat:dict(correlation=float(z.total.corr(z['official_log_'+cat])),mean_gap_log_pp=float(z['gap_log_'+cat].mean()),rmse_log_pp=float(np.sqrt(np.mean(z['gap_log_'+cat]**2)))) for cat in ['0001','0163']}
    audit['household_spending_coverage']=dict(min=float(comp.household_spending_coverage.min()),max=float(comp.household_spending_coverage.max()),mean=float(comp.household_spending_coverage.mean()))
    (OUT/'observed_validation.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(audit,ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
