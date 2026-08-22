from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

try:
    from .constants import BUILD_ID, BUILD_NAME, OUTPUT_COLUMNS
    from .data_io import validate_input as _validate_input
    from .metrics import make_report, validate_config
    from .utils import json_safe
    from .visual_report import render_report_html, write_report
except ImportError:
    from constants import BUILD_ID, BUILD_NAME, OUTPUT_COLUMNS
    from data_io import validate_input as _validate_input
    from metrics import make_report, validate_config
    from utils import json_safe
    from visual_report import render_report_html, write_report


# 模块级 logger。库代码默认挂 NullHandler，由调用方决定是否启用日志输出。
logger = logging.getLogger("b10.factor_evaluation")
if not logger.handlers:
    logger.addHandler(logging.NullHandler())


def validate_input(input_data: Any) -> pd.DataFrame:
    """校验输入：标准结构化的因子值与远期收益面板。"""
    return _validate_input(input_data)


def run(input_data: Any, config: dict | None = None) -> pd.DataFrame:
    """执行一次完整的因子评估。

    参数
    ----
    input_data: 标准结构化因子与收益数据，字段包含 trade_date、ts_code、factor_value、
        forward_return。
    config: 可选配置，包括 group_mode、group_count、turnover_quantile、decay_horizons、
        factor_direction、target_kind、annualization_factor 等；target_kind=binary_success
        时 forward_return 按 0/1 成功标签评估。

    返回
    ----
    一行 BUILD 标准结果表，``result_json`` 列为完整的因子评估报告 JSON 字符串。
    """
    started = time.perf_counter()
    config = validate_config(config or {})
    data_version = str(config.get("data_version", "factor-eval-v1.3"))
    update_time = str(config.get("update_time", datetime.now().isoformat(timespec="seconds")))
    target_id = str(config.get("target_id", "factor_evaluation_report"))
    result_type = str(config.get("result_type", "factor_evaluation_report"))

    panel = _validate_input(input_data, config)
    logger.info(
        "B10 run start: target_id=%s stock_pool=%s group_mode=%s rows=%d dates=%d assets=%d",
        target_id,
        config.get("stock_pool"),
        config.get("group_mode"),
        len(panel),
        panel["trade_date"].nunique(),
        panel["ts_code"].nunique(),
    )
    report = make_report(panel, config)
    summary = report["summary"]

    out = pd.DataFrame(
        {
            "trade_date": [summary["end_date"]],
            "build_id": [BUILD_ID],
            "build_name": [BUILD_NAME],
            "target_id": [target_id],
            "result_type": [result_type],
            "result_value": [summary["rank_ic"]],
            "result_json": [json.dumps(json_safe(report), ensure_ascii=False, allow_nan=False)],
            "source_data_date": [summary["end_date"]],
            "data_version": [data_version],
            "update_time": [update_time],
        }
    )[OUTPUT_COLUMNS]
    logger.info(
        "B10 run done: target_id=%s rank_ic=%.6f quality_passed=%s elapsed=%.2fs",
        target_id,
        float(summary.get("rank_ic", 0.0)),
        bool(summary.get("quality_check_passed", False)),
        time.perf_counter() - started,
    )
    return out


def validate_output(output: pd.DataFrame) -> pd.DataFrame:
    missing = set(OUTPUT_COLUMNS) - set(output.columns)
    if missing:
        raise ValueError(f"输出缺少必要字段: {sorted(missing)}")

    # 数值字段：NaN/inf 直接报错（astype(str) 会得到 'nan' 长度为 3 而绕过判空）
    numeric_required = ["result_value"]
    for col in numeric_required:
        if output[col].isna().any():
            raise ValueError(f"输出字段 {col} 不能为空 (NaN)")
        numeric = pd.to_numeric(output[col], errors="coerce")
        if numeric.isna().any() or not np.isfinite(numeric).all():
            raise ValueError(f"输出字段 {col} 必须是有限数值")

    # 字符串字段：NaN 或空字符串都不允许
    string_required = [
        "trade_date",
        "build_id",
        "build_name",
        "target_id",
        "result_type",
        "source_data_date",
        "data_version",
        "update_time",
    ]
    for col in string_required:
        if output[col].isna().any() or (output[col].astype(str).str.len() == 0).any():
            raise ValueError(f"输出字段 {col} 不能为空")

    key = ["trade_date", "build_id", "target_id", "result_type"]
    if output.duplicated(key).any():
        raise ValueError(f"输出主键重复: {key}")

    for raw in output["result_json"].dropna():
        json.loads(raw)
    return output[OUTPUT_COLUMNS].copy()


PRIMARY_KEY = ["trade_date", "build_id", "target_id", "result_type"]


def _read_existing_production(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=OUTPUT_COLUMNS)
    try:
        existing = pd.read_parquet(path)
    except Exception as exc:  # 文件损坏或格式不兼容
        raise RuntimeError(f"读取已有生产 Parquet 失败: {path} - {exc}") from exc
    missing = [c for c in OUTPUT_COLUMNS if c not in existing.columns]
    if missing:
        raise RuntimeError(f"已有生产 Parquet schema 不兼容，缺少字段: {missing}")
    return existing[OUTPUT_COLUMNS].copy()


def write_production(
    input_data: Any,
    output_path: str | Path,
    config: dict | None = None,
    mode: str = "overwrite",
) -> pd.DataFrame:
    """把一次因子评估结果写入生产 Parquet。

    参数
    ----
    input_data: 标准评价面板。
    output_path: 生产 Parquet 路径。
    config: ``run()`` 的配置项。
    mode:
        - ``"overwrite"``（默认，向后兼容）：直接覆盖文件，最终只保留这一次评估结果。
        - ``"append"``: 读旧库 → 按主键 ``(trade_date, build_id, target_id, result_type)``
          做 upsert → 写回。同一主键以本次结果覆盖旧值，便于按日期累积多份评估。

    返回
    ----
    实际写入磁盘的 DataFrame（``append`` 模式下含历史记录）。
    """
    if mode not in {"overwrite", "append"}:
        raise ValueError(f"write_production mode 必须是 'overwrite' 或 'append'，收到: {mode!r}")

    fresh = validate_output(run(input_data, config))
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if mode == "append":
        existing = _read_existing_production(output_path)
        if not existing.empty:
            # 主键冲突时本次写入覆盖旧值（upsert 语义）
            keep_mask = ~existing.set_index(PRIMARY_KEY).index.isin(fresh.set_index(PRIMARY_KEY).index)
            preserved = existing.loc[keep_mask].copy()
            merged = pd.concat([preserved, fresh], ignore_index=True)
        else:
            merged = fresh
        merged = merged.sort_values(["trade_date", "build_id", "target_id", "result_type"]).reset_index(drop=True)
        # 写后再校验一次主键唯一性
        if merged.duplicated(PRIMARY_KEY).any():
            raise RuntimeError("append 后生产 Parquet 主键重复，写入被中止")
        validate_output(merged)
        final = merged
    else:
        final = fresh

    # 原子写：先写 .tmp 再 replace，避免半成品文件
    tmp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    try:
        final.to_parquet(tmp_path, index=False)
    except ImportError as exc:
        raise RuntimeError("写入 Parquet 需要安装 pyarrow 或 fastparquet") from exc
    tmp_path.replace(output_path)
    logger.info(
        "B10 write_production: path=%s mode=%s rows=%d (this batch=%d)",
        output_path,
        mode,
        len(final),
        len(fresh),
    )
    return final


if __name__ == "__main__":
    # B10 不再在 build.py 入口跑 demo 数据自检——这与 tests/ 子目录里的 make_sample
    # 测试同质，且不能作为回归手段。要做命令行烟测请使用：
    #   python scripts/test.py            # 跑全部测试
    #   python scripts/daily_runner.py    # 真正的调度入口
    print(
        "build.py 是 BUILD 标准入口模块（run / write_production / write_report 等），"
        "本身没有命令行用途。请用 `python scripts/test.py` 跑测试，"
        "或 `python scripts/daily_runner.py --help` 查看调度入口。"
    )
