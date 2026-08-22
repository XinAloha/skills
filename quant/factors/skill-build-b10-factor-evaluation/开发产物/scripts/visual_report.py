"""B10 可视化报告对外薄入口。

历史调用方一直 ``from visual_report import render_report_html, write_report`` 等。
内部实现已拆为三层 ``visual/{svg_charts,sections,document}``。本模块只做顶层
re-export，保持签名 100% 兼容。

新代码请直接 ``from visual import ...``，避免叠加间接层。
"""

from __future__ import annotations

try:
    from .visual.document import (
        available_stock_pools,
        config_for_group_mode,
        group_mode_label,
        make_group_reports,
        render_group_selector,
        render_html_report,
        render_report_html,
        write_report,
    )
    from .visual.sections import (
        metric_card,
        render_report_sections,
        render_research_diagnostics,
        report_figures,
    )
    from .visual.svg_charts import (
        axis_range,
        format_number,
        format_percent,
        project,
        svg_bar_chart,
        svg_histogram,
        svg_line_chart,
    )
    # ``compute_panel_base`` / ``apply_layer`` 是测试里 monkeypatch 的目标
    # （test_make_group_reports_reuses_panel_base 通过这两个名字打补丁），
    # 历史上从 visual_report 顶部转发而来；保留这一层重导出以兼容。
    from .metrics import apply_layer, compute_panel_base
except ImportError:
    from visual.document import (  # type: ignore[no-redef]
        available_stock_pools,
        config_for_group_mode,
        group_mode_label,
        make_group_reports,
        render_group_selector,
        render_html_report,
        render_report_html,
        write_report,
    )
    from visual.sections import (  # type: ignore[no-redef]
        metric_card,
        render_report_sections,
        render_research_diagnostics,
        report_figures,
    )
    from visual.svg_charts import (  # type: ignore[no-redef]
        axis_range,
        format_number,
        format_percent,
        project,
        svg_bar_chart,
        svg_histogram,
        svg_line_chart,
    )
    from metrics import apply_layer, compute_panel_base  # type: ignore[no-redef]


__all__ = [
    # 文档组装层
    "available_stock_pools",
    "config_for_group_mode",
    "group_mode_label",
    "make_group_reports",
    "render_group_selector",
    "render_html_report",
    "render_report_html",
    "write_report",
    # 章节渲染层
    "metric_card",
    "render_report_sections",
    "render_research_diagnostics",
    "report_figures",
    # SVG 工具层
    "axis_range",
    "format_number",
    "format_percent",
    "project",
    "svg_bar_chart",
    "svg_histogram",
    "svg_line_chart",
    # 测试 monkeypatch 入口（性能拆分复用次数测试要求）
    "apply_layer",
    "compute_panel_base",
]
