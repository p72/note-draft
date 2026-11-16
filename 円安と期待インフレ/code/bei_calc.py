import csv, io, math, datetime, urllib.request, time

def fetch_jsda(date):
    """date: datetime.date (publication date). Return rows or None."""
    y, m, d = date.year, date.month, date.day
    cands = []
    if date >= datetime.date(2020,3,2):
        cands.append(f"https://market.jsda.or.jp/shijyo/saiken/baibai/baisanchi/files/{y}/S{y%100:02d}{m:02d}{d:02d}.csv")
    else:
        cands.append(f"https://market.jsda.or.jp/shijyo/saiken/baibai/baisanchi/files/{y}/{m:02d}/S{y%100:02d}{m:02d}{d:02d}.csv")
        cands.append(f"https://market.jsda.or.jp/shijyo/saiken/baibai/baisanchi/files/{y}/SA{y%100:02d}{m:02d}{d:02d}.csv")
    for url in cands:
        try:
            req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                data = r.read()
            text = data.decode("shift_jis", errors="replace")
            rows = list(csv.reader(io.StringIO(text)))
            if rows and len(rows[0])>=10:
                return rows, url
        except Exception as e:
            continue
    return None, None

COUPON = {  # JGBi coupon % per annum, by issue no. (MOF/fund disclosures)
    16:0.1,17:0.1,18:0.1,19:0.1,20:0.1,21:0.1,22:0.1,23:0.1,24:0.1,25:0.1,
    26:0.005,27:0.005,28:0.005,29:0.005,30:0.005,31:0.6,
}

def coupon_dates(maturity):
    # semiannual Mar 10 / Sep 10 going back
    dates=[]
    dt=maturity
    while dt > datetime.date(2000,1,1):
        dates.append(dt)
        # step back 6 months: Mar10 -> prev Sep10, Sep10 -> Mar10
        if dt.month==3:
            dt=datetime.date(dt.year-1,9,10)
        else:
            dt=datetime.date(dt.year,3,10)
        if len(dates)>40: break
    return sorted(dates)

def real_ytm(settle, maturity, coupon_pct, clean):
    cds = [d for d in coupon_dates(maturity) if d>settle]
    # last coupon on/before settle
    allcd = coupon_dates(maturity)
    prev = max([d for d in allcd if d<=settle])
    nxt = min([d for d in allcd if d>settle])
    frac = (nxt-settle).days/(nxt-prev).days  # fraction of period remaining
    accrued = (coupon_pct/2)*((settle-prev).days/(nxt-prev).days)
    dirty = clean + accrued
    def price(y):
        pv=0.0
        for i,cd in enumerate(cds):
            t = frac + i
            cf = coupon_pct/2 + (100.0 if cd==maturity else 0.0)
            pv += cf/((1+y/200.0)**t) if False else cf/((1+y/2/100)**t)
        return pv
    lo, hi = -5.0, 20.0
    for _ in range(100):
        mid=(lo+hi)/2
        if price(mid) > dirty: lo=mid
        else: hi=mid
    return (lo+hi)/2, dirty, accrued

def bei_on(date):
    rows, url = fetch_jsda(date)
    if rows is None: return None
    jgbi=[]; nominal=[]
    for r in rows:
        if len(r)<8: continue
        name=r[3]
        try: mat=datetime.datetime.strptime(r[4],"%Y%m%d").date()
        except: continue
        if name.startswith("物価連動国債"):
            try: issue=int(name.split()[-1]); price=float(r[7])
            except: continue
            jgbi.append((mat, issue, price))
        if r[1]=="02" and ("長期国債" in name) and not name.startswith("超長期"):
            try: yld=float(r[6]); price=float(r[7]); cpn=float(r[5])
            except: continue
            nominal.append((mat, yld, price, cpn, name))
    if not jgbi or not nominal: return None
    # newest JGBi = longest maturity
    jgbi.sort()
    mat, issue, price = jgbi[-1]
    cpn = COUPON.get(issue)
    if cpn is None: return {"date":date,"error":f"no coupon issue {issue}"}
    ry, dirty, acc = real_ytm(date, mat, cpn, price)
    # nominal with maturity closest to JGBi maturity
    nominal.sort(key=lambda x: abs((x[0]-mat).days))
    nmat, nyld, nprice, ncpn, nname = nominal[0]
    return {"date":str(date),"jgbi_issue":issue,"jgbi_mat":str(mat),"jgbi_price":price,"coupon":cpn,
            "real_yield":round(ry,3),"nominal_name":nname,"nominal_mat":str(nmat),"nominal_yield":nyld,
            "BEI":round(nyld-ry,3),"url":url}

if __name__=="__main__":
    for dstr in ["2024-03-29","2025-03-31","2026-01-07","2026-01-22","2026-03-31","2026-07-30"]:
        d=datetime.date.fromisoformat(dstr)
        print(bei_on(d)); time.sleep(1)
