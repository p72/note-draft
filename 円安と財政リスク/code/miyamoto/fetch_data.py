"""宮本（2025）再現用のデータ取得。SKILLS_DIR に Claude のカスタムスキル（fred-data）のベースディレクトリを指定して実行する。
FOMCの公表日（fomc_dates.txt）は、eco3min.fr の1990年以降のFOMC決定一覧（1995〜2023年）と、FRBの会合日程ページ（2021年以降）から作成した。
2020年3月の臨時利下げは3月3日（火）と3月15日（日）。日曜の公表は翌営業日に対応させる。
2008年の臨時の決定は1月22日と10月8日（Glick and Leduc 2018 の脚注9と一致）。
FOMC公表日以外のイベント（speech_dates.txt）は、Glick and Leduc (2015/2018) の表1と脚注10にある
議長のスピーチ・議会証言・臨時の発表の7日（2008年11月25日、12月1日、2010年8月27日、10月15日、2011年8月26日、2012年8月31日、2013年5月22日）。"""
import os, sys
sys.path.insert(0, os.path.join(os.environ.get("SKILLS_DIR", "."), "fred-data"))
from scripts.fred_data import get_fred, get_yahoo
import pandas as pd
d = {k: get_fred(i, start="1994-10-01") for k, i in {"i1": "DGS1", "i2": "DGS2", "i3": "DGS3", "i5": "DGS5",
                                                   "i7": "DGS7", "i10": "DGS10", "fx": "DEXJPUS"}.items()}
pd.DataFrame(d).to_csv("us_daily_1994.csv")
get_yahoo("JPY=X", start="1994-01-01").to_csv("yahoo_jpy.csv")
# Gürkaynak-Sack-Wright のゼロクーポン金利（FRB、www.federalreserve.gov）
import io, urllib.request
txt = urllib.request.urlopen("https://www.federalreserve.gov/data/yield-curve-tables/feds200628.csv", timeout=120).read().decode()
lines = txt.splitlines(); h = [i for i, l in enumerate(lines) if l.startswith("Date,")][0]
g = pd.read_csv(io.StringIO("\n".join(lines[h:])), index_col=0, parse_dates=True)
g[[f"SVENY0{k}" for k in range(1, 6)]].apply(pd.to_numeric, errors="coerce").loc["1994-10-01":].to_csv("gsw_1to5.csv")
