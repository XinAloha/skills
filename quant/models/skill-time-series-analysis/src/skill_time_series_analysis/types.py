"""Result dataclasses for time-series diagnostics."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd


def _format_value(value: Any) -> str:
    if isinstance(value, float):
        if pd.isna(value):
            return "nan"
        text = f"{value:.4f}"
    else:
        text = str(value)
    return text.replace("|", "\\|").replace("\r\n", "\n").replace("\r", "\n").replace("\n", "<br>")


def _summary_markdown(summary: dict[str, Any]) -> str:
    rows = ["| Metric | Value |", "|---|---:|"]
    for key, value in summary.items():
        rows.append(f"| `{key}` | {_format_value(value)} |")
    return "\n".join(rows)


def _frame_markdown(frame: pd.DataFrame, *, include_index: bool = True, rows: int = 10) -> str:
    if frame.empty:
        return "_No rows._"
    view = frame.head(rows).copy()
    columns = list(view.columns)
    if include_index:
        header = ["index", *columns]
        body = [[idx, *[view.loc[idx, col] for col in columns]] for idx in view.index]
    else:
        header = columns
        body = [[row[col] for col in columns] for _, row in view.iterrows()]
    lines = [
        "| " + " | ".join(str(col) for col in header) + " |",
        "| " + " | ".join("---" for _ in header) + " |",
    ]
    for row in body:
        lines.append("| " + " | ".join(_format_value(value) for value in row) + " |")
    return "\n".join(lines)


def _bullet_markdown(items: list[str]) -> str:
    if not items:
        return "- 无。"
    return "\n".join(f"- {item}" for item in items)


@dataclass
class DistributionDiagnostics:
    """Distribution-level diagnostics for a price series."""

    summary: dict[str, Any]
    kde: pd.DataFrame
    qq: pd.DataFrame
    plot_paths: dict[str, str]

    def to_markdown(self) -> str:
        return (
            "## Summary\n\n"
            f"{_summary_markdown(self.summary)}\n\n"
            "## Evidence\n\n"
            "### KDE Diagnostics\n\n"
            f"{_frame_markdown(self.kde)}\n\n"
            "### QQ Diagnostics\n\n"
            f"{_frame_markdown(self.qq)}\n"
        )


@dataclass
class TimeSeriesAnalysis:
    """Top-level price-series analysis result."""

    summary: dict[str, Any]
    distribution: DistributionDiagnostics
    stationarity: pd.DataFrame
    log_diff: pd.DataFrame = field(default_factory=pd.DataFrame)
    log_diff_kde: pd.DataFrame = field(default_factory=pd.DataFrame)
    log_diff_qq: pd.DataFrame = field(default_factory=pd.DataFrame)

    def to_markdown(self) -> str:
        return (
            "## Summary\n\n"
            f"{_summary_markdown(self.summary)}\n\n"
            "## Evidence\n\n"
            "### Distribution\n\n"
            f"{_frame_markdown(self.distribution.kde)}\n\n"
            "### Stationarity\n\n"
            f"{_frame_markdown(self.stationarity, include_index=False)}\n\n"
            "### Log Diff\n\n"
            f"{_frame_markdown(self.log_diff, include_index=False)}\n\n"
            "### Log Diff KDE Diagnostics\n\n"
            f"{_frame_markdown(self.log_diff_kde, include_index=False)}\n\n"
            "### Log Diff QQ Diagnostics\n\n"
            f"{_frame_markdown(self.log_diff_qq, include_index=False)}\n"
        )


@dataclass
class MeanReversionAnalysis:
    """Spread and mean-reversion diagnostics."""

    summary: dict[str, Any]
    stationarity: pd.DataFrame
    half_life: dict[str, Any]
    distribution: DistributionDiagnostics | None = None

    def to_markdown(self) -> str:
        return (
            "## Summary\n\n"
            f"{_summary_markdown(self.summary)}\n\n"
            "## Evidence\n\n"
            "### Half-Life\n\n"
            f"{_summary_markdown(self.half_life)}\n\n"
            "### Stationarity\n\n"
            f"{_frame_markdown(self.stationarity, include_index=False)}\n"
        )


@dataclass
class CointegrationAnalysis:
    """Engle-Granger pair cointegration diagnostics."""

    summary: dict[str, Any]
    residuals: pd.Series
    evidence: dict[str, Any]

    def to_markdown(self) -> str:
        return (
            "## Summary\n\n"
            f"{_summary_markdown(self.summary)}\n\n"
            "## Evidence\n\n"
            f"{_summary_markdown(self.evidence)}\n"
        )


@dataclass
class TimeSeriesInterpretation:
    """Human-readable interpretation of a price-series analysis."""

    summary: dict[str, Any]
    properties: dict[str, str]
    strategy_directions: list[str]
    factor_directions: list[str]
    caveats: list[str]

    def to_markdown(self) -> str:
        return (
            "## 一句话结论\n\n"
            f"{self.summary.get('one_sentence', '')}\n\n"
            "## 时间序列性质\n\n"
            "### 平稳性分析\n\n"
            f"{self.properties.get('平稳性分析', '')}\n\n"
            "### 记忆性分析\n\n"
            f"{self.properties.get('记忆性分析', '')}\n\n"
            "### 趋势性分析\n\n"
            f"{self.properties.get('趋势性分析', '')}\n\n"
            "### 分布形态分析\n\n"
            f"{self.properties.get('分布形态分析', '')}\n\n"
            "## 量化投研建议\n\n"
            "### 策略方向\n\n"
            f"{_bullet_markdown(self.strategy_directions)}\n\n"
            "### 因子方向\n\n"
            f"{_bullet_markdown(self.factor_directions)}\n\n"
            "## 注意事项\n\n"
            f"{_bullet_markdown(self.caveats)}\n"
        )


@dataclass
class TimeSeriesReport:
    """Structured Markdown report produced by the agent-facing report API."""

    analysis: TimeSeriesAnalysis
    interpretation: TimeSeriesInterpretation
    markdown: str
    markdown_path: Path | None
    plot_paths: dict[str, str]

    def to_markdown(self) -> str:
        return self.markdown


@dataclass
class AnalysisReport:
    """Structured Markdown report for spread and pair diagnostics."""

    analysis: Any
    markdown: str
    markdown_path: Path | None
    plot_paths: dict[str, str] = field(default_factory=dict)

    def to_markdown(self) -> str:
        return self.markdown


__all__ = [
    "AnalysisReport",
    "CointegrationAnalysis",
    "DistributionDiagnostics",
    "MeanReversionAnalysis",
    "TimeSeriesAnalysis",
    "TimeSeriesInterpretation",
    "TimeSeriesReport",
]
