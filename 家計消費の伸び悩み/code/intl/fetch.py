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

# ---- 2020年代の四半期比較（季節調整値） ----
fq = "OECD.SDD.NAD,DSD_NASEC1@DF_QSA,1.1"
kq = build_key(fq, FREQ='Q', ADJUSTMENT='Y', REF_AREA=A, SECTOR='S1M',
               TRANSACTION=['B6G', 'P3', 'D1', 'D5', 'D61', 'D62', 'D4', 'B2A3G', 'B8G', 'D8'], TRANSFORMATION='N')
get_data(fq, kq, start='2019-Q1').to_csv('qsa.csv', index=False)
fn = "OECD.SDD.NAD,DSD_NAMAIN1@DF_QNA,1.1"
for pb, out in [('V', 'qna_p3.csv'), ('L', 'qna_p3_L.csv')]:
    kn = build_key(fn, FREQ='Q', ADJUSTMENT='Y', REF_AREA=A, SECTOR='S1M', TRANSACTION='P3', UNIT_MEASURE='XDC',
                   PRICE_BASE=pb, TRANSFORMATION='N')
    get_data(fn, kn, start='2019-Q1').to_csv(out, index=False)
fpq = "OECD.SDD.NAD,DSD_NAMAIN1@DF_QNA_POP_EMPNC,1.1"
get_data(fpq, build_key(fpq, FREQ='Q', REF_AREA=A, TRANSACTION='POP'), start='2019-Q1').to_csv('qpop.csv', index=False)
# 日本は内閣府の家計可処分所得・貯蓄率四半期別速報（../levels3.csv）を使う

# ---- 年金（公的老齢給付）----
fc = "OECD.SDD.NAD,DSD_NASEC10@DF_TABLE11,1.1"
kc = build_key(fc, REF_AREA=['JPN', 'USA', 'GBR', 'DEU', 'FRA', 'ITA', 'KOR', 'AUS'], SECTOR='S13',
               TRANSACTION=['D62', 'OTE'], EXPENDITURE=['GF1002', 'GF10', '_T'])
get_data(fc, kc, start='2010').to_csv('cofog.csv', index=False)

# 65歳以上人口（World Bank WDI, SP.POP.65UP.TO）：worldbank-data スキルの wb_utils.fetch で取得し pop65.csv に保存
# 米国の社会保障給付（FRED W823RC1A027NBEA, 10億ドル）：環境変数 FRED_API_KEY を使って取得し us_socsec.csv に保存
import os, requests, pandas as pd
r = requests.get('https://api.stlouisfed.org/fred/series/observations',
                 params=dict(series_id='W823RC1A027NBEA', api_key=os.environ['FRED_API_KEY'], file_type='json',
                             observation_start='2010-01-01'), timeout=30)
pd.Series({int(o['date'][:4]): float(o['value']) for o in r.json()['observations'] if o['value'] != '.'}).to_csv('us_socsec.csv')
