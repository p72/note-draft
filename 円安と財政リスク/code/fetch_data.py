"""データ取得（Claude カスタムスキルのモジュールを使用）。
SKILLS_DIR にスキルのベースディレクトリ（fred-data, mof-jgb, boj-api, estat-api を含む）を指定して実行する。
各スキルは同名パッケージ scripts/ を持つため、サブプロセスで1つずつ読み込む。
"""
import os, subprocess, sys, textwrap
SK = os.environ.get("SKILLS_DIR", ".")
JOBS = {
"mof-jgb": """
from scripts.mof_jgb import get_yields
y = get_yields(start="2014-01-01")[[2, 10, 30]]; y.columns = ["jp2", "jp10", "jp30"]
y.to_csv("jgb_daily.csv")
""",
"fred-data": """
from scripts.fred_data import get_fred, get_fred_multi, get_yahoo
import pandas as pd
d = {k: get_fred(i, start="2022-01-01") for k, i in {"us2": "DGS2", "us10": "DGS10", "us30": "DGS30"}.items()}
d["usdjpy"] = get_yahoo("JPY=X", start="2022-01-01")
pd.DataFrame(d).to_csv("daily_us_fx.csv")
m, _ = get_fred_multi({"fx": "EXJPUS", "us2": "DGS2", "brent": "DCOILBRENTEU"}, start="2014-01-01", frequency="m", aggregation_method="avg")
c, _ = get_fred_multi({"us_core": "CPILFESL"}, start="2014-01-01", units="pc1")
m.join(c).to_csv("monthly_us.csv")
""",
"boj-api": """
from scripts.boj_api import get_series
# デジタル関連収支は日本銀行の定義（著作権等使用料＋通信・コンピュータ・情報サービス＋専門・経営コンサルティングサービス）
codes = {"COPY": "BPBP6JYNSN9062", "ICT": "BPBP6JYNSN907", "CONS": "BPBP6JYNSN9082",
         "FDI": "BPBP6JYNFB1", "FDI_reinv_A": "BPBP6JYNFA132", "FDI_reinv_L": "BPBP6JYNFL132",
         "TB": "BPBP6JYNTB", "EQ_A": "BPBP6JYNFA21"}
df = get_series("BP01", list(codes.values()), start_date="201401"); df.columns = list(codes)
df.to_csv("bop.csv")
# 東京市場ドル・円スポット17時時点（日次）：国債の東京終値と時点をそろえるため
fx = get_series("FM08", "FXERD04", start_date="202201", dropna=True); fx.columns = ["usdjpy_tokyo17"]
fx.to_csv("usdjpy_tokyo17.csv")
""",
"estat-api": """
from scripts.estat_api import get_stats_df
import pandas as pd
out = {}
for k, c in {"jp_core": "0161", "jp_cc": "0178"}.items():
    d = get_stats_df("0003427113", cdCat01=c, cdArea="00000", cdTab="3", cdTimeFrom="2013000101", monthly=True)
    s = d["value"]; s.index = s.index.to_timestamp(); out[k] = s
pd.DataFrame(out).to_csv("jpcpi.csv")
""",
}
for skill, code in JOBS.items():
    pre = f"import sys; sys.path.insert(0, {os.path.join(SK, skill)!r})\n"
    subprocess.run([sys.executable, "-c", pre + textwrap.dedent(code)], check=True)
    print("done:", skill)
