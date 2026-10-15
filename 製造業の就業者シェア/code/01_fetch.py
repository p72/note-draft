"""労働力調査（基本集計）年平均の産業別就業者数を e-Stat API から取得する。
estat-api スキルの scripts/estat_api.py を使う（appId は環境変数 ESTAT_APP_ID）。
出力: old.csv / old10.csv / new.csv / old_med.csv / new_med.csv（01_plot.py の入力）
"""
import sys
sys.path.insert(0, "/mnt/skills/plugins/estat-api")
from scripts.estat_api import get_stats_df

common = dict(cdCat02="0", cdCat03="00")  # 男女計・15歳以上
# 0002060057: 年齢階級，産業別就業者数（1953年～2009年）第10・11回改定産業分類
get_stats_df("0002060057", cdCat01="000,010", **common).to_csv("old.csv", index=False)   # 全産業, 製造業(第11回 2003-)
get_stats_df("0002060057", cdCat01="A009", **common).to_csv("old10.csv", index=False)     # *製造業(第10回 1953-2002)
get_stats_df("0002060057", cdCat01="064", **common).to_csv("old_med.csv", index=False)    # 医療，福祉(第11回)
# 0003007108: 年齢階級，産業別就業者数（2007年～）第12・13回改定産業分類
get_stats_df("0003007108", cdCat01="00,10", **common).to_csv("new.csv", index=False)     # 全産業, 製造業
get_stats_df("0003007108", cdCat01="78,51", **common).to_csv("new_med.csv", index=False)  # 医療，福祉, 卸売業，小売業
