# 日本版Dupor・Hogan分解の再現手順

**実データ推計は未完了。** 現状と残課題は [検証記録](02_review.md) を参照。

## 準備
Pythonと numpy、pandas、requests、matplotlib を用意する。
e-StatのAPP IDは環境変数 ESTAT_APP_ID に設定する。キーはソース、引数、コミット、記録ファイルに書かない。

## 実行
このディレクトリで次を実行する。

```sh
python 02_verify_dupor_hogan.py
python 02_download_estat.py
python 02_dupor_hogan_jp.py --input-dir 02_data/raw
```

初回の通信ができなければ、取得済みの信頼できる kakei_0004023601.pkl と cpi_idx.pkl のあるフォルダを --input-dir へ指定できる。
CSVの場合は kakei.csv と cpi.csv（先頭列は月、cat01_code と value 列を含む）を置く。
取得専用処理も全期間・全品目の完全性を検査する。欠損を補間して処理を継続しない。

## 保存先
- 02_data/raw：APIの統計本体JSON、分類メタデータ、取得日時・条件・ハッシュのmanifest、読込用CSV。
- 02_data/processed：nominal.csv、price.csv、real.csv、mapping.csv。
- 元からある02_*.csv出力：5成分、品目別月次寄与、5仕様の比較、安定性。
- 既存グラフ処理は暫定であり、日本語の最終図表一式は未作成。

rawのJSONはレスポンスのSTATISTICAL_DATA部分を保存する。リクエストパラメータの認証情報は保存しない。
取得し直す場合は --raw-dir で別の空フォルダを指定して、取得時点を混ぜない。

実行成功だけで公表可とはしない。実データの単位・対象・末月・分類コードを確認し、検証記録の未完了項目を埋めてから記事に数値を反映する。

