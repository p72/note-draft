# miyamoto

宮本亘（2025）「日本の為替レートの動向と決定要因に関する分析」（日本銀行ワーキングペーパー No.25-J-2）の構造VARを、公表データで再現・延長するコード。

論文の仕様：米国債1〜5年金利（Gürkaynak-Sack-Wright）の日次変化とドル円（Bloomberg）の対数日次変化×100のVAR(2)。FOMC公表日などの誘導型残差の共分散から下三角の B^F を求め、金利ショックの列に B_n = x_n B^F_n の制約を置いて、vech(BB')−vech(Ω̂) の重み付き二乗を最小化する。

本稿の置き換え・仮定：
- 金利：論文と同じ Gürkaynak-Sack-Wright のゼロクーポン金利1〜5年（FRB）。FRED の国債定満期利回り DGS1・2・3・5（4本）は感度分析（`rates="fred"`）
- ドル円：FRED の DEXJPUS（ニューヨーク正午）。FOMCの発表（東部時間午後）より前の値なので、翌営業日の正午の値を当日の終わりの値とみなす（`fx="fred_lead"`）。正午の値そのまま（`fred`）と Yahoo の終値（`yahoo`、1996年10月から）は感度分析
- イベント日：FOMCの政策決定の公表日（臨時を含む）と、Glick and Leduc (2018) の表1・脚注10にある議長のスピーチ・議会証言などの7日（`speech_dates.txt`）。論文がGlick and Leducのどの日を使ったかは本文に記載がないため、この選び方は本稿の仮定
- ドル円の列は B_6 = x_6 B^F_6（ドル円のショックは同時点の金利に影響しない）
- 重み：1段階目は単位行列、2段階目は vech(u_t u_t') の分散の逆行列
- 要因分解：論文と同じ定義。期首の前の状態から期間中のショックを0としたVARの予測（VARトレンド）と、期間中の各構造ショックの寄与に分け、実績＝トレンド＋寄与の合計を確認（`identity_check`）
- ブートストラップ：FOMC日とそれ以外の日を分けた残差の引き直し（各200回）。再推計した係数を実際のデータに当てはめて分解する

ファイル：
- `fetch_data.py`：データ取得（`us_daily_1994.csv`、`yahoo_jpy.csv`、`gsw_1to5.csv`）
- `fomc_dates.txt`：FOMCの公表日（1995〜2026年）
- `speech_dates.txt`：FOMC公表日以外のイベント日（7日）
- `miyamoto_boot.py`：関数版、感度分析とブートストラップ（`python3 miyamoto_boot.py 200` → `miyamoto_sensitivity.csv`）
- `miyamoto_extension.csv`：2026年11月まで延長した推計の窓別の分解（ブートストラップ200回）
- `miyamoto_plot.py`：図（`../../01_chart_miyamoto.png`）と `miyamoto_hd_2021_2026.csv`
