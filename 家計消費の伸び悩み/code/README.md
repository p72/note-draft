# 査読後の再計算手順

リポジトリのルートから実行する。絶対パスや元著者の独自スキルは不要。

```bash
python -m pip install -r 家計消費の伸び悩み/code/requirements-review.txt
python 家計消費の伸び悩み/code/review_reproduce.py
```

`review_reproduce.py` が現行の図2〜4を生成する入口。`chart3.py`〜`chart5.py` 等は元稿の作業記録であり、現行図の生成には使わない。

## 入力と出力

| 保存入力 | 内容 | 再計算できる範囲 |
| --- | --- | --- |
| levels3.csv | SNA家計系列、GDP系列、資金循環、CSI、加工値 | 恒等式、貯蓄率回帰A、図2 |
| decomp.csv | 前年比の恒等式分解 | 分解の残差確認 |
| burden.csv | 2019・2022・2025年の年齢別所得・消費・黒字内訳 | 本文年齢別表、図3上段、図4 |
| shiftshare.csv | 丸め済みの名目シフトシェア分解 | 図3下段の厳密な実質化（原分解は未再現） |
| cpi_y.csv | CPI総合の年平均 | 図3下段 |
| source/kakei_26q2.xlsx | 内閣府の原本 | 保存済み家計13系列と130四半期の照合 |

出力は `../01_chart_saving.png`、`../01_chart_age.png`、`../01_chart_workers.png` と `review_periods.csv`、`review_shiftshare.csv`、`review_regression.csv`、`review_checks.json`。既存の入力CSVは上書きしない。

検算は、恒等式、名目消費系列の一致、貯蓄率の定義、回帰の既存当てはめ値との一致、実質分解の加算整合性、黒字内訳の加算整合性を確認する。丸め済み原数値の許容誤差を設けている。

## 原本取得と検証の範囲

- 取得日：2026-10-26（日本時間）。内閣府の2026年10月9日公表、2026年4〜6月期速報値、2020年基準・2008SNA。
- URL：https://www.esri.cao.go.jp/jp/sna/data/data_list/kakei/files/2026/tables/kakei_26q2.xlsx
- SHA-256：`75fa03e0a4eb1058916d4a903fe15f6efb48437da45f5a2d073ecad3cf21a571`
- 季調系列シートの営業余剰から実質可処分所得までの13系列を `levels3.csv` と照合し、1994Q1〜2026Q2の130四半期すべて一致した。金額は年率、単位は10億円。貯蓄率は％。
- 元稿のSNA・資金循環・家計調査・CSIのうち、このExcelに含まれない原データ全体の再取得・照合は行っていない。今回の数値検証は主に保存加工CSVに基づく。
- `age_w.csv`、`age_c.csv`、`age_apc_w.csv`、`apc_w_avg.csv`、`kakei_age.csv`、`kakei_w2.csv`、`csi_age_ann.csv`、月次の消費者意識・物価見通しExcelなどは元コミットにない。元スクリプトの `/home/claude`、`/mnt/skills`、一時ディレクトリ等もこの環境では存在しない。
- 図1・図5は元稿の画像を維持。図1の恒等式は再検算したが、元の画像生成経路全体は修復していない。図5の全時系列とハードコードされた物価予想割合の再集計は未検証で、参考図として扱う。`csi_age.csv` だけでは全パネルを再生成できない。
- 図3では欠けた年齢別原表を推測せず、保存済みの名目寄与を実質化する。実質年齢別支出から直接行う中点分解ではなく、物価項を独立表示した会計分解。名目寄与が小数2桁なので丸め残差も保存する。

依存パッケージの範囲は通常の利用環境を想定。今回の確認環境は Python 3.12.14、NumPy 2.3.5、pandas 2.2.3、Matplotlib 3.10.8、statsmodels 0.15.0、japanize-matplotlib 1.1.3、openpyxl 3.1.5。バージョン差で画像のピクセルや回帰末尾桁は変わり得る。
