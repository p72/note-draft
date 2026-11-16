import sys, numpy as np, pandas as pd
sys.path.insert(0, "/home/hatch/workspace/custom-skills/boj-api")
sys.path.insert(0, "/home/hatch/workspace/custom-skills/fred-data")
from scripts.boj_api import get_series
from scripts.fred_data import get_fred

codes = {"CA":"BPBP6JYNCB","REINV_C":"BPBP6JYNPIC2112","REINV_D":"BPBP6JYNPID2112",
         "PORT_C":"BPBP6JYNPIC22","PORT_N":"BPBP6JYNPIN22","FDI_NET":"BPBP6JYNFB1"}
bop = get_series("BP01", list(codes.values()), start_date="199601", columns="code")
bop.columns = [k for k,v in codes.items() if v in bop.columns]
print(bop.shape, bop.index.min(), bop.index.max())
bop.to_csv("/home/hatch/workspace/bei-replication/bop_monthly.csv")

reinv_net = bop["REINV_C"] - bop["REINV_D"]
fdi_fx = bop["FDI_NET"] - reinv_net
# Variant A: credit-based adjustments (literal reading)
cafx_a = bop["CA"] - bop["REINV_C"] - bop["PORT_C"]/2
# Variant B: net-based adjustments
cafx_b = bop["CA"] - reinv_net - bop["PORT_N"]/2
flow_a = cafx_a - fdi_fx
flow_b = cafx_b - fdi_fx
ann = pd.DataFrame({"A": flow_a, "B": flow_b}).resample("A").sum()/1e4  # 兆円
print("\nAnnual real-demand flow (trillion yen):")
print(ann.loc["2000":"2025"].round(1).to_string())

gdp_q = get_fred("JPNNGDP", start="1995-01-01")  # billions yen, SAAR
gdp_q_oku = gdp_q * 2.5  # -> quarterly GDP in 億円 (SAAR/4 * 10)
cum = pd.DataFrame({"cumA": flow_a.cumsum(), "cumB": flow_b.cumsum()})
q = cum.resample("Q").last()
q.index = q.index.to_period("Q")
g = pd.Series(gdp_q_oku.values, index=gdp_q.index.to_period("Q"), name="gdp")
out = q.join(g, how="inner")
out["jitsuju_A"] = out["cumA"]/out["gdp"]
out["jitsuju_B"] = out["cumB"]/out["gdp"]
out.to_csv("/home/hatch/workspace/bei-replication/jitsuju_quarterly.csv")
print("\nQuarterly real-demand (cum/GDP):")
print(out.loc["2015Q1":"2026Q2", ["cumA","cumB","jitsuju_A","jitsuju_B"]].head(4).round(3).to_string())
print(out.loc["2015Q1":"2026Q2", ["jitsuju_A","jitsuju_B"]].tail(4).round(3).to_string())
print("2011Q4:", out.loc["2011Q4", ["jitsuju_A","jitsuju_B"]].round(3).to_dict(), " 2021Q4:", out.loc["2021Q4", ["jitsuju_A","jitsuju_B"]].round(3).to_dict())
print("BOP source: BOJ Time-Series Data Search API, db BP01")
