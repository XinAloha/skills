"""端到端示例：生成一个 3 行业 × 20 只股票 × 20 个交易日的合成组合，
跑完整归因流程（行业 + 因子）并输出报告到 examples/output/。

python examples/run_example.py
"""

import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))

from attribution import main as attribution_main

RNG = np.random.default_rng(7)


def make_data(data_dir):
    os.makedirs(data_dir, exist_ok=True)
    symbols = [f"{600000 + i}.SH" for i in range(20)]
    sectors = ["银行", "白酒", "半导体"]
    sector_map = pd.DataFrame(
        {"symbol": symbols, "sector": [sectors[i % 3] for i in range(20)]}
    )
    dates = pd.date_range("2026-06-01", periods=20, freq="B").strftime("%Y-%m-%d")

    pw_rows, bw_rows, ret_rows, expo_rows = [], [], [], []
    for d in dates:
        # 基准：等权；组合：故意超配半导体、低配银行，行业内再做主动选股
        bw = np.full(20, 1 / 20)
        tilt = np.array([0.7 if s == "银行" else 1.4 if s == "半导体" else 1.0
                         for s in sector_map["sector"]])
        pw = bw * tilt * (1 + RNG.normal(0, 0.15, 20))
        pw = np.clip(pw, 0, None)
        pw /= pw.sum()

        mom = RNG.normal(0, 1, 20)
        value = RNG.normal(0, 1, 20)
        ret = 0.0005 + 0.004 * mom - 0.002 * value + RNG.normal(0, 0.01, 20)

        for i, s in enumerate(symbols):
            pw_rows.append({"date": d, "symbol": s, "weight": pw[i]})
            bw_rows.append({"date": d, "symbol": s, "weight": bw[i]})
            ret_rows.append({"date": d, "symbol": s, "ret": ret[i]})
            expo_rows.append({"date": d, "symbol": s,
                              "mom": mom[i], "value": value[i]})

    pd.DataFrame(pw_rows).to_csv(f"{data_dir}/portfolio.csv", index=False)
    pd.DataFrame(bw_rows).to_csv(f"{data_dir}/benchmark.csv", index=False)
    pd.DataFrame(ret_rows).to_csv(f"{data_dir}/returns.csv", index=False)
    pd.DataFrame(expo_rows).to_csv(f"{data_dir}/exposures.csv", index=False)
    sector_map.to_csv(f"{data_dir}/sectors.csv", index=False)


if __name__ == "__main__":
    data = os.path.join(HERE, "data")
    out = os.path.join(HERE, "output")
    make_data(data)
    sys.exit(attribution_main([
        "--portfolio", f"{data}/portfolio.csv",
        "--benchmark", f"{data}/benchmark.csv",
        "--returns", f"{data}/returns.csv",
        "--sectors", f"{data}/sectors.csv",
        "--exposures", f"{data}/exposures.csv",
        "--out", out,
    ]))
