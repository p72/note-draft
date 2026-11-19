import sys, time
sys.path.insert(0,"/root/.claude/skills/synced/42857046-7317-47fd-aa84-fb40ead701d4_f90ecdde-6477-4665-b7b2-90b3176d5903/estat-api")
from scripts.estat_api import get_stats_df
time.sleep(3)
df=get_stats_df("0003427113", cdCat01="0001", cdArea="00000", cdTab="1")
print(df.tab_name.iloc[0], len(df))
df["y"]=df.time_name.str.extract(r"(\d{4})年").astype(int)
df["m"]=df.time_name.str.extract(r"年(\d+)月")
m=df[df.m.notna()]
a=m.groupby("y").value.agg(["mean","count"])
a=a[a["count"]==12]; a["CPI"]=(a["mean"].pct_change()*100).round(1)
print(a.tail(35)); a[["CPI"]].to_csv("cpi.csv")
