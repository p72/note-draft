"""Dupor-Hogan (2025), eqs. (1)-(2), Japan adaptation.
Run from any directory: python 02_dupor_hogan_jp.py --self-test
For empirical analysis: set ESTAT_APP_ID and run without arguments.
Optional --input-dir points to existing trusted pickles from 01_shapiro_jp.py.
No API credential is stored in source or output.
"""
import argparse
import os
import json
import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd
import requests

MAP = {  # 家計調査コード: CPIコード
 '010100000':'0003','010200000':'0008','010300000':'0013','010400000':'0016','010500000':'0021',
 '010600000':'0027','010700000':'0030','010800000':'0033','010900000':'0034','011000000':'0037',
 '011100000':'0041','011200000':'0042','020100000':'0165','020200000':'0051','030100000':'0056',
 '030200000':'0057','030300000':'0058','030400001':'0059','040100000':'0061','040200000':'0066',
 '040300000':'0070','040400000':'0073','040500000':'0077','040600000':'0081','050100000':'0084',
 '050200000':'0085','050300000':'0090','050400000':'0094','050500000':'0103','050600000':'0103',
 '050700000':'0098','050800000':'0106','060100000':'0108','060200001':'0108','060300000':'0109',
 '060400000':'0110','070100000':'0112','070200000':'0113','070300000':'0117','080100000':'0119',
 '080200000':'0120','080300000':'0121','090100000':'0123','090200000':'0128','090300000':'0134',
 '090400000':'0138','100100000':'0145'}

HERE = Path(__file__).resolve().parent
COLS = ["drift", "current_demand", "current_supply", "past_demand", "past_supply"]

def get_table(table, raw_dir=None, **filters):
    app_id = os.environ.get("ESTAT_APP_ID", "").strip()
    if not app_id:
        raise RuntimeError("Set the ESTAT_APP_ID environment variable before downloading")
    if raw_dir is not None and list(Path(raw_dir).glob(f"{table}_*.json")):
        raise ValueError("Raw table archive already exists; use a new directory")
    endpoint = "https://api.e-stat.go.jp/rest/3.0/app/json/getStatsData"
    pages = []
    start = 1
    while True:
        # requests exceptions can contain the credential-bearing request URL.
        try:
            r = requests.get(endpoint, params=dict(appId=app_id, statsDataId=table,
                             limit=10000, startPosition=start, **filters), timeout=120)
            r.raise_for_status()
            obj = r.json()["GET_STATS_DATA"]
        except (requests.RequestException, ValueError, KeyError):
            raise RuntimeError(f"e-Stat request failed: table={table}, start={start}; URL redacted") from None
        if int(obj["RESULT"]["STATUS"]) != 0:
            raise RuntimeError(f"e-Stat status={obj['RESULT']['STATUS']}: table={table}")
        data = obj["STATISTICAL_DATA"]
        if raw_dir is not None:
            dest = Path(raw_dir)
            dest.mkdir(parents=True, exist_ok=True)
            # Preserve statistical data and metadata, not request parameters.
            payload = json.dumps(data, ensure_ascii=False, sort_keys=True).replace(app_id, "[REDACTED]").encode("utf-8")
            name = f"{table}_{start}.json"
            (dest/name).write_bytes(payload)
            record = dict(table=table, start=start, filters=filters, file=name,
                          retrieved_at=datetime.now(timezone.utc).isoformat(),
                          sha256=hashlib.sha256(payload).hexdigest())
            with (dest/"manifest.jsonl").open("a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False)+"\n")
        pages.append(data)
        nxt = data["RESULT_INF"].get("NEXT_KEY")
        if nxt is None:
            break
        start = int(nxt)
    return parse_pages(pages)


def parse_pages(pages):
    """Use published time labels, excluding annual/fiscal averages explicitly."""
    values, months, names = [], {}, {}
    for data in pages:
        v = data["DATA_INF"]["VALUE"]
        values.extend(v if isinstance(v, list) else [v])
        for obj in data["CLASS_INF"]["CLASS_OBJ"]:
            classes = obj["CLASS"]
            classes = classes if isinstance(classes, list) else [classes]
            if obj["@id"] == "time":
                for c in classes:
                    match = re.fullmatch(r"(\d{4})年(\d{1,2})月", c["@name"])
                    if match:
                        year, month = map(int, match.groups())
                        months[c["@code"]] = pd.Period(year=year, month=month, freq="M")
                    elif not re.fullmatch(r"\d{4}年(?:度)?", c["@name"]):
                        raise ValueError("Unrecognized time label: " + c["@name"])
            if obj["@id"] == "cat01":
                names.update({c["@code"]: c["@name"] for c in classes})
    df = pd.DataFrame(values)
    df = df[df["@time"].isin(months)].copy()
    if df.empty:
        raise ValueError("No monthly observations")
    df["value"] = pd.to_numeric(df["$"], errors="coerce")
    df.index = pd.PeriodIndex(df["@time"].map(months), freq="M")
    df.index.name = "period"
    df["cat01_code"] = df["@cat01"].astype(str)
    df["cat01_name"] = df["cat01_code"].map(names)
    return df


def load_saved_table(folder, table):
    """Verify archived page hashes and contiguous pagination before parsing."""
    folder = Path(folder)
    records = [json.loads(line) for line in (folder/"manifest.jsonl").read_text().splitlines()]
    records = sorted((r for r in records if r["table"] == table), key=lambda r: r["start"])
    pages, expected = [], 1
    for r in records:
        payload = (folder/r["file"]).read_bytes()
        if hashlib.sha256(payload).hexdigest() != r["sha256"] or r["start"] != expected:
            raise ValueError("Archive hash/pagination mismatch")
        page = json.loads(payload)
        pages.append(page)
        expected = page["RESULT_INF"].get("NEXT_KEY")
        expected = int(expected) if expected is not None else None
    if not pages or expected is not None:
        raise ValueError("Incomplete archive")
    return parse_pages(pages)

def load_panel(input_dir=None, raw_dir=None):
    if input_dir:
        folder = Path(input_dir)
        if (folder / "kakei.csv").exists() and (folder / "cpi.csv").exists():
            k = pd.read_csv(folder/"kakei.csv", index_col=0, dtype={"cat01_code":str})
            c = pd.read_csv(folder/"cpi.csv", index_col=0, dtype={"cat01_code":str})
        elif (folder / "manifest.jsonl").exists():
            k = load_saved_table(folder, "0004023601")
            c = load_saved_table(folder, "0003427113")
            k.to_csv(folder/"kakei.csv")
            c.to_csv(folder/"cpi.csv")
        else:
            k = pd.read_pickle(folder / "kakei_0004023601.pkl")
            c = pd.read_pickle(folder / "cpi_idx.pkl")
    else:
        k = get_table("0004023601", raw_dir=raw_dir, cdCat02="03", cdArea="00000",
                      cdCat01=",".join(MAP))
        c = get_table("0003427113", raw_dir=raw_dir, cdTab="1", cdArea="00000",
                      cdCat01=",".join(sorted(set(MAP.values()))))
        if raw_dir is not None:
            k.to_csv(Path(raw_dir)/"kakei.csv")
            c.to_csv(Path(raw_dir)/"cpi.csv")
    k = k.copy()
    c = c.copy()
    k.index = pd.PeriodIndex(k.index, freq="M")
    c.index = pd.PeriodIndex(c.index, freq="M")
    k["cat01_code"] = k["cat01_code"].astype(str).str.zfill(9)
    c["cat01_code"] = c["cat01_code"].astype(str).str.zfill(4)
    k = k[k.cat01_code.isin(MAP)]
    c = c[c.cat01_code.isin(MAP.values())]
    if k.assign(period=k.index).duplicated(["period","cat01_code"]).any():
        raise ValueError("Duplicate family survey observations; check API dimensions")
    if c.assign(period=c.index).duplicated(["period","cat01_code"]).any():
        raise ValueError("Duplicate CPI observations; check API dimensions")
    k["cpi"] = k.cat01_code.map(MAP)
    nominal = k.groupby([k.index,"cpi"]).value.sum(min_count=1).unstack()
    # A combined category is missing if any constituent is missing.
    count = k.groupby([k.index,"cpi"]).value.count().unstack()
    expected = pd.Series(list(MAP.values())).value_counts()
    nominal = nominal.where(count.eq(expected, axis=1))
    price = c.pivot(columns="cat01_code",values="value")
    cats = sorted(set(MAP.values()))
    idx = pd.period_range("2000-01","2026-09",freq="M")
    nominal = nominal.reindex(index=idx, columns=cats)
    price = price.reindex(index=idx, columns=cats)
    if nominal.isna().any().any() or price.isna().any().any():
        raise ValueError("Incomplete panel: "+str(pd.concat({"nominal":nominal.isna().sum(),"price":price.isna().sum()},axis=1).query("nominal > 0 or price > 0")))
    if (nominal<=0).any().any() or (price<=0).any().any():
        raise ValueError("Nonpositive price or spending")
    return nominal, price

def decompose(y, lag=12, seasonal=True, tax=None, fit_end=None, details=False):
    """OLS fixed-sample VAR. Drift includes deterministic path and initial history.
    Recursion is exactly equivalent to the finite-sample MA representation.
    Tax dummies (if enabled) are deterministic controls, not structural shocks.
    """
    y = np.asarray(y, dtype=float)
    T, n = y.shape
    if n != 2 or not np.isfinite(y).all():
        raise ValueError("Expected complete two-variable panel")
    if seasonal is True:
        raise ValueError("Pass calendar month array or False")
    z = np.ones((T,1))
    if seasonal is not False:
        z = np.column_stack([z, np.asarray(seasonal)[:,None] == np.arange(2,13)])
    if tax is not None:
        z = np.column_stack([z,tax])
    X = np.column_stack([z[lag:]]+[y[lag-j:T-j] for j in range(1,lag+1)])
    fit = np.arange(T-lag) < (T-lag if fit_end is None else fit_end-lag)
    keep = np.any(X[fit]!=0,axis=0)
    if not np.all(keep[z.shape[1]:]):
        raise ValueError("Degenerate endogenous regressor")
    B = np.zeros((X.shape[1],2))
    B[keep] = np.linalg.lstsq(X[fit][:,keep],y[lag:][fit],rcond=None)[0]
    if np.linalg.matrix_rank(X[fit][:,keep]) != keep.sum():
        raise ValueError("Rank-deficient VAR")
    A = np.array([B[z.shape[1]+2*j:z.shape[1]+2*j+2].T for j in range(lag)])
    comp = np.zeros((2*lag,2*lag))
    comp[:2,:] = np.concatenate(A,axis=1)
    comp[2:,:-2] = np.eye(2*(lag-1))
    rho = np.max(np.abs(np.linalg.eigvals(comp)))
    residual = y[lag:]-X@B
    d = np.zeros_like(y); s = np.zeros_like(y); drift = np.zeros_like(y)
    drift[:lag] = y[:lag]
    out = np.full((T,5),np.nan)
    for t in range(lag,T):
        e = residual[t-lag]
        supply = e[0]*e[1]<0
        cd = np.zeros(2) if supply else e
        cs = e if supply else np.zeros(2)
        pd_ = sum(A[j-1]@d[t-j] for j in range(1,lag+1))
        ps_ = sum(A[j-1]@s[t-j] for j in range(1,lag+1))
        drift[t] = z[t]@B[:z.shape[1]]+sum(A[j-1]@drift[t-j] for j in range(1,lag+1))
        d[t] = cd+pd_; s[t] = cs+ps_
        out[t] = [drift[t,0],cd[0],cs[0],pd_[0],ps_[0]]
    np.testing.assert_allclose(out[lag:].sum(1), y[lag:,0], atol=1e-8, rtol=1e-8)
    if details:
        return out, float(rho), dict(A=A, residual=residual, fitted=X@B, nfit=int(fit.sum()), rank=int(keep.sum()))
    return out, float(rho)

def run(nominal, price, lag=12, fit_end=None, seasonal=True, weights="geometric"):
    idx = nominal.index[1:]
    dp = 100*np.log(price).diff().iloc[1:]
    dq = 100*np.log(nominal/price).diff().iloc[1:]
    share = nominal.div(nominal.sum(axis=1),axis=0)
    w = (np.sqrt(share*share.shift(1)) if weights=="geometric"
         else share.rolling(12).mean().shift(1)).iloc[1:]
    result = {}
    rho = {}
    for cat in price.columns:
        arr, rho[cat] = decompose(np.column_stack([dp[cat],dq[cat]]),lag,
                                  idx.month if seasonal else False, fit_end=fit_end)
        result[cat] = pd.DataFrame(arr,index=idx,columns=COLS).mul(w[cat],axis=0)
    panel = pd.concat(result,axis=1)
    monthly = panel.T.groupby(level=1).sum(min_count=len(result)).T[COLS]
    monthly["total"] = (w*dp).sum(axis=1,min_count=len(result))
    monthly.loc[monthly[COLS].isna().any(axis=1),"total"] = np.nan
    np.testing.assert_allclose(monthly[COLS].sum(axis=1,min_count=5),monthly.total,atol=1e-8)
    annual = monthly.rolling(12,min_periods=12).sum()
    annual["demand"] = annual.current_demand+annual.past_demand
    annual["supply"] = annual.current_supply+annual.past_supply
    annual["excess"] = annual.demand+annual.supply
    return annual, panel, pd.Series(rho,name="spectral_radius")

def self_test():
    rng = np.random.default_rng(42)
    y = np.zeros((400,2))
    A = np.array([[.4,.2],[-.1,.25]])
    for t in range(1,len(y)):
        y[t] = np.array([.1,.2])+A@y[t-1]+rng.normal(size=2)
    out,rho = decompose(y,1,False)
    assert rho<1
    assert np.max(np.abs(out[1:].sum(axis=1)-y[1:,0]))<1e-8
    assert np.allclose(out[1,3:],0)
    print("Synthetic VAR additivity and zero initial past shocks: PASS")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--self-test",action="store_true")
    ap.add_argument("--input-dir",type=Path)
    ap.add_argument("--raw-dir",type=Path,default=HERE/"02_data"/"raw")
    ap.add_argument("--download-only",action="store_true")
    args=ap.parse_args()
    if args.self_test:
        self_test(); return
    nominal,price=load_panel(args.input_dir, args.raw_dir)
    processed=HERE/"02_data"/"processed"
    processed.mkdir(parents=True, exist_ok=True)
    nominal.to_csv(processed/"nominal.csv")
    price.to_csv(processed/"price.csv")
    (nominal/price*100).to_csv(processed/"real.csv")
    pd.DataFrame(list(MAP.items()),columns=["kakei_code","cpi_code"]).to_csv(processed/"mapping.csv",index=False)
    if args.download_only:
        print("Complete panel validated and saved")
        return
    # Save baseline and sensitivity results; no unstable model is silently accepted.
    variants = {}
    for name,lag,seasonal,weights,fit_end in [
        ("baseline",12,True,"geometric",None),
        ("lag6",6,True,"geometric",None),
        ("no_seasonal",12,False,"geometric",None),
        ("lagged_weights",12,True,"lagged",None),
        ("pre2020_fit",12,True,"geometric",int((nominal.index[1:]<pd.Period("2020-01","M")).sum())),
    ]:
        annual,panel,rho=run(nominal,price,lag,fit_end,seasonal,weights)
        if (rho>=1).any():
            raise RuntimeError(name+" unstable VARs: "+str(rho[rho>=1].to_dict()))
        variants[name]=annual
        rho.to_csv(HERE/f"02_{name}_stability.csv")
        if name=="baseline":
            annual.to_csv(HERE/"02_jp_dupor_hogan_12m.csv",float_format="%.8f")
            panel.to_csv(HERE/"02_jp_dupor_hogan_items_monthly.csv",float_format="%.8f")
    comparison=pd.concat(variants,names=["specification","period"])
    comparison.to_csv(HERE/"02_jp_dupor_hogan_sensitivity.csv",float_format="%.8f")
    print(comparison.loc[(slice(None),[pd.Period(x,"M") for x in ["2022-12","2024-06","2025-09","2026-09"]]),:].round(3).to_string())
    import matplotlib.pyplot as plt
    annual=variants["baseline"].dropna().loc["2015-01":]
    fig,ax=plt.subplots(figsize=(12,5))
    positive=np.zeros(len(annual)); negative=positive.copy()
    for c,color in zip(COLS,["#999999","#2875bd","#df7900","#94c0e6","#f3c58b"]):
        v=annual[c].to_numpy()
        ax.bar(annual.index.to_timestamp(),v,bottom=np.where(v>=0,positive,negative),width=25,label=c,color=color)
        positive+=np.maximum(v,0); negative+=np.minimum(v,0)
    ax.plot(annual.index.to_timestamp(),annual.total,color="black",label="Total")
    ax.axhline(0,color="black",linewidth=.5); ax.legend(ncol=3); ax.set_ylabel("12-month log change, percentage points")
    fig.tight_layout(); fig.savefig(HERE/"02_chart_jp_dupor_hogan.png",dpi=180)
    plt.close(fig)

if __name__=="__main__":
    main()

