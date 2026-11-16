import datetime, calendar, sys, time, json
sys.path.insert(0,'/home/hatch/workspace/bei-replication')
from bei_calc import bei_on
out=[]
y,m=2015,1
while (y,m) <= (2026,7):
    last=calendar.monthrange(y,m)[1]
    got=None
    for back in range(0,10):
        d=datetime.date(y,m,last-back)
        try: r=bei_on(d)
        except Exception as e: r=None
        if r and "BEI" in r: got=r; break
        time.sleep(0.5)
    print(y,m, got["date"] if got else None, got["BEI"] if got else None, flush=True)
    if got: out.append(got)
    m+=1
    if m==13: y,m=y+1,1
    time.sleep(0.5)
import csv
with open('/home/hatch/workspace/bei-replication/bei_monthly.csv','w',newline='') as f:
    w=csv.DictWriter(f, fieldnames=["date","jgbi_issue","jgbi_mat","jgbi_price","coupon","real_yield","nominal_name","nominal_mat","nominal_yield","BEI","url"])
    w.writeheader()
    for r in out: w.writerow({k:r.get(k) for k in w.fieldnames})
print("saved", len(out))
