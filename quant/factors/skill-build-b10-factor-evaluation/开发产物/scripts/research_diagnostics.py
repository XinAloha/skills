"""B10 研究诊断（V7 研究层）。

把以下 5 类研究指标从 metrics.py 中拆出来，避免主指标模块（IC/分层/换手/衰减/达标表）
和"打板研究分支专用诊断"互相耦合：

- ``component_ic_analysis``：子因子 IC（V7 研究列 ``factor_component_*`` + ``factor_reverse``）。
- ``component_bin_analysis``：子因子分层均值。
- ``reverse_factor_analysis``：反向因子检验。
- ``state_segment_analysis``：仓位状态分组（``position_state``）。
- ``monthly_stability``：月度稳定性 + 信号分布（``signal``）。
- ``return_target_comparison``：跨 ``ret_*`` 收益口径比较。

入口 ``make_research_diagnostics(panel, config)`` 在 ``apply_layer`` 中按需调用，
默认在面板中存在 ``factor_component_*`` 列时自动启用，否则需要显式 ``research_diagnostics=True``。

口径修正
- 子因子分组数已统一为 ``min(group_count, group_count)`` 即按 config["group_count"] 全量
  使用，不再混用 5 / 10 / min(5, group_count)。原来 ``component_ic_analysis`` 写死 5、
  ``state/monthly/return_target_comparison`` 写死 ``min(5, group_count)`` 会让同一份
  result_json 内分组数不一致，导致 sub-factor 与主报告无法横向对比。修正后所有
  研究函数都按 config["group_count"] 出表。
"""

from __future__ import annotations

from typing import Any

import pandas as pd

try:
    from .metrics import daily_ic, ic_summary, layer_backtest
except ImportError:
    from metrics import daily_ic, ic_summary, layer_backtest


# 兼容旧 import 路径：metrics.RESEARCH_RETURN_TARGETS 仍可被外部代码引用
RESEARCH_RETURN_TARGETS = [
    "ret_oc_t1",
    "ret_oo_t1_t2",
    "ret_open_t1_close_t2",
    "ret_cc_t1_t2",
    "ret_vwap_t1_t2",
]


def _parse_return_targets(value: Any) -> list[str]:
    if value is None:
        return RESEARCH_RETURN_TARGETS
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return [str(item).strip() for item in value if str(item).strip()]


def _factor_summary(
    panel: pd.DataFrame,
    factor_col: str,
    target_kind: str,
    annualization_factor: float,
    group_count: int,
) -> dict[str, Any]:
    """对任意因子列跑一次"轻量评估摘要"：日 IC + 分层。

    研究诊断各子模块（subfactor / state / monthly / target_compare）共用此辅助。
    `group_count` 由调用方传入，不做内部 ``min(5, ...)`` 截断——保证同一份报告内
    所有研究表的分组语义一致（与主 layer_backtest 一致）。
    """
    if factor_col not in panel.columns:
        return {}
    data = panel.dropna(subset=[factor_col, "forward_return"]).copy()
    if data.empty:
        return {}
    daily = daily_ic(data, factor_col)
    report = ic_summary(daily)
    layer = layer_backtest(data, group_count, factor_col, annualization_factor, target_kind)
    return {
        "factor_col": factor_col,
        "sample_count": int(len(data)),
        "date_count": int(data["trade_date"].nunique()),
        "ic": report["ic"]["mean"],
        "icir": report["ic"]["ir"],
        "rank_ic": report["rank_ic"]["mean"],
        "rank_icir": report["rank_ic"]["ir"],
        "positive_ratio": report["rank_ic"]["positive_ratio"],
        "long_short_cumulative_return": layer["long_short_cumulative_return"],
        "long_short_ir": layer["long_short_ir"],
        "long_short_win_rate": layer["long_short_win_rate"],
        "monotonicity_spearman": layer["monotonicity"]["spearman"],
        "monotonicity_passed": layer["monotonicity"]["passed"],
    }


def research_component_columns(panel: pd.DataFrame) -> list[str]:
    """列出可参与子因子诊断的列：``factor_component_*`` 与 ``factor_reverse``。

    ``factor_reverse`` 在 data_io 端被作为可选输入列保留；进入研究诊断时如果上游
    没传，则在 ``reverse_factor_analysis`` 中按 ``-factor_value`` 临时构造。
    """
    preferred = [
        "factor_component_same_day",
        "factor_component_repeat",
        "factor_component_quality",
        "factor_component_money",
        "factor_component_sell_pressure",
        "factor_reverse",
    ]
    extras = [col for col in panel.columns if str(col).startswith("factor_component_") and col not in preferred]
    return [col for col in [*preferred, *extras] if col in panel.columns]


def component_ic_analysis(panel: pd.DataFrame, config: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    group_count = int(config["group_count"])
    annualization = float(config["annualization_factor"])
    target_kind = str(config["target_kind"])
    for col in research_component_columns(panel):
        summary = _factor_summary(panel, col, target_kind, annualization, group_count)
        if summary:
            rows.append(summary)
    return rows


def component_bin_analysis(panel: pd.DataFrame, config: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    group_count = int(config["group_count"])
    annualization = float(config["annualization_factor"])
    target_kind = str(config["target_kind"])
    for col in research_component_columns(panel):
        data = panel.dropna(subset=[col, "forward_return"]).copy()
        if data.empty:
            continue
        layer = layer_backtest(data, group_count, col, annualization, target_kind)
        row = {
            "factor_col": col,
            "monotonicity_spearman": layer["monotonicity"]["spearman"],
            "monotonicity_passed": layer["monotonicity"]["passed"],
        }
        for group, value in layer["group_mean_return"].items():
            row[f"{group}_mean_return"] = value
        rows.append(row)
    return rows


def reverse_factor_analysis(panel: pd.DataFrame, config: dict[str, Any]) -> dict[str, Any]:
    """反向因子检验：始终用 ``-factor_value`` 重算，不读上游 ``factor_reverse``。

    收口语义：``factor_reverse`` 在 data_io / metrics / research 三处历史上有冲突
    （input 列 / research sub-factor / 反向重算）。这里的反向检验固定按
    ``-factor_value`` 构造，结果列名仍叫 ``factor_reverse`` 以保持报告兼容。
    """
    data = panel.copy()
    data["factor_reverse"] = -pd.to_numeric(data["factor_value"], errors="coerce")
    return _factor_summary(
        data,
        "factor_reverse",
        str(config["target_kind"]),
        float(config["annualization_factor"]),
        group_count=int(config["group_count"]),
    )


def state_segment_analysis(
    panel: pd.DataFrame,
    config: dict[str, Any],
    factor_col: str = "effective_factor_value",
) -> list[dict[str, Any]]:
    if "position_state" not in panel.columns:
        return []
    rows = []
    group_count = int(config["group_count"])
    annualization = float(config["annualization_factor"])
    target_kind = str(config["target_kind"])
    for state, part in panel.groupby("position_state", dropna=False):
        if str(state).strip() == "":
            continue
        summary = _factor_summary(part, factor_col, target_kind, annualization, group_count)
        if summary:
            summary["position_state"] = str(state)
            rows.append(summary)
    order = {"low_position": 0, "mid_position": 1, "high_position": 2}
    return sorted(rows, key=lambda row: order.get(row["position_state"], 9))


def monthly_stability(
    panel: pd.DataFrame,
    config: dict[str, Any],
    factor_col: str = "effective_factor_value",
) -> list[dict[str, Any]]:
    data = panel.copy()
    data["month"] = pd.to_datetime(data["trade_date"], errors="coerce").dt.strftime("%Y-%m")
    rows = []
    group_count = int(config["group_count"])
    annualization = float(config["annualization_factor"])
    target_kind = str(config["target_kind"])
    for month, part in data.dropna(subset=["month"]).groupby("month"):
        daily = daily_ic(part, factor_col)
        ic_report = ic_summary(daily)
        layer = layer_backtest(part, group_count, factor_col, annualization, target_kind)
        signal_counts = part["signal"].value_counts().to_dict() if "signal" in part.columns else {}
        rows.append(
            {
                "month": str(month),
                "sample_count": int(len(part)),
                "asset_count": int(part["ts_code"].nunique()),
                "rank_ic": ic_report["rank_ic"]["mean"],
                "rank_ic_positive_ratio": ic_report["rank_ic"]["positive_ratio"],
                "top_bottom_return": layer["long_short_cumulative_return"],
                "buy_count": int(signal_counts.get("buy", 0)),
                "watch_count": int(signal_counts.get("watch", 0)),
                "hold_count": int(signal_counts.get("hold", 0)),
            }
        )
    return rows


def return_target_comparison(
    panel: pd.DataFrame,
    config: dict[str, Any],
    factor_col: str = "effective_factor_value",
) -> dict[str, Any]:
    rows = []
    warnings = []
    group_count = int(config["group_count"])
    annualization = float(config["annualization_factor"])
    target_kind = str(config["target_kind"])
    for target in _parse_return_targets(config.get("return_targets")):
        if target not in panel.columns:
            warnings.append(f"收益口径 {target} 不在输入面板中，已跳过。")
            continue
        data = panel.dropna(subset=[target, factor_col]).copy()
        if data.empty:
            warnings.append(f"收益口径 {target} 没有有效样本，已跳过。")
            continue
        data["forward_return"] = pd.to_numeric(data[target], errors="coerce")
        summary = _factor_summary(data, factor_col, target_kind, annualization, group_count)
        if summary:
            summary["target_col"] = target
            rows.append(summary)
    return {"targets": rows, "warnings": warnings}


def make_research_diagnostics(panel: pd.DataFrame, config: dict[str, Any]) -> dict[str, Any]:
    """V7 研究诊断总入口。

    启用规则：``config["research_diagnostics"] == True`` 显式开启，
    或者面板中存在任何 ``factor_component_*`` / ``factor_reverse`` 列时自动启用。
    没有任何研究列、且没有显式开启时返回空 dict，apply_layer 用空 dict 视为关闭。
    """
    enabled = bool(config.get("research_diagnostics", False)) or bool(research_component_columns(panel))
    if not enabled:
        return {}
    return {
        "component_ic": component_ic_analysis(panel, config),
        "component_bins": component_bin_analysis(panel, config),
        "reverse_factor": reverse_factor_analysis(panel, config),
        "state_segments": state_segment_analysis(panel, config),
        "monthly_stability": monthly_stability(panel, config),
        "return_target_comparison": return_target_comparison(panel, config),
    }
