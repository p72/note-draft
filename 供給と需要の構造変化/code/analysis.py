import pandas as pd, numpy as np, statsmodels.api as sm
S = "./"

# ---------- data ----------
qe = pd.read_csv(S + "qe_real.csv", parse_dates=["date"])
qe["q"] = qe["year"].astype(str) + "Q" + qe["quarter"].astype(str)
g = pd.read_excel(S + "dl/gap.xlsx", "data1", header=None).iloc[5:, :4]
g.columns = ["q", "gap", "kgap", "lgap"]
g["q"] = g["q"].str.replace(r"(\d{4})\.(\d)Q", r"\1Q\2", regex=True)
g = g.dropna(subset=["gap"])
d = qe.merge(g, on="q", how="left")
d["pot"] = d["GDP"] / (1 + d["gap"].astype(float) / 100)
d["lY"] = np.log(d["GDP"]); d["lP"] = np.log(d["pot"]); d["lC"] = np.log(d["HouseholdConsumptionExImputedRent"])
d["t"] = np.arange(len(d)); d = d.set_index("q")
d.to_csv(S + "merged.csv")
pg = pd.read_excel(S + "dl/gap.xlsx", "data2", header=None).iloc[5:, :6]
pg.columns = ["h", "pg", "tfp", "k", "hours", "emp"]
pg["fy"] = pg["h"].str[:6].astype(float)
pg = pg.set_index("fy").drop(columns="h").astype(float)

def idx(q): return d.index.get_loc(q)

def hac(y, X, lags=4):
    return sm.OLS(y, sm.add_constant(X)).fit(cov_type="HAC", cov_kwds={"maxlags": lags})

def tab(m):
    return pd.DataFrame({'coef':m.params,'se':m.bse,'p':m.pvalues}).round(3)

def broken_trend(col, breaks, start, end, extra=None):
    s = d.loc[start:end].copy(); t = s["t"]
    X = pd.DataFrame({"trend": t}, index=s.index)
    for name, q in breaks:
        T = d.loc[q, "t"]
        X[f"{name}_level"] = (t >= T).astype(float)
        X[f"{name}_slope"] = np.maximum(t - T, 0)
    if extra:
        for name, qs in extra.items():
            X[name] = s.index.isin(qs).astype(float)
    return hac(s[col] * 100, X), X

def supF(col, start, end, trim=0.15):
    """Quandt-Andrews: unknown single break in level+slope of a linear trend."""
    s = d.loc[start:end]; n = len(s); t = s["t"].values; y = s[col].values * 100
    X0 = sm.add_constant(t); r0 = sm.OLS(y, X0).fit().ssr
    out = []
    for i in range(int(n * trim), int(n * (1 - trim))):
        T = t[i]; X1 = np.column_stack([X0, (t >= T), np.maximum(t - T, 0)])
        r1 = sm.OLS(y, X1).fit().ssr
        out.append((s.index[i], ((r0 - r1) / 2) / (r1 / (n - 4))))
    f = pd.DataFrame(out, columns=["q", "F"]).set_index("q")
    return f

pd.set_option("display.width", 200)
print("=== A1. 潜在成長率(日銀, 半期) 期間平均と寄与度 ===")
per = {"1994-2007": (1994, 2007.2), "2008-2010": (2008, 2010.2), "2011-2013": (2011, 2013.2), "2014-2019": (2014, 2019.2), "2020-2026": (2020, 2026.2)}
print(pd.DataFrame({k: pg.loc[a:b].mean() for k, (a, b) in per.items()}).T.round(2))

print("\n=== A2. 潜在GDP(対数×100)の折れ線トレンド 1994Q1-2019Q4 (リーマン2008Q4, 震災2011Q1, HAC SE) ===")
covid_end = "2019Q4"
m, _ = broken_trend("lP", [("Lehman", "2008Q4"), ("Quake", "2011Q1")], "1994Q1", covid_end)
print(tab(m))
print("参考: 実質GDPでも同じ式")
m2, _ = broken_trend("lY", [("Lehman", "2008Q4"), ("Quake", "2011Q1")], "1994Q1", covid_end)
print(tab(m2))

print("\n=== A3. 未知の構造変化点探索 (supF) ===")
for col, a, b in [("lP", "1994Q1", "2019Q4"), ("lP", "2001Q1", "2019Q4")]:
    f = supF(col, a, b); print(col, a, b, "最大F at", f["F"].idxmax(), round(f["F"].max(), 1), " 上位:", f["F"].nlargest(5).index.tolist())

print("\n=== B1. 実質家計消費(除く帰属家賃) 折れ線トレンド 2002Q1-2019Q4 ===")
spikes = {"rush97": ["1997Q1"], "drop97": ["1997Q2"], "rush14": ["2014Q1"], "rush19": ["2019Q3"]}
for brks, lab in [([("Lehman", "2008Q4"), ("Quake", "2011Q1"), ("Tax14", "2014Q2")], "リーマン/震災/増税14"),
                  ([("Tax14", "2014Q2")], "増税14のみ")]:
    m, _ = broken_trend("lC", brks, "2002Q1", "2019Q3", {k: v for k, v in spikes.items() if k in ("rush14", "rush19")})
    print(lab); print(tab(m))

print("\n=== B2. 消費のsupF (2002Q1-2019Q3, 駆け込み期を除外せず) ===")
f = supF("lC", "2002Q1", "2019Q3"); print("最大F at", f["F"].idxmax(), round(f["F"].max(), 1), f["F"].nlargest(6).round(1).to_dict())
f2 = supF("lC", "2009Q3", "2019Q3"); print("リーマン後のみ: 最大F at", f2["F"].idxmax(), round(f2["F"].max(), 1))

print("\n=== B3. イベントスタディ: 増税直前8四半期のトレンドからの乖離(%) ===")
ev = {"1997年(3→5%)": "1997Q2", "2014年(5→8%)": "2014Q2", "2019年(8→10%)": "2019Q4"}
rows = {}
for lab, q in ev.items():
    i = idx(q); pre = d.iloc[i - 9:i - 1]  # 駆け込み期(直前1Q)を除く8四半期
    b = np.polyfit(pre["t"], pre["lC"], 1)
    dev = {h: 100 * (d.iloc[i + h]["lC"] - np.polyval(b, d.iloc[i + h]["t"])) for h in [0, 2, 4, 8, 12] if i + h < len(d)}
    rows[lab] = dev
print(pd.DataFrame(rows).T.round(1))

print("\n=== B4. 消費 vs GDP: 2014Q2以降 消費/GDP比の変化 ===")
d["Cshare"] = d["HouseholdConsumptionExImputedRent"] / d["GDP"] * 100
print(d.loc[["2007Q4", "2010Q4", "2013Q4", "2014Q3", "2016Q4", "2019Q2", "2020Q1", "2023Q4", "2026Q2"], ["Cshare", "gap"]].round(2))
print("\n需給ギャップ期間平均:", {k: round(d.loc[a:b, "gap"].astype(float).mean(), 2) for k, (a, b) in {"2009-2013": ("2009Q1", "2013Q4"), "2014Q2-2019Q3": ("2014Q2", "2019Q3"), "2017-2019Q3": ("2017Q1", "2019Q3")}.items()})
