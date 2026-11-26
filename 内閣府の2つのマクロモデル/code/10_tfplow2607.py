"""2026年7月の中長期試算の「潜在成長率低下ケース」（本文 図20）を、このモデルで解き直す.

資料: https://www5.cao.go.jp/keizai-shimon/kaigi/minutes/2026/0730shiryo_02-2.pdf （４．リスク・不確実性、図20）
資料の設定: 現状投影ケースをベースに、その他の外生変数は変えずに、2028年度以降ＴＦＰ上昇率を継続的に0.5%pt程度下げる。
資料は主要乗数表による感応度分析。ここでは現状投影ケースの再現経路（projection2607.py の proj_state_2607_gen.pkl、
記事08の「試算の姿」。毎年度実質10兆円の追加財政支出込み）の誤差項と外生変数をそのまま使い、対数ＴＦＰ（M_TFP）を
2028年度から毎年0.005ずつ下げて解き直す（chuuchouki.py の図19の再現と同じ方法）。
- 実質の政府消費・公的固定資本形成は再現経路のまま（chuuchouki.hold_real_g。追加財政支出の公需も実質で同じ）。
  --nominal を付けると、歳出の調整項を動かさない（名目の予算の置き方をそのまま使う）。
- 金利（長期・短期）、税収、利払費、社会保障などはモデルの式で動く。
出力: output/tfplow2607_gen{_nominal}.csv（item, year, base, low）、output/parts/proj_state_2607_gen_tfplow{_nominal}.pkl
"""
from __future__ import annotations

import os

os.environ.setdefault("CAO_LAST_VINTAGE", "2040")

import copy  # noqa: E402
import pickle  # noqa: E402
from pathlib import Path  # noqa: E402

import pandas as pd  # noqa: E402

import projection2607 as Q  # noqa: E402
from chuuchouki import hold_real_g  # noqa: E402
from hire2607 import solve  # noqa: E402
from solver import Solver  # noqa: E402
from spec import build, compile_eq  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
START = 2028
YEARS = list(range(START, 2041))
DTFP = 0.005            # 対数ＴＦＰの1年あたりの下げ幅（上昇率 −0.5%pt）


def run(case: str = "gen", nominal: bool = False) -> pd.DataFrame:
    Q.configure()
    m = build("calibrated", "port")
    m.eqs.append(compile_eq("Z_EXPX35E", "Z_EXPX35E=Z_EXPX35+Z_ADJEXPX35E"))   # projection.py と同じ
    m.meta["Z_EXPX35E"] = {"label": "（追加: その他一般歳出の SNA 用）", "block": "fiscal", "estimated": False}
    st = pickle.loads(Q.state_path(case).read_bytes())
    base, af = st["data"], copy.deepcopy(st["af"])
    af.setdefault("Z_EXPX35E", {})
    data = copy.deepcopy(base)
    for k, t in enumerate(YEARS):
        data["M_TFP"][t] = base["M_TFP"][t] - DTFP * (k + 1)
    s = Solver(m, data, af)
    for t in YEARS:
        solve(s, t)
        if not nominal:
            hold_real_g(s, "tfp", t, base, set())
        d = lambda v: data[v][t] - base[v][t]
        print(f"{case} {t}: 潜在成長率 {(data['M_GDPP'][t] / data['M_GDPP'][t - 1] - base['M_GDPP'][t] / base['M_GDPP'][t - 1]) * 100:+.2f}pt"
              f"  実質GDP {(data['M_GDP'][t] / base['M_GDP'][t] - 1) * 100:+.2f}%  名目GDP {d('M_GDPV') / 1000:+.1f}兆円"
              f"  長期金利 {d('M_RGB'):+.2f}  PB比 {d('M_PBGAGDPV'):+.2f}  残高比 {d('Z_DEBTAGDP'):+.2f}", flush=True)
    tag = f"{case}_tfplow" + ("_nominal" if nominal else "")
    (ROOT / "output" / "parts" / f"proj_state_2607_{tag}.pkl").write_bytes(pickle.dumps({"data": data, "af": af}))
    rows = []
    for t in range(2024, 2041):
        vb, vl = Q.item_values(base, t), Q.item_values(data, t)
        for item in Q.ITEMS + ["国の税収", "国のPB対象経費", "純利払費", "短期金利"]:
            rows.append({"item": item, "year": t, "base": vb[item], "low": vl[item]})
        rows.append({"item": "実質GDP（水準比、%）", "year": t, "base": 0.0, "low": (data["M_GDP"][t] / base["M_GDP"][t] - 1) * 100})
    df = pd.DataFrame(rows)
    out = ROOT / "output" / f"tfplow2607_{tag}.csv"
    df.to_csv(out, index=False, encoding="utf-8-sig")
    print(f"→ {out}")
    return df


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", default="gen", choices=Q.CASES)
    ap.add_argument("--nominal", action="store_true", help="実質の公需を固定せず、歳出の調整項を再現経路のままにする")
    a = ap.parse_args()
    run(a.case, a.nominal)
