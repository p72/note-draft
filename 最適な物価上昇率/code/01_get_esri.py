import sys
sys.path.insert(0, "/root/.claude/skills/synced/42857046-7317-47fd-aa84-fb40ead701d4_f90ecdde-6477-4665-b7b2-90b3176d5903/esri-data")
from scripts.esri_data import get_qe_raw, parse_qe_column, get_latest_qe_info
import pandas as pd
print(get_latest_qe_info()["label"])
out={}
for k,s in [("名目","ritu-mcy"),("実質","ritu-jcy"),("デフレーター","rdef-cy")]:
    raw=get_qe_raw(series=s); d=parse_qe_column(raw,"GDP" if s!="rdef-cy" else 1)
    print(s, raw.attrs.get("url"))
    out[k]=d.set_index("year")["value"]
df=pd.DataFrame(out); print(df); df.to_csv("esri.csv")
