"""財務省「ブレーク・イーブン・インフレ率（BEI）の推移」PDFの折れ線（ベクターデータ）から日次・月次の値を読み取る。
使い方: python3 mof_bei_extract.py bei.pdf mof_bei_daily.csv mof_bei_monthly.csv
対象PDF: https://www.mof.go.jp/jgbs/topics/bond/10year_inflation-indexed/bei.pdf（2026/10/22現在版。座標は版ごとに確認が必要）
左パネル（2019年1月〜）の黒線=BEI、赤線=10年利付債、青線=10年物価連動債。
月次値は日次の中央値（端点の重複による外れ値を避けるため）。"""
import sys, numpy as np, pandas as pd, pymupdf as fitz
p = fitz.open(sys.argv[1])[0]
# 横軸：各年1月の目盛り線の座標（ページは回転しているため y 座標が時間軸）
jan_y = np.array([719.2, 670.2, 621.0, 571.9, 522.8, 473.7, 424.5, 375.4])
jan_d = pd.to_datetime([f"{y}-01-01" for y in range(2019, 2027)]).map(pd.Timestamp.toordinal).values
def to_date(y):
    o = np.interp(-y, -jan_y, jan_d)
    ext = y < jan_y[-1]
    sl = (jan_d[-1] - jan_d[-2]) / (jan_y[-1] - jan_y[-2])
    o[ext] = jan_d[-1] + (y[ext] - jan_y[-1]) * sl
    return o
def to_val(x):  # 縦軸：0.0% が x=342.5、0.5%pt あたり 31.85pt
    return (342.5 - x) / 31.85 * 0.5
out = {}
for name, col in {"bei": (0.0, 0.0, 0.0), "nom": (0.8, 0.0, 0.0), "real": (0.18, 0.46, 0.71)}.items():
    pts = []
    for d in p.get_drawings():
        c = d.get("color")
        if c and round(d.get("width") or 0, 2) == 2.25 and tuple(round(v, 2) for v in c) == col:
            for it in d["items"]:
                if it[0] == "l":
                    for q in (it[1], it[2]):
                        if 335.5 <= q.y <= 719.5:
                            pts.append((min(q.y, 719.2), q.x))
    a = np.array(pts)
    s = pd.Series(to_val(a[:, 1]), index=[pd.Timestamp.fromordinal(int(round(o))) for o in to_date(a[:, 0])])
    out[name] = s.groupby(level=0).mean().sort_index()
df = pd.DataFrame(out); df.to_csv(sys.argv[2])
df.resample("MS").median().to_csv(sys.argv[3])
