"""Offline numerical/security checks; synthetic data are NOT empirical results."""
import importlib.util
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import numpy as np
import requests

spec = importlib.util.spec_from_file_location("dh", Path(__file__).with_name("02_dupor_hogan_jp.py"))
dh = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dh)

def check_ma():
    rng = np.random.default_rng(123)
    y = rng.normal(size=(180, 2))
    for t in range(2, len(y)):
        y[t] += [.2, .3] + np.array([[.35,.15],[-.1,.3]]) @ y[t-1] + .1*y[t-2]
    for lag in (1,3,6,12):
        for end in (None,120):
            out, _ = dh.decompose(y, lag, False, fit_end=end)
            X = np.column_stack([np.ones(len(y)-lag)] + [y[lag-j:len(y)-j] for j in range(1,lag+1)])
            nfit = len(X) if end is None else end-lag
            B = np.linalg.lstsq(X[:nfit],y[lag:lag+nfit],rcond=None)[0]
            A = [B[1+2*j:3+2*j].T for j in range(lag)]
            e = y[lag:]-X@B
            psi = [np.eye(2)]
            for h in range(1,len(e)):
                psi.append(sum(A[j-1]@psi[h-j] for j in range(1,min(h,lag)+1)))
            d = e.copy(); s = e.copy()
            supply = e[:,0]*e[:,1]<0
            d[supply]=0; s[~supply]=0
            past_d=np.zeros(len(e)); past_s=np.zeros(len(e))
            for t in range(len(e)):
                for h in range(1,t+1):
                    past_d[t]+=(psi[h]@d[t-h])[0]
                    past_s[t]+=(psi[h]@s[t-h])[0]
            np.testing.assert_allclose(out[lag:,1],d[:,0],atol=1e-10)
            np.testing.assert_allclose(out[lag:,2],s[:,0],atol=1e-10)
            np.testing.assert_allclose(out[lag:,3],past_d,atol=1e-10)
            np.testing.assert_allclose(out[lag:,4],past_s,atol=1e-10)
    print("PASS: independent MA convolution vs recursion, 4 lags x 2 fit periods")

def check_credentials():
    fake="TEST_CREDENTIAL_NOT_REAL"
    with patch.dict(os.environ, {"ESTAT_APP_ID":fake}):
        with patch.object(dh.requests,"get",side_effect=requests.ConnectionError("https://example.test?appId="+fake)):
            try:
                dh.get_table("example")
            except RuntimeError as e:
                import traceback
                assert fake not in "".join(traceback.format_exception(e))
            else:
                raise AssertionError("Expected sanitized failure")
    print("PASS: failed HTTP request does not disclose credential in traceback")

def check_panel():
    import pandas as pd
    idx=pd.period_range("2000-01","2026-09",freq="M")
    k=pd.DataFrame([dict(period=str(t),cat01_code=c,value=100.) for t in idx for c in dh.MAP]).set_index("period")
    p=pd.DataFrame([dict(period=str(t),cat01_code=c,value=100.) for t in idx for c in set(dh.MAP.values())]).set_index("period")
    with TemporaryDirectory() as temp:
        k.to_csv(Path(temp)/"kakei.csv"); p.to_csv(Path(temp)/"cpi.csv")
        n,pr=dh.load_panel(temp)
        assert n.shape==(321,45) and pr.shape==n.shape
        assert len(dh.MAP)==47
        k.iloc[:-1].to_csv(Path(temp)/"kakei.csv")
        try:
            dh.load_panel(temp)
        except ValueError as e:
            assert "Incomplete panel" in str(e)
        else:
            raise AssertionError("Missing observation accepted")
    print("PASS: CSV code preservation, 47-to-45 mapping and missing-data rejection")



def check_time_labels():
    # Fiscal-year code 2020100000 used to be misread as October.
    classes=[{'@code':'2020000101','@name':'2020年1月'},
             {'@code':'2020000000','@name':'2020年'},
             {'@code':'2020100000','@name':'2020年度'}]
    page={'CLASS_INF':{'CLASS_OBJ':[{'@id':'time','CLASS':classes},
          {'@id':'cat01','CLASS':{'@code':'0003','@name':'穀類'}}]},
          'DATA_INF':{'VALUE':[{'@time':c['@code'],'@cat01':'0003','$':str(i+1)} for i,c in enumerate(classes)]}}
    parsed=dh.parse_pages([page])
    assert len(parsed)==1 and str(parsed.index[0])=='2020-01' and parsed.iloc[0].value==1
    classes[0]['@name']='unknown'
    try:
        dh.parse_pages([page])
    except ValueError:
        pass
    else:
        raise AssertionError('Unknown time label accepted')
    print('PASS: monthly labels only; annual and fiscal rows excluded')


def check_unclear_ma():
    spec = importlib.util.spec_from_file_location('emp',Path(__file__).with_name('02_empirical_analysis.py'))
    emp = importlib.util.module_from_spec(spec);spec.loader.exec_module(emp)
    rng=np.random.default_rng(918)
    y=rng.normal(size=(110,2))
    for t in range(1,len(y)):
        y[t]+=.3*y[t-1]
    out,_,info=dh.decompose(y,3,False,details=True)
    result,mask=emp.unclear_path(y,info,out,3,.3)
    e=info['residual'].copy(); e[~mask]=0
    psi=[np.eye(2)]
    for h in range(1,len(e)):
        psi.append(sum(info['A'][j-1]@psi[h-j] for j in range(1,min(h,3)+1)))
    for t in range(len(e)):
        expected=sum((psi[h]@e[t-h])[0] for h in range(t+1))
        np.testing.assert_allclose(result[t+3,5:7].sum(),expected,atol=1e-10)
    zero,_=emp.unclear_path(y,info,out,3,0)
    np.testing.assert_allclose(zero[:,:5],out,atol=1e-10)
    assert mask.any() and (~mask).any()
    print('PASS: unclear innovations retain independent MA propagation; zero threshold recovers baseline')

if __name__=='__main__':
    check_ma()
    check_credentials()
    check_panel()
    check_time_labels()
    check_unclear_ma()
