"""OECD SDMX API から9か国の家計データを取得する（2026-10-26 取得時のクエリ）。
OECD_DATA_SKILL_DIR は oecd-data スキル（scripts/oecd_data.py）の置き場所に置き換える。"""
import sys
sys.path.insert(0, 'OECD_DATA_SKILL_DIR')
from scripts.oecd_data import build_key, get_data

A = ['JPN', 'USA', 'GBR', 'DEU', 'FRA', 'ITA', 'CAN', 'KOR', 'AUS']

# 制度部門別所得支出勘定（家計＋対家計民間非営利団体 S1M）
f14 = "OECD.SDD.NAD,DSD_NASEC10@DF_TABLE14,1.1"
T = ['B6G', 'P3', 'P31', 'D8', 'B8G', 'D1', 'D5', 'D61', 'D62', 'B2A3G', 'D4']
get_data(f14, build_key(f14, REF_AREA=A, SECTOR='S1M', TRANSACTION=T), start='1995').to_csv('table14.csv', index=False)

# 家計最終消費支出（名目 V・実質 LR）
f1 = "OECD.SDD.NAD,DSD_NAMAIN10@DF_TABLE1_EXPENDITURE,2.0"
k1 = build_key(f1, REF_AREA=A, SECTOR=['S1M', 'S14'], TRANSACTION=['P3', 'P31'], UNIT_MEASURE='XDC',
               PRICE_BASE=['V', 'LR'], TRANSFORMATION='N')
get_data(f1, k1, start='1995').to_csv('table1_p3.csv', index=False)

# 人口
f3 = "OECD.SDD.NAD,DSD_NAMAIN10@DF_TABLE3_POP_EMPNC,2.0"
get_data(f3, build_key(f3, REF_AREA=A, TRANSACTION='POP'), start='1995').to_csv('pop.csv', index=False)
