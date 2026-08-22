#!/usr/bin/env python3
"""run_demo.py — 无需凭证的离线演示。

强制使用内置样本分钟线（examples/sample_data/get_stock_min.json）与样本成交
（examples/sample_data/fills.csv），对一批"茅台分批买入 + 平安银行卖出"的成交
做交易成本分析，展示 implementation shortfall 五项分解。

真实使用见 README（配置 panda_data SDK 后去掉 prefer="sample"）。
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from tca_report import build_report  # noqa: E402
import formatters                    # noqa: E402

FILLS = ROOT / "examples" / "sample_data" / "fills.csv"


def main():
    report = build_report(
        str(FILLS),
        benchmark="vwap",
        commission_bps=2.5,
        impact_coef=0.1,
        frequency="5m",
        prefer="sample",
    )
    print(formatters.to_text(report))
    print("\n" + "-" * 60)
    print("Markdown 版：\n")
    print(formatters.to_markdown(report))


if __name__ == "__main__":
    main()
