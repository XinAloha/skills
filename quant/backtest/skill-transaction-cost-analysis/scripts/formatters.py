"""formatters.py — TCAReport 渲染为 JSON / 中文文本 / Markdown"""
from __future__ import annotations
import json

# 五项成本中文标签与展示顺序
COST_CN = {
    "timing": "择时",
    "impact": "冲击",
    "spread": "点差",
    "fees": "佣金税费",
    "slippage": "滑点",
}
COST_ORDER = ["timing", "impact", "spread", "fees", "slippage"]
SIDE_CN = {"buy": "买入", "sell": "卖出", "b": "买入", "s": "卖出"}


def _side_cn(s: str) -> str:
    return SIDE_CN.get(str(s).lower(), str(s))


def to_json(report: dict) -> str:
    return json.dumps(report, ensure_ascii=False, indent=2)


def _waterfall(breakdown: dict, total: float) -> list[str]:
    """把五项成本渲染成简易 ASCII 瀑布（按占总成本绝对值比例）。"""
    lines = []
    denom = sum(abs(v) for v in breakdown.values()) or 1.0
    for k in COST_ORDER:
        v = breakdown.get(k, 0.0)
        bar = "█" * max(0, int(round(abs(v) / denom * 24)))
        lines.append(f"    {COST_CN[k]:<4} {v:>8.2f} bps  {bar}")
    return lines


def to_text(report: dict) -> str:
    lines = []
    lines.append("=" * 60)
    lines.append("A股/跨市场 交易成本分析 (TCA) 报告")
    lines.append(f"生成时间: {report['generated_at']}   基准: {report['benchmark']}   后端: {report['backend']}")
    lines.append(f"成交笔数: {report['n_fills']}   总成交额: {report['notional']:,.0f}   "
                 f"佣金: {report['params']['commission_bps']}bps   冲击系数 k={report['params']['impact_coef']}")
    lines.append("=" * 60)

    # 总账
    total = report["total_cost_bps"]
    lines.append("")
    lines.append(f"▶ 总交易成本: {total:.2f} bps   （相对{report['benchmark']}基准，正值=对本方不利）")
    lines.append("  五项瀑布分解（成交额加权）:")
    lines += _waterfall(report["breakdown"], total)

    # 按方向
    if report.get("by_side"):
        lines.append("")
        lines.append("▶ 按买卖方向:")
        for row in report["by_side"]:
            lines.append(f"    {_side_cn(row['side']):<4} 成本 {row['total_cost_bps']:>7.2f} bps  "
                         f"额 {row['notional']:>14,.0f}  笔 {row['n_fills']}")

    # 按标的
    if report.get("by_symbol"):
        lines.append("")
        lines.append("▶ 按标的:")
        for row in report["by_symbol"]:
            bd = row["breakdown"]
            main = max(COST_ORDER, key=lambda k: abs(bd.get(k, 0.0)))
            lines.append(f"    {row['symbol']:<11} 成本 {row['total_cost_bps']:>7.2f} bps  "
                         f"额 {row['notional']:>14,.0f}  主因: {COST_CN[main]}({bd.get(main, 0):.1f})")

    # 逐笔明细（最多 12 笔）
    fills = report.get("fills", [])
    if fills:
        lines.append("")
        lines.append("▶ 逐笔明细（前 12 笔）:")
        lines.append(f"    {'标的':<11}{'方向':<4}{'时间':<18}{'价':>9}{'量':>10}"
                     f"{'总bps':>9}")
        for f in fills[:12]:
            lines.append(f"    {f['symbol']:<11}{_side_cn(f['side']):<4}{f['datetime'][:16]:<18}"
                         f"{f['price']:>9.3f}{f['qty']:>10.0f}{f['total_bps']:>9.2f}")

    # 结论
    if report.get("insights"):
        lines.append("")
        lines.append("▶ 结论与改进方向:")
        for ins in report["insights"]:
            lines.append(f"    - {ins}")

    # 降级
    if report.get("degraded"):
        lines.append("")
        lines.append("⚠️ 数据降级 / 近似说明:")
        for d in report["degraded"]:
            lines.append(f"    - {d}")

    lines.append("")
    lines.append("免责声明：冲击/点差为分钟级近似（无逐笔tick/盘口），结果用于研究与执行诊断。")
    lines.append("仅供研究参考，不构成投资建议。")
    return "\n".join(lines)


def to_markdown(report: dict) -> str:
    lines = [f"# 交易成本分析 (TCA) — {report['generated_at']}", ""]
    lines.append(f"基准 `{report['benchmark']}` · 后端 `{report['backend']}` · "
                 f"成交 {report['n_fills']} 笔 · 总额 {report['notional']:,.0f}")
    lines.append("")
    lines.append(f"**总交易成本：{report['total_cost_bps']:.2f} bps**")
    lines.append("")
    lines.append("| 成本项 | bps |")
    lines.append("|---|---|")
    for k in COST_ORDER:
        lines.append(f"| {COST_CN[k]} | {report['breakdown'].get(k, 0.0):.2f} |")
    lines.append(f"| **合计** | **{report['total_cost_bps']:.2f}** |")
    lines.append("")

    if report.get("by_symbol"):
        lines.append("## 按标的")
        lines.append("")
        lines.append("| 代码 | 成本 bps | 成交额 | 笔数 | 主要成本 |")
        lines.append("|---|---|---|---|---|")
        for row in report["by_symbol"]:
            bd = row["breakdown"]
            main = max(COST_ORDER, key=lambda k: abs(bd.get(k, 0.0)))
            lines.append(f"| {row['symbol']} | {row['total_cost_bps']:.2f} | "
                         f"{row['notional']:,.0f} | {row['n_fills']} | {COST_CN[main]} |")
        lines.append("")

    if report.get("insights"):
        lines.append("## 结论")
        lines.append("")
        for ins in report["insights"]:
            lines.append(f"- {ins}")
        lines.append("")

    if report.get("degraded"):
        lines.append("## 数据降级 / 近似")
        lines.append("")
        for d in report["degraded"]:
            lines.append(f"- {d}")
        lines.append("")

    lines.append("> 冲击/点差为分钟级近似（无逐笔tick/盘口）。仅供研究参考，不构成投资建议。")
    return "\n".join(lines)
