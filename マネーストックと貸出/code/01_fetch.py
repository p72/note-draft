"""日本銀行 時系列統計API と e-Stat API からデータを取得し、code/ に CSV で保存する。"""
import sys, pathlib
import pandas as pd
HERE = pathlib.Path(__file__).parent
sys.path.insert(0, "/mnt/skills/plugins/boj-api")
from scripts.boj_api import get_series  # noqa: E402

# 旧マネタリーサーベイ（～1999/3）と 2008/3 までのマネタリーサーベイ：民間向け貸出、通貨、準通貨＋CD（末残、億円）
ms = get_series("MD03", "MASVK_MASV1A51,MASVK_MASV1L1,MASVK_MASV1L2,MASV4NA51,MASV4NL1,MASV4NL2")
ms.to_csv(HERE / "survey.csv")
# 総貸出平残（銀行・信金計）と M3 平残（億円）
cur = get_series("MD13", "FAAP@01", start_date="200001").join(
    get_series("MD02", "MAM1NAM3M3MO", start_date="200304"), how="outer")
cur.to_csv(HERE / "loan_m3.csv")

sys.modules.pop("scripts", None)
sys.path.insert(0, "/mnt/skills/plugins/estat-api")
from scripts.estat_api import get_stats_df  # noqa: E402
# 消費者物価指数（2020年基準）総合・全国・指数
cpi = get_stats_df("0003427113", cdCat01="0001", cdArea="00000", cdTab="1", monthly=True)
cpi[["value"]].rename(columns={"value": "cpi"}).to_csv(HERE / "cpi.csv")
