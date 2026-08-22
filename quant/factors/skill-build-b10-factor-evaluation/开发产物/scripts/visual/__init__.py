"""B10 可视化报告子模块。

按职责拆为三层，避免 visual_report 单文件 685 行混合 SVG/章节/编排：

- ``svg_charts``：纯 SVG 工具函数（line / bar / histogram + 共用 axis/scale 工具）。
- ``sections``：把 report dict 渲染成 metric cards / 表格 / figure-grid 等中间 HTML 段。
- ``document``：组装独立 HTML 文档（``render_html_report`` / ``write_report``）。

历史调用方一直从 ``visual_report`` 顶层 import；上层 ``scripts/visual_report.py``
保留一个薄入口模块对外重新导出，签名不变。
"""

from .document import (  # noqa: F401
    available_stock_pools,
    config_for_group_mode,
    group_mode_label,
    make_group_reports,
    render_group_selector,
    render_html_report,
    render_report_html,
    write_report,
)
from .sections import (  # noqa: F401
    metric_card,
    render_report_sections,
    render_research_diagnostics,
    report_figures,
)
from .svg_charts import (  # noqa: F401
    axis_range,
    format_number,
    format_percent,
    project,
    svg_bar_chart,
    svg_histogram,
    svg_line_chart,
)
