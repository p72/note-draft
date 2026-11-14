"""宮本（2025）再現用のデータ取得。SKILLS_DIR に Claude のカスタムスキル（fred-data）のベースディレクトリを指定して実行する。
FOMCの公表日（fomc_dates.txt）は、eco3min.fr の1990年以降のFOMC決定一覧（1995〜2023年）と、FRBの会合日程ページ（2021年以降）から作成した。
2020年3月の臨時利下げは3月3日（火）と3月15日（日）。日曜の公表は翌営業日に対応させる。"""
import os, sys
sys.path.insert(0, os.path.join(os.environ.get("SKILLS_DIR", "."), "fred-data"))
from scripts.fred_data import get_fred, get_yahoo
import pandas as pd
d = {k: get_fred(i, start="1994-10-01") for k, i in {"i1": "DGS1", "i2": "DGS2", "i3": "DGS3", "i5": "DGS5",
                                                   "i7": "DGS7", "i10": "DGS10", "fx": "DEXJPUS"}.items()}
pd.DataFrame(d).to_csv("us_daily_1994.csv")
get_yahoo("JPY=X", start="1994-01-01").to_csv("yahoo_jpy.csv")
