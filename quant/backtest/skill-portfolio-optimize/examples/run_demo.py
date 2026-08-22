"""
Demo: build the same universe under five objectives and show how the weights,
risk concentration and exposures differ. Then demonstrate sector-neutral and
turnover-limited construction.

    python examples/run_demo.py

Fully synthetic / offline (no credentials needed).
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Windows consoles default to a non-UTF-8 codec; make Chinese output safe.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.append(str(Path(__file__).resolve().parents[1] / "scripts"))

from covariance import estimate_cov          # noqa: E402
from optimize_report import build_portfolio  # noqa: E402
from data_source import get_return_panel      # noqa: E402

universe = ["000001.SZ", "600000.SH", "000333.SZ", "600519.SH",
            "000651.SZ", "601318.SH", "600036.SH", "000858.SZ",
            "002415.SZ", "600276.SH"]
rets = get_return_panel(universe, "20220101", "20231231")
cov = estimate_cov(rets)
mu = rets.mean() * 252                         # toy expected returns
sectors = pd.Series(["金融", "金融", "家电", "白酒", "家电",
                     "金融", "金融", "白酒", "科技", "医药"], index=universe)

print("\n### 五种目标函数对比 ###")
for obj in ["min_variance", "max_sharpe", "risk_parity", "max_diversification", "mean_variance"]:
    out = build_portfolio(obj, cov, mu=mu, long_only=True, weight_cap=0.30)
    d = out["diagnostics"]
    print(f"{obj:20s} vol={d['portfolio_volatility_annual']:.3f} "
          f"holdings={d['n_holdings']:2d} maxw={d['max_weight']:.3f}")

print("\n### 行业中性 + 个股上限 5% + 换手约束 (long-short) ###")
# 美元中性来自行业中性约束本身：每个行业净敞口=0 ⇒ 组合总净敞口=0。
# （若没有行业约束，多空 mean_variance 用 net_exposure=0.0 做美元中性锚定。）
w_prev = pd.Series(1.0 / len(universe), index=universe)
out = build_portfolio(
    "mean_variance", cov, mu=mu,
    long_only=False, full_investment=False,
    weight_cap=0.05, sectors=sectors,          # sector-neutral ⇒ dollar-neutral
    w_prev=w_prev, turnover_limit=1.5, risk_aversion=8.0)
print(out["report_text"])

print("\n### 纯美元中性多空 (无行业约束, 用 net_exposure=0 锚定) ###")
out2 = build_portfolio(
    "mean_variance", cov, mu=mu,
    long_only=False, full_investment=False,
    net_exposure=0.0,                          # explicit dollar-neutral anchor
    weight_cap=0.10, risk_aversion=8.0)
d2 = out2["diagnostics"]
print(f"  net={d2['sum_weights']:+.4f}  gross={d2['gross_exposure']:.4f}  vol={d2['portfolio_volatility_annual']}")
