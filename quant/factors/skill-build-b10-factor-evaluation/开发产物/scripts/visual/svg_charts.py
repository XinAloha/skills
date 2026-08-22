"""B10 报告中的 SVG 图表工具。

只负责"把数据画成 SVG 字符串"，不读 report 字典、不组装 HTML 文档。
和 sections.py 的关系：sections 把 report 拆成图表数据后调用本模块；本模块
完全无业务概念。
"""

from __future__ import annotations

from html import escape
from typing import Any

import numpy as np

try:
    from ..constants import CHART_COLORS
    from ..utils import safe_float
except ImportError:
    from constants import CHART_COLORS
    from utils import safe_float


def format_number(value: Any, digits: int = 4) -> str:
    return f"{safe_float(value):.{digits}f}"


def format_percent(value: Any, digits: int = 2) -> str:
    return f"{safe_float(value) * 100:.{digits}f}%"


def axis_range(values: list[float], include_zero: bool = True) -> tuple[float, float]:
    clean = [float(v) for v in values if v is not None and np.isfinite(float(v))]
    if not clean:
        return -1.0, 1.0
    low, high = min(clean), max(clean)
    if include_zero:
        low, high = min(low, 0.0), max(high, 0.0)
    if low == high:
        span = abs(low) or 1.0
        low -= span * 0.2
        high += span * 0.2
    padding = (high - low) * 0.08
    return low - padding, high + padding


def project(value: float, low: float, high: float, start: float, end: float, invert: bool = False) -> float:
    ratio = 0.5 if high == low else (value - low) / (high - low)
    if invert:
        ratio = 1 - ratio
    return start + ratio * (end - start)


def svg_line_chart(
    series: list[dict[str, Any]],
    title: str,
    y_label: str = "",
    width: int = 900,
    height: int = 350,
    percent_axis: bool = False,
    include_zero: bool = True,
) -> str:
    margin = {"left": 62, "right": 28, "top": 62, "bottom": 50}
    plot_w = width - margin["left"] - margin["right"]
    plot_h = height - margin["top"] - margin["bottom"]
    all_values = [v for item in series for v in item["values"] if v is not None]
    y_min, y_max = axis_range(all_values, include_zero=include_zero)
    max_len = max((len(item["values"]) for item in series), default=0)
    labels = series[0].get("labels", []) if series else []

    grid = []
    for i in range(5):
        y_value = y_min + (y_max - y_min) * i / 4
        y = project(y_value, y_min, y_max, margin["top"], margin["top"] + plot_h, invert=True)
        label = format_percent(y_value, 1) if percent_axis else format_number(y_value, 3)
        grid.append(
            f'<line x1="{margin["left"]}" y1="{y:.2f}" x2="{width - margin["right"]}" y2="{y:.2f}" class="grid"/>'
            f'<text x="{margin["left"] - 10}" y="{y + 4:.2f}" class="axis-label" text-anchor="end">{label}</text>'
        )

    x_labels = []
    if max_len:
        for idx in sorted(set([0, max_len // 2, max_len - 1])):
            x = margin["left"] if max_len == 1 else margin["left"] + plot_w * idx / (max_len - 1)
            label = escape(str(labels[idx])) if idx < len(labels) else str(idx + 1)
            x_labels.append(f'<text x="{x:.2f}" y="{height - 18}" class="axis-label" text-anchor="middle">{label}</text>')

    paths = []
    legend = []
    for s_idx, item in enumerate(series):
        values = item["values"]
        color = item.get("color", CHART_COLORS[s_idx % len(CHART_COLORS)])
        points = []
        for i, raw in enumerate(values):
            if raw is None:
                continue
            x = margin["left"] if len(values) == 1 else margin["left"] + plot_w * i / (len(values) - 1)
            y = project(float(raw), y_min, y_max, margin["top"], margin["top"] + plot_h, invert=True)
            points.append((x, y))
        if points:
            d = " ".join(("M" if idx == 0 else "L") + f"{x:.2f},{y:.2f}" for idx, (x, y) in enumerate(points))
            paths.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="2.4" stroke-linejoin="round" stroke-linecap="round"/>')
            for x, y in points[-3:]:
                paths.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="2.8" fill="{color}" opacity="0.95"/>')
        lx = margin["left"] + (s_idx % 3) * 220
        ly = 44 + (s_idx // 3) * 18
        legend.append(
            f'<line x1="{lx}" y1="{ly}" x2="{lx + 22}" y2="{ly}" stroke="{color}" stroke-width="3" stroke-linecap="round"/>'
            f'<text x="{lx + 30}" y="{ly + 4}" class="legend">{escape(str(item["name"]))}</text>'
        )

    return f"""
<svg class="chart" viewBox="0 0 {width} {height}" role="img" aria-label="{escape(title)}">
  <text x="{margin["left"]}" y="24" class="chart-title">{escape(title)}</text>
  {''.join(legend)}
  <line x1="{margin["left"]}" y1="{margin["top"] + plot_h}" x2="{width - margin["right"]}" y2="{margin["top"] + plot_h}" class="axis"/>
  <line x1="{margin["left"]}" y1="{margin["top"]}" x2="{margin["left"]}" y2="{margin["top"] + plot_h}" class="axis"/>
  {''.join(grid)}
  {''.join(paths)}
  {''.join(x_labels)}
  <text x="18" y="{margin["top"] + plot_h / 2:.2f}" class="axis-label" transform="rotate(-90 18,{margin["top"] + plot_h / 2:.2f})" text-anchor="middle">{escape(y_label)}</text>
</svg>
"""


def svg_bar_chart(
    labels: list[str],
    values: list[float],
    title: str,
    width: int = 900,
    height: int = 320,
    percent_axis: bool = False,
) -> str:
    margin = {"left": 62, "right": 28, "top": 44, "bottom": 54}
    plot_w = width - margin["left"] - margin["right"]
    plot_h = height - margin["top"] - margin["bottom"]
    y_min, y_max = axis_range(values, include_zero=True)
    zero_y = project(0.0, y_min, y_max, margin["top"], margin["top"] + plot_h, invert=True)
    gap = 14
    bar_w = (plot_w - gap * (len(values) + 1)) / max(len(values), 1)
    label_step = max(1, int(np.ceil(len(labels) / 7)))

    grid = []
    for i in range(5):
        y_value = y_min + (y_max - y_min) * i / 4
        y = project(y_value, y_min, y_max, margin["top"], margin["top"] + plot_h, invert=True)
        label = format_percent(y_value, 1) if percent_axis else format_number(y_value, 3)
        grid.append(
            f'<line x1="{margin["left"]}" y1="{y:.2f}" x2="{width - margin["right"]}" y2="{y:.2f}" class="grid"/>'
            f'<text x="{margin["left"] - 10}" y="{y + 4:.2f}" class="axis-label" text-anchor="end">{label}</text>'
        )

    bars = []
    for idx, (label, value) in enumerate(zip(labels, values)):
        x = margin["left"] + gap + idx * (bar_w + gap)
        y = project(value, y_min, y_max, margin["top"], margin["top"] + plot_h, invert=True)
        top = min(y, zero_y)
        color = "#2a9d8f" if value >= 0 else "#e76f51"
        shown_label = escape(label) if idx % label_step == 0 or len(labels) <= 7 else ""
        bars.append(
            f'<rect x="{x:.2f}" y="{top:.2f}" width="{bar_w:.2f}" height="{abs(zero_y - y):.2f}" rx="3" fill="{color}" opacity="0.88"/>'
            f'<text x="{x + bar_w / 2:.2f}" y="{height - 20}" class="axis-label" text-anchor="middle">{shown_label}</text>'
        )

    return f"""
<svg class="chart" viewBox="0 0 {width} {height}" role="img" aria-label="{escape(title)}">
  <text x="{margin["left"]}" y="28" class="chart-title">{escape(title)}</text>
  {''.join(grid)}
  <line x1="{margin["left"]}" y1="{zero_y:.2f}" x2="{width - margin["right"]}" y2="{zero_y:.2f}" class="zero"/>
  <line x1="{margin["left"]}" y1="{margin["top"]}" x2="{margin["left"]}" y2="{margin["top"] + plot_h}" class="axis"/>
  {''.join(bars)}
</svg>
"""


def svg_histogram(values: list[float], title: str) -> str:
    clean = [v for v in values if v is not None and np.isfinite(float(v))]
    clean = clean or [0.0]
    bins = min(18, max(6, int(np.sqrt(len(clean)))))
    counts, edges = np.histogram(clean, bins=bins)
    labels = [f"{edges[i]:.2f}" for i in range(len(edges) - 1)]
    return svg_bar_chart(labels, [float(x) for x in counts], title)
