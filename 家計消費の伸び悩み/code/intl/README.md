# 02 国際比較の計算手順

このフォルダのスクリプトを順に実行する（作業ディレクトリはこのフォルダ）。

1. `fetch.py`：OECD SDMX API から `table14.csv`・`table1_p3.csv`・`pop.csv` を取得（取得日 2026-10-26）
2. `build.py`：`panel.csv` と、1人当たり実質消費の分解 `decomp_intl.csv` を作成
3. `income.py`：1人当たり名目可処分所得の項目別寄与 `income_decomp.csv` を作成
4. `recent_q.py`・`recent_income.py`：2022年平均→直近4四半期の分解（`decomp_recent_q.csv`、`income_recent_q.csv`）。日本は `../levels3.csv`（内閣府）を使う
5. `pension.py`：65歳以上1人当たり公的老齢給付の伸び（`pension_intl.csv`）
6. `charts.py`・`chart_recent_q.py`・`chart_pension.py`：記事の図（`../../02_chart_*.png`）を作成。日本語フォント設定に esri-data スキルの `setup_japanese_font` を使っている（`ESRI_DATA_SKILL_DIR` を置き換えるか、任意の日本語フォント設定に差し替える）

保存済みCSVがあれば、1 を飛ばして 2 以降だけで再計算できる。charts.py は図をカレントディレクトリに出力するので、記事フォルダへ移す。

## 査読後の本文・図4〜5を再生成する

現在の本文の近年比較は、全9か国で定義・期間を合わせた年次の2022→2024年である。旧四半期比較では日本の純所得と他国の総所得が混在しているため、旧CSVと図は作業記録として保持し、本文には使わない。

リポジトリのルートから次を実行する。

```bash
python -m pip install -r 家計消費の伸び悩み/code/intl/requirements-review.txt
python 家計消費の伸び悩み/code/intl/review_intl.py
```

ネットワーク接続・独自スキル・APIキーは不要。入力は保存済みの `table14.csv`、`table1_p3.csv`、`pop.csv`、`cofog.csv`、`pop65.csv`、`us_socsec.csv` と、比較検算用の既存の加工CSV。入力ファイルは上書きしない。

出力：

- `review_annual_decomp.csv`：2000/2019/2021/2022→2024年、9か国。全期間で総所得B6G・部門S1M。
- `review_annual_income.csv`：同期間の所得項目寄与。欠測項目名を記録し、残差の「その他」に含める。
- `review_pension.csv`：主比較5か国＋米国・豪州参考値の21行。給付総額・65歳以上人口・物価を別々に記録。
- `review_pension_index.csv`：2012〜2024年の指数。
- `review_checks.json`：既存結果との照合行数、恒等式の残差、日本の結果。
- 記事フォルダの `02_chart_2022annual.png` と `02_chart_pension.png`。

年次27行・所得寄与18行・年金21行の既存結果との一致を確認する。年金の豪州値は大幅増だからという理由だけで捨てず参考CSVに保持。米国も主比較とは異なる範囲として扱う。COFOG D62/GF1002の支出を65歳以上人口で割った指標は、受給者1人当たり年金額ではない。

元の `fetch.py` は独自スキルやFREDのキーを必要とし、World Bank人口取得の実装も別途必要。今回のスクリプトは**保存原表からの計算の再現**を対象にし、OECD・World Bank全系列を再取得・照合するものではない。図1〜3の元画像は維持し、その本文に対応する集計値を再検算した。
