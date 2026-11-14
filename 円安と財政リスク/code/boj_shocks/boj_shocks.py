"""一方井・川本・桜（2024、日本銀行WP 24-J-26）の設計を参考に、日本銀行の金融政策決定会合の日の
金利ショックと為替への直接ショックを取り出し、ローカル・プロジェクション（LP）でドル円の反応を推計する。

論文の仕様（本文で確認できたもの）
- 金利ショック ε_y,t = −(Δi_t^JP の各年限) × d_t（d_t は政策決定日に1。日本の金利が下がるとプラス）
  年限は3か月物OIS、2年・10年・30年国債。決定日の前日差（日本の終値）
- 為替への直接ショック ε_s,t = x_t × d_t。x_t は次の式の残差
  Δs(9→17)_t = α + B'ΔY_t + Γ'ΔY_{t−1} + γ Δs(9→17)_{t−1} + u_t、ΔY は日米金利差（米−日）の変化
- LP：s_{t+h} − s_{t−1} = α_h + B_h'ΔY_t + β_h x_t + Γ_h'ΔY_{t−1} + γ_h Δs_{t−1} + u、h=0..30、Newey-West
  反応 (A) = B_h' ε_y、(B) = B_h' ε_y + β_h ε_s
- 期間：2002年4月〜2023年12月。9時・17時のドル円は日本銀行の公表値

本稿の置き換え・仮定
- 3か月物OISの代わりに1年物（日本：財務省の国債1年、米国：GSWのゼロクーポン1年）。米国の2・10・30年もGSW
- LPの s は東京17時のドル円（対数×100）。Δs_{t−1} は前日の17時→17時の変化
- 会合日：日本銀行「決定事項」一覧の、各年の会合の公表文（k+日付のファイル）の日（2002〜2026年、299日）
- 各会合の反応：論文と同じく h=0〜30 を表示
- 期間への寄与（本稿の拡張）：LPを h=0〜120 まで推計し、各会合の反応 R(h)（会合前は0）について、
  期末までの R(期末−会合) と期首前日までの R(期首前日−会合) の差を、期首前の会合も含めて合計する。
  120営業日より先の反応は120日の値で一定と仮定する。区間は20営業日のブロック・ブートストラップ（200回）
"""
import sys
import numpy as np, pandas as pd, statsmodels.api as sm

END = "2023-12-31"
for a in sys.argv[1:]:
    k, v = a.split("="); globals()[k] = v
H = 30
HL = 120
NB = 200

fx = pd.read_csv("usdjpy_tokyo_09_17.csv", index_col=0, parse_dates=True)
jp = pd.read_csv("jgb_1_2_10_30.csv", index_col=0, parse_dates=True)
us = pd.read_csv("gsw_us_1_2_10_30.csv", index_col=0, parse_dates=True)
# 東京の営業日（9時・17時のドル円と日本国債がそろう日）
d = fx.join(jp, how="inner").dropna()
# 米国の金利：その日のニューヨーク終値（論文と同じく日次終値の前日差。米国の休日は直近の値）
# 米国だけが休みの日はファイルに空欄の行があるため、空欄を除いてから直近の値を対応させる
d = d.join(us.dropna().reindex(d.index, method="ffill"))
d["s"] = np.log(d.fx17) * 100
d["ds917"] = (np.log(d.fx17) - np.log(d.fx09)) * 100
M = ["1", "2", "10", "30"]
for m in M:
    d[f"dY{m}"] = (d[f"us{m}"] - d[f"jp{m}"]).diff()
    d[f"dJP{m}"] = d[f"jp{m}"].diff()
d["ds"] = d.s.diff()
Y = [f"dY{m}" for m in M]
for c in Y + ["ds917", "ds"]:
    d[f"{c}_l1"] = d[c].shift(1)
d = d.dropna(subset=Y + [f"{c}_l1" for c in Y] + ["ds917_l1", "ds_l1"])

est = d.loc["2002-04-01":END]
# 直接ショックのための予測式
Xp = sm.add_constant(est[Y + [f"{c}_l1" for c in Y] + ["ds917_l1"]])
mp = sm.OLS(est.ds917, Xp).fit(cov_type="HAC", cov_kwds={"maxlags": 5})
d["x"] = d.ds917 - sm.add_constant(d[Y + [f"{c}_l1" for c in Y] + ["ds917_l1"]]) @ mp.params

# LP
ZC = Y + ["x"] + [f"{c}_l1" for c in Y] + ["ds_l1"]
def lp(dd, Hmax):
    out = {}
    base = dd.loc["2002-04-01":END]
    for h in range(Hmax + 1):
        yv = (dd.s.shift(-h) - dd.s.shift(1)).loc[base.index]
        sub = pd.concat([yv.rename("y"), sm.add_constant(base[ZC])], axis=1).dropna()
        out[h] = np.linalg.lstsq(sub.drop(columns="y").values, sub.y.values, rcond=None)[0]
    return pd.DataFrame(out, index=["const"] + ZC).T
coef = lp(d, max(H, HL))
mpm = pd.read_csv("boj_mpm_dates.csv", parse_dates=["date"])
idx = d.index
rows = []
for _, e in mpm.iterrows():
    if e.date not in idx: continue
    t = idx.get_loc(e.date)
    epsy = -d.iloc[t][[f"dJP{m}" for m in M]].values.astype(float)     # 日本の金利の低下がプラス
    epss = d.iloc[t].x
    A = np.array([coef.loc[h, Y].values @ epsy for h in range(HL + 1)])
    Bt = A + np.array([coef.loc[h, "x"] * epss for h in range(HL + 1)])
    rows.append({"date": e.date.date(), "title": e.title, "ds917": d.iloc[t].ds917, "x_direct": epss,
                 **{f"dJP{m}_bp": d.iloc[t][f"dJP{m}"] * 100 for m in M},
                 "A_h0": A[0], "B_h0": Bt[0], "A_h5": A[5], "B_h5": Bt[5], "A_h30": A[30], "B_h30": Bt[30],
                 "_A": A, "_B": Bt, "_pos": t})
ev = pd.DataFrame(rows)

def contrib(ev_, a, z, key="_B"):
    """期末と期首前日の差で見た、会合ショックの期間寄与（期首前の会合の持ち越しを含む）"""
    b0 = idx.searchsorted(pd.Timestamp(a)) - 1; e = idx.searchsorted(pd.Timestamp(z), side="right") - 1
    tot = 0.0
    for _, r in ev_.iterrows():
        t = r._pos
        if t > e: continue
        R = r[key]
        re_ = R[min(e - t, HL)]; rb = R[min(b0 - t, HL)] if b0 >= t else 0.0
        tot += re_ - rb
    return tot

def window(a, z):
    b0 = idx.searchsorted(pd.Timestamp(a)) - 1; e = idx.searchsorted(pd.Timestamp(z), side="right") - 1
    w = ev[(pd.to_datetime(ev.date) >= a) & (pd.to_datetime(ev.date) <= z)]
    cA = contrib(ev, a, z, "_A"); cB = contrib(ev, a, z, "_B")
    return {"window": f"{a}..{z}", "meetings_in_window": len(w), "fx_change": d.s.iloc[e] - d.s.iloc[b0],
            "rate_shock_A": cA, "total_B": cB, "direct": cB - cA}

def bootstrap(windows, nb=NB, block=20, seed=0):
    """日をブロックで引き直して予測式とLPを再推計し、実際のショックに当てはめる"""
    rng = np.random.default_rng(seed); base = d.loc["2002-04-01":END]
    n = len(base); nblk = int(np.ceil(n / block)); res = {w: [] for w in windows}
    Xcols = Y + [f"{c}_l1" for c in Y] + ["ds917_l1"]
    lead = {h: (d.s.shift(-h) - d.s.shift(1)).loc[base.index].values for h in range(HL + 1)}
    for b in range(nb):
        st = rng.integers(0, n - block, nblk); pos = np.concatenate([np.arange(s0, s0 + block) for s0 in st])[:n]
        bb = base.iloc[pos]
        bp = np.linalg.lstsq(sm.add_constant(bb[Xcols]).values, bb.ds917.values, rcond=None)[0]
        xb = d.ds917 - sm.add_constant(d[Xcols]).values @ bp
        Zall = sm.add_constant(d[ZC].assign(x=xb)).loc[base.index].values[pos]
        cf = []
        for h in range(HL + 1):
            yv = lead[h][pos]; ok = ~np.isnan(yv) & ~np.isnan(Zall).any(1)
            cf.append(np.linalg.lstsq(Zall[ok], yv[ok], rcond=None)[0])
        cf = pd.DataFrame(cf, columns=["const"] + ZC)
        rows_ = []
        for _, e in ev.iterrows():
            t = e._pos; epsy = -d.iloc[t][[f"dJP{m}" for m in M]].values.astype(float); epss = xb.iloc[t]
            A_ = cf[Y].values @ epsy; rows_.append({"_pos": t, "_A": A_, "_B": A_ + cf["x"].values * epss})
        eb = pd.DataFrame(rows_)
        for (a, z) in windows: res[(a, z)].append((contrib(eb, a, z, "_A"), contrib(eb, a, z, "_B")))
    return res

if __name__ == "__main__":
    tag = END[:4]
    pd.set_option("display.width", 250)
    print("予測式 R2", round(mp.rsquared, 3), "n", int(mp.nobs))
    print(coef.loc[[0, 5, 30], Y + ["x"]].round(3))
    PAPER = ["2003-04-30", "2003-05-20", "2008-10-31", "2008-12-19", "2009-12-01", "2009-12-18", "2010-10-05",
             "2012-02-14", "2013-04-04", "2014-10-31", "2016-01-29", "2016-09-21", "2018-07-31", "2022-04-28"]
    p = ev[ev.date.astype(str).isin(PAPER)]
    cols = ["date", "ds917", "x_direct", "dJP1_bp", "dJP2_bp", "dJP10_bp", "dJP30_bp", "A_h0", "B_h0", "A_h30", "B_h30"]
    print(p[cols].round(2).to_string())
    ev.drop(columns=["_A", "_B", "_pos"]).round(4).to_csv(f"boj_events_{tag}.csv", index=False)
    coef.round(5).to_csv(f"boj_lp_coef_{tag}.csv")
    if END > "2025":
        W = [("2021-01-01", "2023-09-15"), ("2023-09-16", "2025-09-30"), ("2025-10-01", "2026-02-27"),
             ("2026-03-01", "2026-11-05"), ("2025-10-01", "2026-11-05")]
        wt = pd.DataFrame([window(a, z) for a, z in W])
        bs = bootstrap(W)
        for i, w in enumerate(W):
            arr = np.array(bs[w])
            wt.loc[i, "total_B_p5"], wt.loc[i, "total_B_p95"] = np.percentile(arr[:, 1], [5, 95])
            wt.loc[i, "rate_A_p5"], wt.loc[i, "rate_A_p95"] = np.percentile(arr[:, 0], [5, 95])
        print(wt.round(2).to_string()); wt.round(3).to_csv(f"boj_windows_{tag}.csv", index=False)
        print(ev[pd.to_datetime(ev.date) >= "2024-01-01"][cols].round(2).to_string())
