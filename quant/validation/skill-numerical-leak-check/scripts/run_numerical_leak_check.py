#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import os
import random
import sys
import time
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any


DEFAULT_RATIOS = (0.10, 0.20, 0.25, 0.30, 0.40, 0.50, 0.70, 0.82, 0.93)
DEFAULT_FIXED = (20, 40, 60, 80, 120, 160, 200, 240, 250, 252, 300, 400, 500)
NEIGHBOR_OFFSETS = (-10, -5, -3, -2, -1, 0, 1, 2, 3, 5, 10)
STATUS_PRIORITY = {"ERROR": 4, "FAIL": 3, "WARN": 2, "PASS": 1}


def load_json_arg(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    path = Path(value)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return json.loads(value)


def load_adapter(path: str):
    adapter_path = Path(path).resolve()
    name = f"numerical_leak_adapter_{abs(hash(str(adapter_path))) & 0xFFFFFFFF:x}"
    spec = importlib.util.spec_from_file_location(name, adapter_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot import adapter: {adapter_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def call_required(adapter: Any, name: str, *args: Any) -> Any:
    func = getattr(adapter, name, None)
    if not callable(func):
        raise AttributeError(f"adapter must define {name}()")
    return func(*args)


def get_case_id(adapter: Any, case: dict[str, Any]) -> str:
    func = getattr(adapter, "case_id", None)
    if callable(func):
        return str(func(case))
    for key in ("case_id", "id", "name", "path"):
        value = case.get(key)
        if value:
            return Path(str(value)).stem if key == "path" else str(value)
    return "case"


def infer_input_length(adapter: Any, input_obj: Any, case: dict[str, Any], config: dict[str, Any]) -> int:
    func = getattr(adapter, "input_length", None)
    if callable(func):
        return int(func(input_obj, case, config))
    if hasattr(input_obj, "__len__"):
        return int(len(input_obj))
    raise AttributeError("adapter must define input_length() when input object has no len()")


def int_list(value: Any) -> list[int]:
    if value is None:
        return []
    if isinstance(value, str):
        raw = [x.strip() for x in value.split(",") if x.strip()]
    elif isinstance(value, (list, tuple, set)):
        raw = list(value)
    else:
        raw = [value]
    out: list[int] = []
    for item in raw:
        try:
            out.append(int(item))
        except Exception:
            continue
    return out


def default_checkpoints(rows: int, case: dict[str, Any], config: dict[str, Any]) -> list[int]:
    candidates: set[int] = {int(rows * ratio) for ratio in config.get("checkpoint_ratios", DEFAULT_RATIOS)}
    candidates.update(int_list(config.get("fixed_checkpoints", list(DEFAULT_FIXED))))
    candidates.update(int_list(case.get("checkpoints")))
    candidates.update(int_list(config.get("checkpoints")))

    sensitive: list[int] = []
    for source in (
        case.get("sensitive_points"),
        case.get("periods"),
        case.get("windows"),
        case.get("warmups"),
        config.get("sensitive_points"),
        config.get("periods"),
        config.get("windows"),
        config.get("warmups"),
    ):
        sensitive.extend(int_list(source))

    for value in sensitive:
        for multiplier in (1, 2, 3):
            anchor = value * multiplier
            for offset in NEIGHBOR_OFFSETS:
                candidates.add(anchor + offset)

    strict_ranges = config.get("strict_ranges") or case.get("strict_ranges") or []
    for item in strict_ranges:
        if isinstance(item, dict):
            start, end = int(item["start"]), int(item["end"])
        else:
            start, end = int(item[0]), int(item[1])
        candidates.update(range(start, end + 1))

    random_cuts = int(config.get("random_checkpoints", 0) or 0)
    if random_cuts > 0 and rows > 10:
        rng = random.Random(int(config.get("seed", 20260709)))
        candidates.update(rng.randrange(5, rows - 1) for _ in range(random_cuts))

    return sorted(x for x in candidates if 1 <= x < rows - 1)


def choose_checkpoints(adapter: Any, input_obj: Any, case: dict[str, Any], config: dict[str, Any]) -> list[int]:
    func = getattr(adapter, "choose_checkpoints", None)
    if callable(func):
        checkpoints = [int(x) for x in func(input_obj, case, config)]
    else:
        rows = infer_input_length(adapter, input_obj, case, config)
        checkpoints = default_checkpoints(rows, case, config)
    limit = config.get("max_checkpoints")
    if limit is not None and len(checkpoints) > int(limit):
        checkpoints = checkpoints[: int(limit)]
    if not checkpoints:
        raise ValueError("no checkpoints selected")
    return checkpoints


def normalize_compare_result(raw: Any) -> dict[str, Any]:
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise TypeError("compare_outputs() must return a dict")
    out = dict(raw)
    out["max_abs_diff"] = float(out.get("max_abs_diff", 0.0) or 0.0)
    out["bad_points"] = int(out.get("bad_points", 0) or 0)
    first_bad_idx = out.get("first_bad_idx", "")
    out["first_bad_idx"] = "" if first_bad_idx is None else str(first_bad_idx)
    return out


def status_from_compare(result: dict[str, Any], config: dict[str, Any]) -> str:
    if result.get("status"):
        return str(result["status"]).upper()
    atol = float(config.get("atol", 1e-8))
    warn_atol = float(config.get("warn_atol", max(1e-5, atol * 1000)))
    max_abs_diff = float(result.get("max_abs_diff", 0.0) or 0.0)
    bad_points = int(result.get("bad_points", 0) or 0)
    if bad_points <= 0 and max_abs_diff <= atol:
        return "PASS"
    if max_abs_diff <= warn_atol:
        return "WARN"
    return "FAIL"


def run_case(job: dict[str, Any]) -> dict[str, Any]:
    adapter = load_adapter(job["adapter"])
    config = dict(job["config"])
    case = dict(job["case"])
    setup = getattr(adapter, "setup_worker", None)
    if callable(setup):
        setup(config)

    case_name = get_case_id(adapter, case)
    started = time.perf_counter()
    rows: list[dict[str, Any]] = []
    base = {"case_id": case_name}

    try:
        input_obj = call_required(adapter, "load_input", case, config)
        checkpoints = choose_checkpoints(adapter, input_obj, case, config)
        full_output = call_required(adapter, "run_target", input_obj, case, config)
    except Exception as exc:
        return {
            "case_id": case_name,
            "case_status": "ERROR",
            "rows": [
                {
                    **base,
                    "status": "ERROR",
                    "test_type": "setup",
                    "cut": "",
                    "max_abs_diff": "",
                    "bad_points": "",
                    "first_bad_idx": "",
                    "error": f"{type(exc).__name__}: {exc}",
                    "traceback": traceback.format_exc(),
                    "elapsed_sec": time.perf_counter() - started,
                }
            ],
        }

    for cut in checkpoints:
        for test_type in ("prefix", "mutation"):
            row_started = time.perf_counter()
            try:
                if test_type == "prefix":
                    test_input = call_required(adapter, "make_prefix", input_obj, cut, case, config)
                else:
                    test_input = call_required(adapter, "mutate_future", input_obj, cut, case, config)
                test_output = call_required(adapter, "run_target", test_input, case, config)
                cmp_result = normalize_compare_result(
                    call_required(adapter, "compare_outputs", full_output, test_output, cut, case, config)
                )
                status = status_from_compare(cmp_result, config)
                rows.append(
                    {
                        **base,
                        "status": status,
                        "test_type": test_type,
                        "cut": int(cut),
                        "max_abs_diff": cmp_result.get("max_abs_diff", 0.0),
                        "bad_points": cmp_result.get("bad_points", 0),
                        "first_bad_idx": cmp_result.get("first_bad_idx", ""),
                        "compared_points": cmp_result.get("compared_points", ""),
                        "notes": cmp_result.get("notes", ""),
                        "error": "",
                        "elapsed_sec": time.perf_counter() - row_started,
                    }
                )
            except Exception as exc:
                rows.append(
                    {
                        **base,
                        "status": "ERROR",
                        "test_type": test_type,
                        "cut": int(cut),
                        "max_abs_diff": "",
                        "bad_points": "",
                        "first_bad_idx": "",
                        "compared_points": "",
                        "notes": "",
                        "error": f"{type(exc).__name__}: {exc}",
                        "traceback": traceback.format_exc(),
                        "elapsed_sec": time.perf_counter() - row_started,
                    }
                )

    worst = max((str(row["status"]) for row in rows), key=lambda status: STATUS_PRIORITY.get(status, 0))
    return {"case_id": case_name, "case_status": worst, "rows": rows, "elapsed_sec": time.perf_counter() - started}


def discover_cases(adapter_path: str, config: dict[str, Any]) -> list[dict[str, Any]]:
    adapter = load_adapter(adapter_path)
    func = getattr(adapter, "discover_cases", None)
    if callable(func):
        cases = func(config)
    else:
        cases = [dict(config.get("case", {}))]
    if not isinstance(cases, list):
        raise TypeError("discover_cases() must return a list of dicts")
    return [dict(case) for case in cases]


def summarize(all_rows: list[dict[str, Any]], case_results: list[dict[str, Any]], elapsed_sec: float) -> dict[str, Any]:
    status_counts: dict[str, int] = {}
    for result in case_results:
        status = str(result.get("case_status", "UNKNOWN"))
        status_counts[status] = status_counts.get(status, 0) + 1

    row_status_counts: dict[str, int] = {}
    for row in all_rows:
        status = str(row.get("status", "UNKNOWN"))
        row_status_counts[status] = row_status_counts.get(status, 0) + 1

    return {
        "cases": len(case_results),
        "rows": len(all_rows),
        "case_status_counts": status_counts,
        "row_status_counts": row_status_counts,
        "elapsed_sec": elapsed_sec,
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "case_id",
        "status",
        "test_type",
        "cut",
        "max_abs_diff",
        "bad_points",
        "first_bad_idx",
        "compared_points",
        "notes",
        "error",
        "elapsed_sec",
    ]
    extra = sorted({key for row in rows for key in row if key not in fieldnames and key != "traceback"})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=[*fieldnames, *extra])
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in [*fieldnames, *extra]})


def case_summary_rows(all_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_case: dict[str, list[dict[str, Any]]] = {}
    for row in all_rows:
        by_case.setdefault(str(row.get("case_id", "")), []).append(row)
    out: list[dict[str, Any]] = []
    for case_id, rows in sorted(by_case.items()):
        worst_status = max((str(row.get("status", "UNKNOWN")) for row in rows), key=lambda x: STATUS_PRIORITY.get(x, 0))
        worst_rows = [row for row in rows if str(row.get("status")) == worst_status]
        first = worst_rows[0] if worst_rows else rows[0]
        max_diff = 0.0
        bad_points = 0
        for row in rows:
            try:
                max_diff = max(max_diff, float(row.get("max_abs_diff") or 0.0))
            except Exception:
                pass
            try:
                bad_points += int(row.get("bad_points") or 0)
            except Exception:
                pass
        out.append(
            {
                "case_id": case_id,
                "worst_status": worst_status,
                "tests": len(rows),
                "worst_test_type": first.get("test_type", ""),
                "first_bad_cut": first.get("cut", ""),
                "first_bad_idx": first.get("first_bad_idx", ""),
                "max_abs_diff": max_diff,
                "bad_points": bad_points,
            }
        )
    return out


def markdown_table(rows: list[dict[str, Any]], columns: list[str], limit: int | None = None) -> str:
    shown = rows[:limit] if limit else rows
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    for row in shown:
        values = [str(row.get(col, "")) for col in columns]
        lines.append("| " + " | ".join(values) + " |")
    if limit and len(rows) > limit:
        values = ["..."] + ["" for _ in columns[1:]]
        if len(values) > 1:
            values[1] = f"还有 {len(rows) - limit} 行"
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def write_report(path: Path, summary: dict[str, Any], all_rows: list[dict[str, Any]], config: dict[str, Any]) -> None:
    case_rows = case_summary_rows(all_rows)
    issue_rows = [row for row in all_rows if str(row.get("status")) in {"WARN", "FAIL", "ERROR"}]
    status_rows = [
        {"status": key, "cases": value}
        for key, value in sorted(summary["case_status_counts"].items(), key=lambda item: STATUS_PRIORITY.get(item[0], 0), reverse=True)
    ]
    text = [
        "# 数值型未来泄露检查报告",
        "",
        "## 检查范围",
        "",
        f"- case 数量：{summary['cases']}",
        f"- 测试行数：{summary['rows']}",
        f"- 容忍度：{config.get('atol', 1e-8)}",
        f"- warn_atol：{config.get('warn_atol', max(1e-5, float(config.get('atol', 1e-8)) * 1000))}",
        "",
        "## 方法",
        "",
        "- Prefix replay：完整输入的历史输出必须等于只给历史前缀时的输出。",
        "- Future mutation：保留历史输入不变、替换未来输入后，历史输出不得变化。",
        "- Checkpoint：由 adapter 自定义或由 runner 根据比例、固定点、敏感点、随机点生成。",
        "",
        "## 总览",
        "",
        markdown_table(status_rows, ["status", "cases"]),
        "",
        "## Case 汇总",
        "",
        markdown_table(case_rows, ["case_id", "worst_status", "tests", "worst_test_type", "first_bad_cut", "max_abs_diff", "bad_points"], limit=200),
        "",
        "## FAIL/WARN/ERROR 明细",
        "",
    ]
    if issue_rows:
        text.append(markdown_table(issue_rows, ["case_id", "status", "test_type", "cut", "first_bad_idx", "max_abs_diff", "bad_points", "error"], limit=200))
    else:
        text.append("本次检查没有发现 WARN、FAIL 或 ERROR。")
    text.extend(
        [
            "",
            "## 稳健性和局限",
            "",
            "- PASS 只表示当前 adapter、输入、checkpoint、扰动和比较口径下没有发现未来泄露，不是形式化证明。",
            "- 若泄露只发生在极窄边界，需要围绕 period、warmup、session、resample 或历史失败位置做更密集 cut sweep。",
            "- 若真实生产依赖交易日历、换月、停复牌、成分变化、缓存或外部状态，adapter 需要尽量复现这些路径。",
            "",
        ]
    )
    path.write_text("\n".join(text), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generic numerical future-leakage checker.")
    parser.add_argument("--adapter", required=True, help="Path to a Python adapter implementing the leak-check contract.")
    parser.add_argument("--config", help="JSON string or path to JSON config.")
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--strict-exit", action="store_true", help="Exit 1 on WARN as well as FAIL/ERROR.")
    args = parser.parse_args()

    config = load_json_arg(args.config)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    cases = discover_cases(args.adapter, config)
    if not cases:
        raise SystemExit("no cases discovered")

    started = time.perf_counter()
    jobs = [{"adapter": str(Path(args.adapter).resolve()), "config": config, "case": case} for case in cases]
    case_results: list[dict[str, Any]] = []
    print(json.dumps({"stage": "leak_check_start", "cases": len(jobs), "workers": args.workers}, ensure_ascii=False))
    if args.workers <= 1:
        for job in jobs:
            result = run_case(job)
            case_results.append(result)
            print(json.dumps({"stage": "case_done", "case_id": result["case_id"], "status": result["case_status"]}, ensure_ascii=False))
    else:
        with ProcessPoolExecutor(max_workers=max(1, args.workers)) as executor:
            futures = {executor.submit(run_case, job): job for job in jobs}
            for future in as_completed(futures):
                result = future.result()
                case_results.append(result)
                print(json.dumps({"stage": "case_done", "case_id": result["case_id"], "status": result["case_status"]}, ensure_ascii=False))

    all_rows = [row for result in case_results for row in result.get("rows", [])]
    elapsed = time.perf_counter() - started
    summary = summarize(all_rows, case_results, elapsed)
    summary.update({"result_csv": str(args.out_dir / "leak_check_results.csv")})

    write_csv(args.out_dir / "leak_check_results.csv", all_rows)
    (args.out_dir / "leak_check_results.json").write_text(json.dumps(all_rows, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    (args.out_dir / "leak_check_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(args.out_dir / "leak_check_report.md", summary, all_rows, config)
    print(json.dumps({"stage": "leak_check_done", **summary}, ensure_ascii=False))

    bad_statuses = {"FAIL", "ERROR"}
    if args.strict_exit:
        bad_statuses.add("WARN")
    return 1 if any(str(result.get("case_status")) in bad_statuses for result in case_results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
