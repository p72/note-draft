# 日銀BOX3との照合（記事02の図6・図7）

- `crop_boj.py`：日本銀行「経済・物価情勢の展望（2026年10月）」全文PDF（https://www.boj.or.jp/mopo/outlook/gor2610b.pdf ）の48ページから図表B3-2を切り出し、`../../02_boj_b3-2.png` に保存する。トリミングのみで加工はしない（記事では出所を明記して引用）。
- `age_real.py`：e-Stat API で総務省「家計調査」月次・二人以上の世帯・世帯主の年齢階級別（statsDataId 0002070010、消費支出 cat01=059、世帯人員 003）と、CPI「持家の帰属家賃を除く総合」（0003427113、cat01=0163）を取得済みの `kakei_m_age.csv`・`cpi_ex_rent_m.csv` から、1人当たり実質消費を年齢グループ別に作り、四半期平均をSTL（period=4, robust）で季節調整して `age_real_idx.csv`（2021/1Q＝100）を出力する。ESTAT_API_SKILL_DIR は estat-api スキルの置き場所（`read_stats_csv` のみ使用）。
- `chart_age_real.py`：`../../02_chart_age_kakei.png` を作成。

年齢グループは世帯主年齢5歳階級（34歳以下は1区分）の単純平均。2026/3Qは7〜8月の平均。
