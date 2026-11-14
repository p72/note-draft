# code

記事「高市政権の財政リスクは円安の最大の原因か」の推計コードとデータ。

実行順：
1. `fetch_data.py`：データ取得。環境変数 `SKILLS_DIR` に Claude のカスタムスキル（fred-data、mof-jgb、boj-api、estat-api）のベースディレクトリを指定して実行する。取得済みのデータ（2026年11月14日取得）を同梱：`jgb_daily.csv`（国債2・10・30年）、`daily_us_fx.csv`（米国債2・10・30年、ドル円 Yahoo）、`usdjpy_tokyo17.csv`（ドル円 東京17時）、`monthly_us.csv`（ドル円・米2年・ブレントの月平均、米コアCPI前年比。2025年10月の米CPIは未公表で欠測）、`bop.csv`（国際収支、億円）、`jpcpi.csv`（日本CPI前年比）
2. `models.py`：推計一式
   - `weekly.csv`、`monthly.csv`、`daily.csv`：推計に使った系列と当てはめ値・異常変化
   - `regression_results.csv`：表1・表2と追加の推計、係数差の検定
   - `unitroot.csv`：ADF検定と Engle-Granger 検定（最終行の右2列は5%・10%の臨界値）
   - `decomposition.csv`：要因分解（対数ポイント、定式化別）
   - `events.csv`、`events_summary.csv`：イベントスタディ
   - `signclass.csv`：日次の符号分類
3. `plots.py`：図1〜図4（`../01_chart_gap.png`、`../01_chart_decomp.png`、`../01_chart_oil.png`、`../01_chart_event.png`）。日本語フォントは Noto Sans CJK JP

必要なパッケージ：pandas、numpy、statsmodels（0.14以降）、matplotlib
