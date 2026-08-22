"""
Demo: build a structural risk model on a synthetic A-share universe and attribute
the risk of an equal-weight portfolio into factor vs specific, factor by factor.

    python examples/run_demo.py

Fully offline (no credentials needed).
"""
import sys
from pathlib import Path

import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.append(str(Path(__file__).resolve().parents[1] / "scripts"))

from data_source import get_return_panel, get_market_cap, get_industry  # noqa: E402
from risk_model import build_risk_model, summarize                       # noqa: E402
from risk_attribution import decompose_risk, render_attribution          # noqa: E402

# A structural cross-sectional model needs many more names than factors.
universe = [f"{600000 + i:06d}.SH" if i % 2 else f"{i + 1:06d}.SZ" for i in range(40)]
rets = get_return_panel(universe, "20210101", "20231231")
cap = get_market_cap(universe, "20210101", "20231231")
ind = get_industry(universe)

print("构建 Barra 式结构化风险模型 ...")
model = build_risk_model(rets, cap, ind)
s = summarize(model)
print(f"  回归期数: {s['n_periods']}  因子数: {s['n_factors']}")
print(f"  因子: {', '.join(s['factors'])}")

print("\n年化因子波动率:")
for k, v in s["annualised_factor_vol"].items():
    print(f"  {k:<14} {v:.4f}")

# Attribute the risk of an equal-weight book.
weights = pd.Series(1.0 / len(universe), index=model["exposures"].index)
attr = decompose_risk(weights, model["exposures"], model["factor_cov"], model["specific_var"])
print("\n等权组合的风险归因:")
print(render_attribution(attr))
print("\n说明: 因子风险 + 特异风险 = 组合总方差; 各因子 %var 之和 = 因子风险占比。")
