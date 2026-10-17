"""毎月勤労統計調査 長期時系列表（全国調査・事業所規模5人以上・就業形態計）を e-Stat からダウンロードする。

statInfId は毎月の更新で変わることがある。失敗したら e-Stat の
「毎月勤労統計調査 全国調査 長期時系列表」のページで取り直す。
"""
import pathlib, time, urllib.request

FILES = {
    "real":    "000032189738",  # 25-1 実質賃金（現金給与総額）指数（５人以上）
    "hours":   "000032189742",  # 29 総実労働時間指数（５人以上）
    "nominal": "000032189720",  # 7 現金給与総額指数（５人以上）
}
URL = "https://www.e-stat.go.jp/stat-search/file-download?&statInfId={}&fileKind=4"
OUT = pathlib.Path(__file__).parent / "raw"
OUT.mkdir(exist_ok=True)

for name, sid in FILES.items():
    req = urllib.request.Request(URL.format(sid), headers={"User-Agent": "Mozilla/5.0"})
    data = urllib.request.urlopen(req, timeout=60).read()
    (OUT / f"{name}.xls").write_bytes(data)
    print(name, len(data), "bytes")
    time.sleep(3)
