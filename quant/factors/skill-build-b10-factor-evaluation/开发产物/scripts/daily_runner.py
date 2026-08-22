"""B10 因子评估每日调度入口。

用法（在 build-b10-factor-evaluation/开发产物/ 下执行）：

    python scripts/daily_runner.py \
        --input "输入面板.parquet" \
        --target-id my-factor-v1 \
        --stock-pool zz500 \
        --group-mode quintile \
        --data-version daily-eval-v1 \
        --output ../生产产物/数据库.parquet \
        --report-dir reports/daily

行为：
1. 读取 ``--input`` 指向的标准评价面板（CSV/Parquet/XLSX），调用 ``validate_input``。
2. 调用一次 ``make_report`` 生成完整 JSON 报告；以此结果同时：
   - 包成 BUILD schema 行，``write_production`` 按主键 upsert 写入生产库；
   - ``render_html_report`` 渲染独立 HTML 文件落盘。
   这样一次评估只跑一遍，避免老版本"write_production 调一次 + write_report 再调一次"
   的重复计算。
3. 全过程结构化日志写到 ``--log-file`` 或标准错误流。

红线
- 本脚本只负责"读已有面板 + 调评估 + 落报告"，不直接拉行情或上游因子；
  PandaAI data 接入由外部桥接层负责，B10 只消费标准面板。
- B10 不联网；中性化所需的行业 / 风格暴露面板必须由调用方在 ``input`` 面板中
  自带或在外部桥接层组装好后传入。
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

try:
    from .build import (
        OUTPUT_COLUMNS,
        PRIMARY_KEY,
        _read_existing_production,
        logger as build_logger,
        validate_output,
    )
    from .constants import BUILD_ID, BUILD_NAME
    from .data_io import validate_input
    from .metrics import make_report, validate_config
    from .utils import json_safe
    from .visual_report import render_html_report
except ImportError:
    from build import (  # type: ignore[no-redef]
        OUTPUT_COLUMNS,
        PRIMARY_KEY,
        _read_existing_production,
        logger as build_logger,
        validate_output,
    )
    from constants import BUILD_ID, BUILD_NAME  # type: ignore[no-redef]
    from data_io import validate_input  # type: ignore[no-redef]
    from metrics import make_report, validate_config  # type: ignore[no-redef]
    from utils import json_safe  # type: ignore[no-redef]
    from visual_report import render_html_report  # type: ignore[no-redef]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="B10 因子评估每日调度入口")
    parser.add_argument("--input", required=True, help="标准评价面板路径，支持 CSV/Parquet/XLSX")
    parser.add_argument("--target-id", required=True, help="本次评估对象 ID，写入 result/HTML")
    parser.add_argument("--stock-pool", default="all_a", help="股票池：all_a/hs300/zz500/zz1000/zz2000")
    parser.add_argument("--group-mode", default="quintile", choices=["quintile", "decile", "5", "10", "五分组", "十分组"])
    parser.add_argument("--factor-direction", default="positive", choices=["positive", "negative", "auto"])
    parser.add_argument("--target-kind", default="return", choices=["return", "binary_success"])
    parser.add_argument("--annualization-factor", type=float, default=252.0)
    parser.add_argument("--data-version", default="b10-daily-v1")
    parser.add_argument("--output", default="../生产产物/数据库.parquet", help="生产 Parquet 路径")
    parser.add_argument(
        "--mode",
        default="append",
        choices=["append", "overwrite"],
        help="写入模式，默认 append（按主键 upsert）",
    )
    parser.add_argument("--report-dir", default="reports/daily", help="HTML 报告输出目录")
    parser.add_argument(
        "--no-report",
        action="store_true",
        help="跳过 HTML 报告，仅写入生产 Parquet（用于纯调度场景）",
    )
    parser.add_argument("--log-file", default=None, help="日志文件路径，默认输出到 stderr")
    parser.add_argument("--log-level", default="INFO", help="日志级别 DEBUG/INFO/WARNING/ERROR")
    return parser


def _setup_logging(level: str, log_file: str | None) -> None:
    fmt = "%(asctime)s [%(levelname)s] %(name)s | %(message)s"
    handlers: list[logging.Handler] = []
    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))
    handlers.append(logging.StreamHandler(sys.stderr))
    logging.basicConfig(level=getattr(logging, level.upper(), logging.INFO), format=fmt, handlers=handlers, force=True)
    build_logger.setLevel(getattr(logging, level.upper(), logging.INFO))


def _build_config(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "target_id": args.target_id,
        "stock_pool": args.stock_pool,
        "group_mode": args.group_mode,
        "factor_direction": args.factor_direction,
        "target_kind": args.target_kind,
        "annualization_factor": args.annualization_factor,
        "data_version": args.data_version,
        "update_time": datetime.now().isoformat(timespec="seconds"),
    }


def _select_current_result_row(result: pd.DataFrame, config: dict[str, Any]) -> pd.Series:
    """append 模式返回的是合并后全库；日志/报告文件名应使用本次 target 的记录。"""
    target_id = str(config.get("target_id", "factor_evaluation_report"))
    result_type = str(config.get("result_type", "factor_evaluation_report"))
    current = result.loc[
        result["target_id"].astype(str).eq(target_id)
        & result["result_type"].astype(str).eq(result_type)
    ].copy()
    if current.empty:
        return result.iloc[-1]
    if "update_time" in current.columns:
        current = current.sort_values("update_time")
    return current.iloc[-1]


def _build_result_row(report: dict[str, Any], config: dict[str, Any]) -> pd.DataFrame:
    """把 make_report 输出包成 BUILD schema 一行结果表。

    口径与 build.run 完全一致：result_value = summary.rank_ic、source_data_date =
    summary.end_date、result_json = json.dumps(json_safe(report))。抽出来是为了
    daily_runner 不再调 build.run 二次评估。
    """
    summary = report["summary"]
    target_id = str(config.get("target_id", "factor_evaluation_report"))
    result_type = str(config.get("result_type", "factor_evaluation_report"))
    data_version = str(config.get("data_version", "factor-eval-v1.3"))
    update_time = str(config.get("update_time", datetime.now().isoformat(timespec="seconds")))
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
    return out


def _write_production_atomic(fresh: pd.DataFrame, output_path: Path, mode: str) -> pd.DataFrame:
    """把已经 evaluate 出来的 fresh 行写入生产 Parquet。

    与 build.write_production 等价语义，但不再二次跑 run()——daily_runner 已经
    在外面跑过一次 make_report。
    """
    if mode not in {"overwrite", "append"}:
        raise ValueError(f"mode 必须是 'overwrite' 或 'append'，收到: {mode!r}")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fresh = validate_output(fresh)

    if mode == "append":
        existing = _read_existing_production(output_path)
        if not existing.empty:
            keep_mask = ~existing.set_index(PRIMARY_KEY).index.isin(fresh.set_index(PRIMARY_KEY).index)
            preserved = existing.loc[keep_mask].copy()
            merged = pd.concat([preserved, fresh], ignore_index=True)
        else:
            merged = fresh
        merged = merged.sort_values(PRIMARY_KEY).reset_index(drop=True)
        if merged.duplicated(PRIMARY_KEY).any():
            raise RuntimeError("append 后生产 Parquet 主键重复，写入被中止")
        validate_output(merged)
        final = merged
    else:
        final = fresh

    tmp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    try:
        final.to_parquet(tmp_path, index=False)
    except ImportError as exc:
        raise RuntimeError("写入 Parquet 需要安装 pyarrow 或 fastparquet") from exc
    tmp_path.replace(output_path)
    return final


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    _setup_logging(args.log_level, args.log_file)
    log = logging.getLogger("b10.daily_runner")

    input_path = Path(args.input)
    if not input_path.exists():
        log.error("输入文件不存在: %s", input_path)
        return 2

    config = _build_config(args)
    log.info("加载评价面板: %s", input_path)
    log.info("评估配置: %s", json.dumps({k: v for k, v in config.items() if k != "update_time"}, ensure_ascii=False))

    # 单次 evaluate：先 validate 输入面板，再跑一次 make_report，结果复用给生产库
    # 写入和 HTML 渲染。老版本两段路径各自重新调 evaluate，研究面板上多花一倍时间。
    try:
        validated_config = validate_config(config)
        panel = validate_input(str(input_path), validated_config)
        report = make_report(panel, validated_config)
    except Exception as exc:
        log.exception("evaluate 失败: %s", exc)
        return 1

    fresh_row = _build_result_row(report, config)

    try:
        result = _write_production_atomic(fresh_row, Path(args.output), args.mode)
    except Exception as exc:
        log.exception("write_production 失败: %s", exc)
        return 1

    current_row = _select_current_result_row(result, config)
    end_date = str(current_row["trade_date"])
    log.info(
        "B10 write_production: path=%s mode=%s rows=%d (this batch=%d)",
        Path(args.output),
        args.mode,
        len(result),
        len(fresh_row),
    )
    log.info("生产 Parquet 写入成功: rows=%d end_date=%s", len(result), end_date)

    if not args.no_report:
        report_dir = Path(args.report_dir)
        report_dir.mkdir(parents=True, exist_ok=True)
        safe_target = args.target_id.replace("/", "_").replace("\\", "_")
        report_path = report_dir / f"{safe_target}_{end_date}.html"
        try:
            html = render_html_report(json_safe(report), validated_config)
            report_path.write_text(html, encoding="utf-8")
            log.info("HTML 报告写入成功: %s", report_path)
        except Exception as exc:
            log.exception("HTML 报告生成失败（生产 Parquet 已写入，不影响主流程）: %s", exc)
            return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
