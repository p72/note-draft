# code

記事「高市政権の財政リスクは円安の最大の原因か」の推計コードとデータ。

実行順：
1. `fetch_data.py`：データ取得。環境変数 `SKILLS_DIR` に Claude のカスタムスキル（fred-data、mof-jgb、boj-api、estat-api）のベースディレクトリを指定して実行する。取得済みのデータ（`jgb_daily.csv`、`daily_us_fx.csv`、`monthly_us.csv`、`bop.csv`、`jpcpi.csv`）を同梱
2. `models.py`：週次の金利差モデル（`weekly.csv`）、月次の要因分解モデル（`monthly.csv`）、回帰結果（`regression_results.csv`）、要因分解（`decomposition.csv`）
3. `plots.py`：図1〜図3（`../01_chart_gap.png`、`../01_chart_decomp.png`、`../01_chart_oil.png`）。日本語フォントは Noto Sans CJK JP

必要なパッケージ：pandas、numpy、statsmodels、matplotlib
