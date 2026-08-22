from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

try:
    from .constants import COLUMN_ALIASES, REQUIRED_COLUMNS, STOCK_POOL_LABELS
except ImportError:
    from constants import COLUMN_ALIASES, REQUIRED_COLUMNS, STOCK_POOL_LABELS


STOCK_POOL_OPTIONAL_COLUMNS = [
    "stock_pool_memberships",
    "primary_stock_pool",
    *[f"is_pool_{pool}" for pool in STOCK_POOL_LABELS],
]
RETURN_TARGET_COLUMNS = [
    "ret_oc_t1",
    "ret_oo_t1_t2",
    "ret_open_t1_close_t2",
    "ret_cc_t1_t2",
    "ret_vwap_t1_t2",
]
DIAGNOSTIC_OPTIONAL_COLUMNS = [
    "signal",
    "position_state",
    "high_position_risk",
    "recent_repeat_agency_count",
    "max_recent_buy_days",
    "disclosure_repeat_agency_count",
    "net_buy_to_amount",
    "sell_pressure",
    "ret_5d",
    "ret_10d",
    "volume_ratio",
    "upper_shadow_ratio",
    "same_day_top_agency_count",
    "consecutive_3_agency_count",
    "max_consecutive_buy_days",
    "collaboration_strength",
    "avg_agency_quality",
    "max_agency_quality",
    "hotmoney_score_v6",
    "hotmoney_score_v7",
    # 注意：factor_reverse 已不在可选输入列里。``research_diagnostics.reverse_factor_analysis``
    # 始终用 ``-factor_value`` 重算反向因子，不再读上游字段，以消除"输入列 / 重算 /
    # sub-factor"三处语义冲突。如果上游 panel 中有同名列，会被 ``research_component_columns``
    # 当作 sub-factor 单独走 component_ic 而不是反向检验通道。
]


def forward_return_horizon_columns(columns: Any) -> list[str]:
    out = []
    for col in columns:
        text = str(col)
        if not text.startswith("forward_return_") or not text.endswith("d"):
            continue
        horizon = text[len("forward_return_") : -1]
        if horizon.isdigit():
            out.append(text)
    return out


def diagnostic_columns(columns: Any) -> list[str]:
    available = set(columns)
    prefixed = [col for col in columns if str(col).startswith("factor_component_")]
    return [col for col in [*DIAGNOSTIC_OPTIONAL_COLUMNS, *RETURN_TARGET_COLUMNS, *prefixed] if col in available]


def coerce_numeric_column(df: pd.DataFrame, col: str) -> None:
    numeric = pd.to_numeric(df[col], errors="coerce")
    bad_numeric = numeric.isna() & df[col].notna()
    if bad_numeric.any():
        raise ValueError(f"{col} 存在无法转换为数字的非法类型，异常行数: {int(bad_numeric.sum())}")
    bad_finite = ~np.isfinite(numeric) & numeric.notna()
    if bad_finite.any():
        raise ValueError(f"{col} 存在 inf 或 -inf 等非有限数值，异常行数: {int(bad_finite.sum())}")
    df[col] = numeric


def load_frame(input_data: Any) -> pd.DataFrame:
    if isinstance(input_data, pd.DataFrame):
        return input_data.copy()
    if isinstance(input_data, (str, Path)):
        path = Path(input_data)
        suffix = path.suffix.lower()
        if suffix == ".parquet":
            return pd.read_parquet(path)
        if suffix == ".csv":
            return pd.read_csv(path)
        if suffix in {".xlsx", ".xls"}:
            return pd.read_excel(path)
        raise ValueError(f"不支持的输入文件类型: {suffix}")
    if isinstance(input_data, dict) and "data" in input_data:
        return load_frame(input_data["data"])
    try:
        return pd.DataFrame(input_data)
    except ValueError as exc:
        raise ValueError("input_data 必须是表格型结构、记录列表、dict(data=...) 或文件路径") from exc


def resolve_columns(df: pd.DataFrame, config: dict | None = None) -> pd.DataFrame:
    config = config or {}
    df = df.rename(columns={source: target for source, target in COLUMN_ALIASES.items() if source in df.columns})
    configured = config.get("columns") or {}
    if not configured:
        return df

    if not isinstance(configured, dict):
        raise ValueError("config['columns'] 必须是 dict 形式 {原始字段: 标准字段} 或 {标准字段: 原始字段}")

    # 同时支持 {原始: 标准} 和 {标准: 原始} 两种写法，但禁止两种写法在同一个 dict 内混用以及目标重复。
    rename_map: dict[str, str] = {}
    for left, right in configured.items():
        if not isinstance(left, str) or not isinstance(right, str):
            raise ValueError(f"config['columns'] 必须全部为字符串映射，发现非法项: {left!r}: {right!r}")
        if left in REQUIRED_COLUMNS and right in df.columns:
            source, target = right, left
        elif right in REQUIRED_COLUMNS and left in df.columns:
            source, target = left, right
        else:
            raise ValueError(
                f"config['columns'] 项 {left!r}: {right!r} 无法解析，"
                f"必须有一边是标准字段 {sorted(REQUIRED_COLUMNS)} 且另一边在输入列中"
            )
        if source in rename_map and rename_map[source] != target:
            raise ValueError(f"config['columns'] 中 {source!r} 被映射到多个标准字段: {rename_map[source]!r} 与 {target!r}")
        if target in rename_map.values() and rename_map.get(source) != target:
            others = [src for src, tgt in rename_map.items() if tgt == target]
            raise ValueError(f"config['columns'] 中多个原始字段 {others + [source]!r} 同时映射到 {target!r}")
        if target in df.columns and target != source:
            raise ValueError(
                f"config['columns'] 试图把 {source!r} 重命名为 {target!r}，但 {target!r} 已存在于输入列中，会产生冲突"
            )
        rename_map[source] = target

    return df.rename(columns=rename_map)


def validate_input(input_data: Any, config: dict | None = None) -> pd.DataFrame:
    config = config or {}
    drop_missing = bool(config.get("drop_missing", True))
    df = load_frame(input_data)
    if df.empty:
        raise ValueError("input_data 不能为空")
    raw_row_count = int(len(df))

    df = resolve_columns(df, config)
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"input_data 缺少必要字段: {sorted(missing)}")

    horizon_cols = forward_return_horizon_columns(df.columns)
    optional_cols = [col for col in STOCK_POOL_OPTIONAL_COLUMNS if col in df.columns]
    diag_cols = diagnostic_columns(df.columns)
    selected_cols = []
    for col in ["trade_date", "ts_code", "factor_value", "forward_return", *horizon_cols, *optional_cols, *diag_cols]:
        if col in df.columns and col not in selected_cols:
            selected_cols.append(col)
    df = df[selected_cols].copy()
    parsed_dates = pd.to_datetime(df["trade_date"], errors="coerce")
    bad_dates = parsed_dates.isna() & df["trade_date"].notna()
    if bad_dates.any():
        raise ValueError(f"trade_date 存在无法解析的日期值，异常行数: {int(bad_dates.sum())}")
    df["trade_date"] = parsed_dates.dt.strftime("%Y-%m-%d")

    for col in ["factor_value", "forward_return"]:
        coerce_numeric_column(df, col)
    for col in horizon_cols:
        coerce_numeric_column(df, col)
    numeric_diag_cols = [
        col
        for col in diag_cols
        if col not in {"signal", "position_state", "high_position_risk"}
    ]
    for col in numeric_diag_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    required_cols = ["trade_date", "ts_code", "factor_value", "forward_return"]
    missing_mask = df[required_cols].isna().any(axis=1)
    missing_row_count = int(missing_mask.sum())
    if missing_row_count:
        if not drop_missing:
            raise ValueError(f"input_data 存在缺失值行，异常行数: {missing_row_count}")
        df = df.loc[~missing_mask].copy()
    if df.empty:
        raise ValueError("清洗后样本为空，请检查 factor_value / forward_return")
    if str(config.get("target_kind", "return")).lower() == "binary_success":
        if not df["forward_return"].between(0, 1).all():
            raise ValueError("target_kind=binary_success 时 forward_return 必须是 0/1 或 0-1 成功标签")

    df["ts_code"] = df["ts_code"].astype(str).str.strip()
    blank_code_mask = df["ts_code"].eq("")
    if blank_code_mask.any():
        raise ValueError(f"ts_code 不能为空或空白字符串，异常行数: {int(blank_code_mask.sum())}")
    for col in optional_cols:
        if col.startswith("is_pool_"):
            df[col] = df[col].astype(str).str.lower().isin({"1", "true", "yes", "y"})
        else:
            df[col] = df[col].fillna("").astype(str)
    if "high_position_risk" in df.columns:
        df["high_position_risk"] = df["high_position_risk"].astype(str).str.lower().isin({"1", "true", "yes", "y"})
    for col in ["signal", "position_state"]:
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str)
    duplicate_mask = df.duplicated(["trade_date", "ts_code"], keep=False)
    if duplicate_mask.any():
        examples = df.loc[duplicate_mask, ["trade_date", "ts_code"]].head(5).to_dict("records")
        raise ValueError(f"input_data 存在重复主键 trade_date + ts_code，示例: {examples}")

    df = df.sort_values(["trade_date", "ts_code"]).reset_index(drop=True)
    df.attrs["raw_row_count"] = raw_row_count
    df.attrs["dropped_missing_row_count"] = missing_row_count
    return df
