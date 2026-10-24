# code

記事「閾値を超える円安水準は毎年動く」の推計コードとデータ。

実行順：
1. データ取得（記事の付記を参照）。`boj.csv`（ドル円・企業物価）、`cpi.csv`（新コアコア）、`cpi_core.csv`（コア）は取得済みのものを同梱。毎月勤労統計の長期時系列表（`wage.xls`＝現金給与総額5人以上、`wage30.xls`＝同30人以上、`kimatte30.xls`＝きまって支給する給与30人以上、`hours30.xls`＝総実労働時間30人以上）は e-Stat の getDataCatalog から取得する（統計コード00450071、2026年8月分の statInfId は順に 000032189720、000032189721、000032189727、000032189743）
2. `build_data.py`：四半期データ `quarterly.csv` を作成
3. `model2.py`：佐々木ほか（2023）の(1)式による閾値モデルの推計（論文再現・大和条件・更新版）→ `est2.pkl`
4. `est2024.py`：2024年6月版（コアCPI）の再現と、推計終期を変えた新コアコア版
5. `scenario2.py`：図1・図3とシナリオ別の押し上げ（`scenario2_results.csv`）
6. `thresh_level.py`：図2と閾値を超えるドル円水準（`threshold_yen_level.csv`）

`model2.py`・`scenario2.py` は e-Stat・日銀APIのラッパー（Claude のカスタムスキル boj-api、estat-api）を import している部分がある（日本語フォントの設定とデータ取得のみ）。
