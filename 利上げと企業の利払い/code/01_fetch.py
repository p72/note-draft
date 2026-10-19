"""法人企業統計（e-Stat）と日本銀行のコールレートを取得する。
e-Stat API の appId は環境変数 ESTAT_APP_ID で渡す。
"""
import sys, pandas as pd
sys.path.insert(0, "<estat-api スキルのディレクトリ>")   # estat_api.py
sys.path.insert(0, "<boj-api スキルのディレクトリ>")     # boj_api.py
from scripts.estat_api import get_stats_df
from scripts.boj_api import get_series

SID = "0003060191"   # 法人企業統計 時系列データ 金融業、保険業以外の業種（原数値）四半期
PL = "081,082,084,086"                 # 営業利益, 受取利息等, 支払利息等, 経常利益
DEBT = "015,016,019,020,021"           # 金融機関借入金(短・長), その他借入金(短・長), 社債
get_stats_df(SID, cdCat01=PL, cdCat02="104", cdCat03="26,25").to_csv("mof.csv", index=False)
get_stats_df(SID, cdCat01=DEBT, cdCat02="104", cdCat03="26,25").to_csv("debt.csv", index=False)
a = get_stats_df(SID, cdCat01=PL + "," + DEBT, cdCat02="104", cdCat03="25,24,19,26")
b = get_stats_df(SID, cdCat01=PL + "," + DEBT,
                 cdCat02="108,144,107,135,142,134,129,130,150,156,137,115,118,123", cdCat03="26")
pd.concat([a, b]).to_csv("detail.csv", index=False)
# 有担保コール翌日物（〜1985年6月）と無担保コールO/N（1985年7月〜）の月平均
get_series("FM02", "STRACLCOON,STRACLUCON", start_date="196001").to_csv("call.csv")
