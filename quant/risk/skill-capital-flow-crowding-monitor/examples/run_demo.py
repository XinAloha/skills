#!/usr/bin/env python3
"""run_demo.py — 跨市场资金面/拥挤监测离线演示（无需凭证，强制内置样本）。

样本设计（两组对比案例）：
  - 600519.SH 贵州茅台 → **三源共识买入**：融资余额稳步净流入 + 北向持股比例稳升
    + 大宗机构专用溢价承接，三源同向且拥挤度处中位区间 → 最优形态。
  - 000858.SZ 五粮液   → **高拥挤预警**：融资余额末段暴力加杠杆冲至历史极高分位，
    北向同步冲高、大宗机构溢价大额承接 → 共识做多但已高度拥挤，反转风险最高。

无凭证运行必定 exit 0。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

try:
    from capital_report import build_report  # noqa: E402
    import formatters                         # noqa: E402
except Exception as e:  # noqa: BLE001
    print(f"[run_demo] 导入失败（环境异常），跳过演示：{e}")
    sys.exit(0)

DEMO = ["600519.SH", "000858.SZ"]


def main():
    try:
        report = build_report(DEMO, window_days=60, crowding_lookback=250,
                              dimensions="all", prefer="sample")
        print(formatters.to_text(report))
        print("\n" + "-" * 64 + "\nMarkdown 版：\n")
        print(formatters.to_markdown(report))
    except Exception as e:  # noqa: BLE001
        print(f"[run_demo] 演示运行异常（不阻断）：{e}")
        sys.exit(0)


if __name__ == "__main__":
    main()
