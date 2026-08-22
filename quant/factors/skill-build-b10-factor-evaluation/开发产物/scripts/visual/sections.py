"""把 B10 评估 report 字典渲染成 HTML 各章节中间片段。

层次定位
- 上：``document`` 用本模块产出的 HTML 拼整篇文档。
- 下：本模块调用 ``svg_charts`` 完成画图，调用 ``utils.safe_float`` / ``json_safe`` 做
  数值清洗。
"""

from __future__ import annotations

from html import escape
from typing import Any

import pandas as pd

try:
    from ..constants import CHART_COLORS
    from ..utils import safe_float
    from .svg_charts import (
        format_number,
        format_percent,
        svg_bar_chart,
        svg_histogram,
        svg_line_chart,
    )
except ImportError:
    from constants import CHART_COLORS
    from utils import safe_float
    from visual.svg_charts import (
        format_number,
        format_percent,
        svg_bar_chart,
        svg_histogram,
        svg_line_chart,
    )


def report_figures(report: dict[str, Any]) -> dict[str, str]:
    target_kind = str(report.get("summary", {}).get("target_kind", "return"))
    daily = report["ic_analysis"]["daily"]
    time_daily = report.get("ic_time_analysis", {}).get("daily", [])
    labels = [row["trade_date"] for row in daily]
    ic_values = [safe_float(row.get("ic")) for row in daily]
    rank_values = [safe_float(row.get("rank_ic")) for row in daily]
    time_labels = [row["trade_date"] for row in time_daily]
    cum_ic_values = [safe_float(row.get("cum_ic")) for row in time_daily]
    cum_rank_values = [safe_float(row.get("cum_rank_ic")) for row in time_daily]
    rolling_window = min(20, max(3, len(rank_values) // 4 or 3))
    rolling_rank = pd.Series(rank_values).rolling(rolling_window, min_periods=1).mean().tolist()

    group_df = pd.DataFrame(report["layer_backtest"]["daily_group_return"])
    group_cols = [c for c in group_df.columns if str(c).startswith("G")]
    cumulative_series = []
    for idx, col in enumerate(group_cols):
        if target_kind == "binary_success":
            values = group_df[col].fillna(0).expanding(min_periods=1).mean().tolist()
            name = f"{col} 累计成功率"
        else:
            values = ((1 + group_df[col].fillna(0)).cumprod() - 1).tolist()
            name = f"{col} 累计收益"
        cumulative_series.append(
            {
                "name": name,
                "values": values,
                "labels": group_df["trade_date"].astype(str).tolist(),
                "color": CHART_COLORS[idx % len(CHART_COLORS)],
            }
        )

    group_mean = report["layer_backtest"]["group_mean_return"]
    turnover_rows = report["turnover_analysis"]["daily"]
    decay_rows = report["decay_curve"]
    factor_dist_rows = report.get("factor_distribution", {}).get("daily", [])
    return {
        "ic_time_series": svg_line_chart(
            [
                {"name": "Pearson IC", "values": ic_values, "labels": labels, "color": "#1f4e79"},
                {"name": f"RankIC {rolling_window}期滚动均值", "values": rolling_rank, "labels": labels, "color": "#e76f51"},
            ],
            "IC Time Series",
            y_label="IC",
        ),
        "rank_ic_distribution": svg_histogram(rank_values, "RankIC Distribution"),
        "cumulative_ic": svg_line_chart(
            [
                {"name": "累计 IC", "values": cum_ic_values, "labels": time_labels, "color": "#1f4e79"},
                {"name": "累计 RankIC", "values": cum_rank_values, "labels": time_labels, "color": "#e76f51"},
            ],
            "Cumulative IC",
            y_label="Cumulative IC",
            include_zero=True,
        ),
        "layer_cumulative": svg_line_chart(
            cumulative_series,
            "Quantile Success Rate" if target_kind == "binary_success" else "Quantile Cumulative Return",
            y_label="Success rate" if target_kind == "binary_success" else "Cumulative return",
            percent_axis=True,
        ),
        "monotonic_bar": svg_bar_chart(
            list(group_mean.keys()),
            [safe_float(v) for v in group_mean.values()],
            "Success Rate by Quantile" if target_kind == "binary_success" else "Mean Return by Quantile",
            percent_axis=True,
        ),
        "turnover": svg_line_chart(
            [
                {
                    "name": "Top组合换手率",
                    "values": [safe_float(row["turnover"]) for row in turnover_rows],
                    "labels": [row["trade_date"] for row in turnover_rows],
                    "color": "#6a4c93",
                }
            ],
            "Turnover Analysis",
            y_label="Turnover",
            percent_axis=True,
        ),
        "decay": svg_line_chart(
            [
                {
                    "name": "RankIC",
                    "values": [safe_float(row["rank_ic"]) for row in decay_rows],
                    "labels": [str(row["horizon"]) for row in decay_rows],
                    "color": "#2a9d8f",
                }
            ],
            "RankIC Decay Curve",
            y_label="RankIC",
        ),
        "factor_distribution": svg_line_chart(
            [
                {
                    "name": "横截面偏度",
                    "values": [safe_float(row.get("skew")) for row in factor_dist_rows],
                    "labels": [row.get("trade_date") for row in factor_dist_rows],
                    "color": "#6a4c93",
                },
                {
                    "name": "极端值占比",
                    "values": [safe_float(row.get("extreme_ratio")) for row in factor_dist_rows],
                    "labels": [row.get("trade_date") for row in factor_dist_rows],
                    "color": "#2a9d8f",
                },
            ],
            "Factor Distribution Diagnostics",
            y_label="Value",
        ),
    }


def metric_card(label: str, value: str, note: str = "") -> str:
    return (
        f'<div class="metric-card"><div class="metric-label">{escape(label)}</div>'
        f'<div class="metric-value">{escape(value)}</div>'
        f'<div class="metric-note">{escape(note)}</div></div>'
    )


def _research_table(title: str, headers: list[str], rows: list[list[Any]]) -> str:
    if not rows:
        return ""
    head = "".join(f"<th>{escape(str(item))}</th>" for item in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{escape(str(item))}</td>" for item in row) + "</tr>"
        for row in rows
    )
    return f'<h3>{escape(title)}</h3><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>'


def render_research_diagnostics(report: dict[str, Any]) -> str:
    diagnostics = report.get("research_diagnostics") or {}
    if not diagnostics:
        return ""

    sections: list[str] = []
    component_rows = []
    for row in diagnostics.get("component_ic", []):
        component_rows.append(
            [
                row.get("factor_col", ""),
                int(row.get("sample_count", 0)),
                format_number(row.get("ic")),
                format_number(row.get("rank_ic")),
                format_number(row.get("rank_icir")),
                format_percent(row.get("positive_ratio")),
                format_percent(row.get("long_short_cumulative_return")),
                "yes" if row.get("monotonicity_passed") else "no",
            ]
        )
    sections.append(
        _research_table(
            "Subfactor IC",
            ["factor", "samples", "IC", "RankIC", "RankICIR", "positive", "top-bottom", "mono"],
            component_rows,
        )
    )

    bin_rows = []
    for row in diagnostics.get("component_bins", []):
        groups = [key for key in sorted(row) if str(key).startswith("G") and str(key).endswith("_mean_return")]
        bin_rows.append(
            [
                row.get("factor_col", ""),
                format_number(row.get("monotonicity_spearman")),
                "yes" if row.get("monotonicity_passed") else "no",
                " / ".join(format_percent(row.get(group)) for group in groups),
            ]
        )
    sections.append(
        _research_table(
            "Subfactor Five-Bin Return",
            ["factor", "spearman", "mono", "G1..G5 mean return"],
            bin_rows,
        )
    )

    reverse = diagnostics.get("reverse_factor") or {}
    if reverse:
        sections.append(
            _research_table(
                "Reverse Factor Test",
                ["factor", "RankIC", "RankICIR", "positive", "top-bottom", "IR", "mono"],
                [
                    [
                        reverse.get("factor_col", "factor_reverse"),
                        format_number(reverse.get("rank_ic")),
                        format_number(reverse.get("rank_icir")),
                        format_percent(reverse.get("positive_ratio")),
                        format_percent(reverse.get("long_short_cumulative_return")),
                        format_number(reverse.get("long_short_ir")),
                        "yes" if reverse.get("monotonicity_passed") else "no",
                    ]
                ],
            )
        )

    state_rows = []
    for row in diagnostics.get("state_segments", []):
        state_rows.append(
            [
                row.get("position_state", ""),
                int(row.get("sample_count", 0)),
                int(row.get("date_count", 0)),
                format_number(row.get("rank_ic")),
                format_number(row.get("rank_icir")),
                format_percent(row.get("long_short_cumulative_return")),
                "yes" if row.get("monotonicity_passed") else "no",
            ]
        )
    sections.append(
        _research_table(
            "Position-State Segments",
            ["state", "samples", "dates", "RankIC", "RankICIR", "top-bottom", "mono"],
            state_rows,
        )
    )

    monthly_rows = []
    for row in diagnostics.get("monthly_stability", [])[-36:]:
        monthly_rows.append(
            [
                row.get("month", ""),
                int(row.get("sample_count", 0)),
                int(row.get("buy_count", 0)),
                int(row.get("watch_count", 0)),
                int(row.get("hold_count", 0)),
                format_number(row.get("rank_ic")),
                format_percent(row.get("top_bottom_return")),
            ]
        )
    sections.append(
        _research_table(
            "Monthly Stability",
            ["month", "samples", "buy", "watch", "hold", "RankIC", "top-bottom"],
            monthly_rows,
        )
    )

    return_rows = []
    for row in (diagnostics.get("return_target_comparison") or {}).get("targets", []):
        return_rows.append(
            [
                row.get("target_col", ""),
                int(row.get("sample_count", 0)),
                format_number(row.get("rank_ic")),
                format_number(row.get("rank_icir")),
                format_percent(row.get("positive_ratio")),
                format_percent(row.get("long_short_cumulative_return")),
                "yes" if row.get("monotonicity_passed") else "no",
            ]
        )
    sections.append(
        _research_table(
            "Return Target Comparison",
            ["target", "samples", "RankIC", "RankICIR", "positive", "top-bottom", "mono"],
            return_rows,
        )
    )

    warning_items = (diagnostics.get("return_target_comparison") or {}).get("warnings", [])
    warning_html = ""
    if warning_items:
        warning_html = "<ul class=\"warnings\">" + "".join(
            f"<li>{escape(str(item))}</li>" for item in warning_items
        ) + "</ul>"

    content = "".join(section for section in sections if section)
    if not content and not warning_html:
        return ""
    return f'<h2>V7 Research Diagnostics</h2>{warning_html}<section class="tables research-diagnostics">{content}</section>'


def render_report_sections(report: dict[str, Any]) -> str:
    summary = report["summary"]
    is_binary = str(summary.get("target_kind", "return")) == "binary_success"
    figures = report_figures(report)
    configured_group_count = int(summary.get("configured_group_count", summary.get("group_count", 0)))
    actual_group_count = int(summary.get("group_count", configured_group_count))
    cards = [
        metric_card("股票池", str(summary.get("stock_pool_label", "全A股")), "当前评估范围"),
        metric_card("RankIC", format_number(summary["rank_ic"]), "横截面秩相关均值"),
        metric_card("RankICIR", format_number(summary["rank_icir"]), "RankIC 均值 / 标准差"),
        metric_card("达标结论", "通过" if summary.get("quality_check_passed") else "研究中", "优质因子特征"),
        metric_card("分层", f"{actual_group_count}组", f"配置 {configured_group_count} 组"),
        metric_card("IC", format_number(summary["ic"]), "Pearson IC 均值"),
        metric_card("ICIR", format_number(summary["icir"]), "IC 均值 / 标准差"),
        metric_card("RankIC自相关", format_number(summary.get("rank_ic_autocorr_lag1")), "lag1 / 时间稳定性"),
        metric_card("因子Rank自相关", format_number(summary.get("factor_rank_autocorr_lag1")), "lag1 / 信号稳定性"),
        metric_card("RankIC偏度", format_number(summary.get("rank_ic_skew")), "分布对称性"),
        metric_card("RankIC峰度", format_number(summary.get("rank_ic_kurtosis")), "尾部风险"),
        metric_card(
            "多空成功率差" if is_binary else "多空累计收益",
            format_percent(summary["long_short_cumulative_return"]),
            "最高组 - 最低组",
        ),
        metric_card("多空IR", format_number(summary["long_short_ir"]), "年化成功率差信息比" if is_binary else "年化多空信息比"),
        metric_card("平均换手率", format_percent(summary["average_turnover"]), "顶部组合 Jaccard 距离"),
        metric_card(
            "单调性",
            "通过" if summary["monotonicity_passed"] else "未通过",
            "分层成功率递增检验" if is_binary else "分层收益递增检验",
        ),
    ]
    warnings = report.get("quality_warnings", [])
    warning_html = ""
    if warnings:
        warning_html = "<h2>质量提示</h2><ul class=\"warnings\">" + "".join(
            f"<li>{escape(str(item))}</li>" for item in warnings
        ) + "</ul>"

    group_rows = "".join(
        f"<tr><td>{escape(group)}</td><td>{format_percent(value)}</td>"
        f"<td>{format_percent(report['layer_backtest']['group_cumulative_return'][group])}</td></tr>"
        for group, value in report["layer_backtest"]["group_mean_return"].items()
    )
    decay_rows = "".join(
        f"<tr><td>{int(row['horizon'])}</td><td>{format_number(row['rank_ic'])}</td>"
        f"<td>{int(row['sample_days'])}</td></tr>"
        for row in report["decay_curve"]
    )
    quality_rows = "".join(
        f"<tr><td>{escape(str(row['dimension']))}</td><td>{escape(str(row['metric']))}</td>"
        f"<td>{format_number(row['value'])}</td><td>{escape(str(row['threshold']))}</td>"
        f"<td>{'通过' if row['passed'] else '未通过'}</td></tr>"
        for row in report.get("quality_checklist", [])
    )
    distribution = report.get("ic_distribution", {})
    factor_distribution = report.get("factor_distribution", {})
    autocorr = report.get("factor_rank_autocorrelation", {}).get("summary", {})
    diagnostic_rows = "".join(
        [
            f"<tr><td>IC偏度</td><td>{format_number(distribution.get('ic_skew'))}</td>"
            f"<td>IC峰度</td><td>{format_number(distribution.get('ic_kurtosis'))}</td></tr>",
            f"<tr><td>RankIC偏度</td><td>{format_number(distribution.get('rank_ic_skew'))}</td>"
            f"<td>RankIC峰度</td><td>{format_number(distribution.get('rank_ic_kurtosis'))}</td></tr>",
            f"<tr><td>因子平均偏度</td><td>{format_number(factor_distribution.get('avg_skew'))}</td>"
            f"<td>因子平均峰度</td><td>{format_number(factor_distribution.get('avg_kurtosis'))}</td></tr>",
            f"<tr><td>因子极端值占比</td><td>{format_percent(factor_distribution.get('avg_extreme_ratio'))}</td>"
            f"<td>因子Rank自相关lag5</td><td>{format_number(autocorr.get('lag5'))}</td></tr>",
        ]
    )

    research_html = render_research_diagnostics(report)
    mean_label = "平均成功率" if is_binary else "平均收益"
    cumulative_label = "累计成功率" if is_binary else "累计收益"
    layer_caption = (
        "按因子值分层后的累计成功率曲线，高组应相对低组占优。"
        if is_binary
        else "按因子值分层后的累计收益曲线，高组应相对低组占优。"
    )
    bar_caption = (
        "各分层平均成功率，检验成功率是否随因子排序单调改善。"
        if is_binary
        else "各分层平均收益，检验收益是否随因子排序单调改善。"
    )
    return (
        f'<section class="metrics">{"".join(cards)}</section>{warning_html}\n'
        '<h2>核心图表</h2><section class="figure-grid">\n'
        f'<figure>{figures["ic_time_series"]}<figcaption>每日 IC 与 RankIC 滚动均值，用于观察预测能力的时间稳定性。</figcaption></figure>\n'
        f'<figure>{figures["rank_ic_distribution"]}<figcaption>RankIC 分布，用于观察偏度、尾部和正 IC 占比。</figcaption></figure>\n'
        f'<figure>{figures["cumulative_ic"]}<figcaption>累计 IC 与累计 RankIC，用于观察长期是否持续同向贡献。</figcaption></figure>\n'
        f'<figure>{figures["layer_cumulative"]}<figcaption>{layer_caption}</figcaption></figure>\n'
        f'<figure>{figures["monotonic_bar"]}<figcaption>{bar_caption}</figcaption></figure>\n'
        f'<figure>{figures["turnover"]}<figcaption>顶部组合换手率，衡量组合稳定性与潜在交易成本压力。</figcaption></figure>\n'
        f'<figure>{figures["decay"]}<figcaption>不同持有期 RankIC 衰减曲线，用于判断信号有效周期。</figcaption></figure>\n'
        f'<figure>{figures["factor_distribution"]}<figcaption>因子横截面偏度和极端值占比，用于识别异常分布风险。</figcaption></figure>\n'
        '</section><h2>优质因子特征达标表</h2><section class="tables">'
        f'<table><thead><tr><th>维度</th><th>指标</th><th>数值</th><th>阈值</th><th>结论</th></tr></thead>'
        f'<tbody>{quality_rows}</tbody></table>'
        f'<table><thead><tr><th>诊断项</th><th>数值</th><th>诊断项</th><th>数值</th></tr></thead>'
        f'<tbody>{diagnostic_rows}</tbody></table></section>\n'
        f'{research_html}\n'
        f'<h2>明细表</h2><section class="tables">'
        f'<table><thead><tr><th>分层</th><th>{mean_label}</th><th>{cumulative_label}</th></tr></thead>'
        f'<tbody>{group_rows}</tbody></table>'
        f'<table><thead><tr><th>周期</th><th>RankIC</th><th>有效天数</th></tr></thead>'
        f'<tbody>{decay_rows}</tbody></table></section>\n'
        f'<h2>方法说明</h2><p class="method">{escape(report["methodology"])}</p>'
    )
