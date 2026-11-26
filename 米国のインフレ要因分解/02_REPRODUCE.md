# 日本版Dupor・Hogan分解の再現手順

実データを取得し、18仕様の診断推計・比較を実施済み。基準VAR(12)は2分類で不安定であり、研究は未完了。[結果](02_results.md)・[検証記録](02_review.md)を参照。

## オフライン再現（取得済みデータを同梱）

Python、numpy、pandas、requests、matplotlibを用意する。このディレクトリで実行する。

```sh
python 02_verify_dupor_hogan.py
python 02_dupor_hogan_jp.py --input-dir 02_data/raw --download-only
python 02_empirical_analysis.py
python 02_compare_observed.py
python 02_download_us.py
```

最後のコマンドは保存済み米国HTMLを読みCSVを再生成する。HTMLがない場合のみ公表ページから取得する。
`02_compare_observed.py` は原JSONのハッシュと入力CSVを照合し、既存Shapiroコードを一時ディレクトリで再実行する。pickleは自分で取得CSVから生成した一時ファイルだけを読む。加工対応表には分類名も追加する。

`02_dupor_hogan_jp.py --input-dir 02_data/raw`（`--download-only`なし）は基準VAR(12)の不安定性で停止するのが今回の正しい挙動。安全チェックを解除しない。`02_empirical_analysis.py` は不安定仕様も明示した診断専用出力であり、公開用推計を意味しない。

クラウドでは必要に応じて `OPENBLAS_NUM_THREADS=1`、`MPLCONFIGDIR=/tmp/mpl-config`、`XDG_CACHE_HOME=/tmp/analysis-cache` を設定する。実行環境のバージョンは `02_data/analysis/runtime.json`。

## 新しい取得時点で再取得する場合

e-StatのAPP IDを環境変数 `ESTAT_APP_ID` に設定する。キーをソース・引数・コミット・記録ファイルに書かない。

```sh
python 02_download_estat.py --raw-dir /path/to/new-empty-raw
python 02_dupor_hogan_jp.py --input-dir /path/to/new-empty-raw --download-only
```

同じ統計表の原JSONが既にあるフォルダへの上書き取得は拒否する。比較系列は `02_download_comparators.py` で取得できるが、`02_data/official` と `02_data/coverage` が空である必要がある。既存取得時点を保存した別チェックアウトで行う。分析・比較スクリプトの入力は同梱の `02_data/raw` に固定してあるため、新時点を使う場合はその配置も明示的に変更する。解析期間は2000年1月～2026年9月に固定。

原JSONは認証パラメータを除いた `STATISTICAL_DATA` 部分。CSVがなければmanifestとページハッシュを検証してJSONから復元する。欠損を補間して継続しない。

## 保存先

- `02_data/raw`：47支出分類・45価格分類のAPI原JSON、分類メタデータ、取得日時・条件・SHA-256、入力CSV。
- `02_data/official`：公式CPI総合（0001）と持家の帰属家賃除く総合（0163）。
- `02_data/coverage`：家計調査の消費支出総額（001100000）。
- `02_data/processed`：nominal・price・real・分類名付きmapping。
- `02_data/analysis`：18仕様の全期間・6時点・安定性・残差・予測誤差・同条件Shapiro・公式指数比較・既存Shapiro再現差・診断図。
- `02_data/us`：米国公表ページHTML・出所とハッシュ・公表表CSV。独自再推計ではない。

18仕様はラグ3/6/12、月ダミーなし、過去ウェイト、2019年末まで固定推計、ラグ3/6/12×判別閾値0.1/0.15/0.3、直近5/10/15年固定窓。判別不能は残差のいずれかが標準偏差×閾値以下。5成分に押し込めず当期・過去を追加する。短い固定窓と各時点のローリングは区別する。

実行成功だけで公表可とはしない。未完了項目と不安定性の判断を先に行う。
