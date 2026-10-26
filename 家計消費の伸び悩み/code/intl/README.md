# 02 国際比較の計算手順

このフォルダのスクリプトを順に実行する（作業ディレクトリはこのフォルダ）。

1. `fetch.py`：OECD SDMX API から `table14.csv`・`table1_p3.csv`・`pop.csv` を取得（取得日 2026-10-26）
2. `build.py`：`panel.csv` と、1人当たり実質消費の分解 `decomp_intl.csv` を作成
3. `income.py`：1人当たり名目可処分所得の項目別寄与 `income_decomp.csv` を作成
4. `charts.py`：記事の図（`../../02_chart_*.png`）を作成。日本語フォント設定に esri-data スキルの `setup_japanese_font` を使っている（`ESRI_DATA_SKILL_DIR` を置き換えるか、任意の日本語フォント設定に差し替える）

保存済みCSVがあれば、1 を飛ばして 2〜4 だけで再計算できる。charts.py は図をカレントディレクトリに出力するので、記事フォルダへ移す。
