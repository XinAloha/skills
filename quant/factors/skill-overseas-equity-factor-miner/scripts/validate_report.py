#!/usr/bin/env python3
"""Validate an overseas (HK/US) cross-sectional factor-mining Markdown report.

Stdlib-only, deterministic. Checks that a produced report has the required sections
plus source / date / market labels and the non-investment-advice disclaimer. Exits
non-zero on a bad report so it can gate a run.

Usage:
    python scripts/validate_report.py <report.md>

Exit codes: 0 = OK, 1 = report has issues, 2 = report file not found.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


# (key, regex, human message) — headings tolerate an optional "N. " numeric prefix.
REQUIRED_SECTIONS = [
    ("title", r"^#\s+.*(因子|factor|alpha)", "一级标题需要标明因子挖掘报告（含 因子/factor/alpha）"),
    ("summary", r"^##\s*(?:\d+[.、]\s*)?摘要", "缺少摘要章节"),
    ("candidates", r"^##\s*(?:\d+[.、]\s*)?候选因子", "缺少候选因子章节"),
    ("caliber", r"^##\s*(?:\d+[.、]\s*)?(计算口径|口径)", "缺少计算口径章节（点位/同业中位/报告口径）"),
    ("validation", r"^##\s*(?:\d+[.、]\s*)?(有效性检验|检验|有效性)", "缺少有效性检验章节（IC/衰减/换手）"),
    ("ranking", r"^##\s*(?:\d+[.、]\s*)?排名", "缺少排名章节"),
    ("risk", r"^##\s*(?:\d+[.、]\s*)?(风险|口径提示|风险与口径)", "缺少风险与口径提示章节"),
    ("data_notes", r"^##\s*(?:\d+[.、]\s*)?数据说明", "缺少数据说明章节"),
]


def validate(text: str) -> list[str]:
    issues: list[str] = []

    if len(text.strip()) < 500:
        issues.append("报告内容过短，可能不是完整的因子挖掘报告")

    for _key, pattern, message in REQUIRED_SECTIONS:
        if not re.search(pattern, text, flags=re.MULTILINE | re.IGNORECASE):
            issues.append(message)

    # Validation metrics must actually appear.
    if not re.search(r"\bIC\b|信息系数|Spearman|秩相关", text, flags=re.IGNORECASE):
        issues.append("缺少 IC / 秩相关（rank IC）有效性指标")
    if not re.search(r"衰减|decay", text, flags=re.IGNORECASE):
        issues.append("缺少 IC 衰减（decay）说明")
    if not re.search(r"换手|turnover", text, flags=re.IGNORECASE):
        issues.append("缺少换手率（turnover）说明")

    # Market must be labeled and singular (HK or US), not mixed A-share.
    if not re.search(r"港股|美股|\bHK\b|\bUS\b|Hong Kong", text, flags=re.IGNORECASE):
        issues.append("缺少市场标注（港股 HK / 美股 US）")

    # Data source / interface labeling.
    if not re.search(
        r"数据来源|来源接口|使用接口|Pandadata|get_hk_daily|get_us_daily|"
        r"get_stock_operating_indicator|get_stock_operating_metric|"
        r"get_stock_mktfin_indicator|get_stock_mktfin_metric|get_trade_cal",
        text,
    ):
        issues.append("缺少数据来源或来源接口说明")

    # Point-in-time / no look-ahead discipline.
    if not re.search(r"点位|point-in-time|时点|前视|look-?ahead|存续偏差|survivorship", text, flags=re.IGNORECASE):
        issues.append("缺少点位/时点（point-in-time，防前视/存活偏差）口径说明")

    # Peer-group normalization for fundamental factors.
    if not re.search(r"同业|行业中位|板块中位|median|分位|z-?score|percentile", text, flags=re.IGNORECASE):
        issues.append("缺少同业组标尺/中位归一说明（基本面因子须在同业组内归一）")

    # Sample window / rebalance dates labeling.
    if not re.search(r"窗口|样本期|调仓|再平衡|财年|financial_year|截止|rebalance", text, flags=re.IGNORECASE):
        issues.append("缺少样本期/调仓日期窗口说明")

    if not re.search(r"不构成任何投资建议", text):
        issues.append("缺少免责声明：本报告基于公开数据与规则化分析生成，仅供研究参考，不构成任何投资建议。")

    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path, help="Path to the Markdown report")
    args = parser.parse_args()

    try:
        text = args.report.read_text(encoding="utf-8-sig")
    except FileNotFoundError:
        print(f"ERROR: report not found: {args.report}", file=sys.stderr)
        return 2

    issues = validate(text)
    if issues:
        print("FAIL")
        for issue in issues:
            print(f"- {issue}")
        return 1

    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
