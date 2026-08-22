from __future__ import annotations

import argparse
import csv
import json
import math
import re
from datetime import datetime
from pathlib import Path


_INPUT_ISSUES: list[dict[str, object]] = []


def _demo_rows(demo_rows: list[dict[str, object]]) -> list[dict[str, str]]:
    return [{k: str(v) for k, v in row.items()} for row in demo_rows]


def load_rows(path: str | None, demo_rows: list[dict[str, object]]) -> list[dict[str, str]]:
    _INPUT_ISSUES.clear()
    if path is None:
        return _demo_rows(demo_rows)
    with open(path, "r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    required = set(globals().get("REQUIRED_COLUMNS", set(demo_rows[0]) if demo_rows else set()))
    numeric_columns = set(globals().get("NUMERIC_COLUMNS", set()))
    optional_numeric = set(globals().get("OPTIONAL_NUMERIC_COLUMNS", set()))
    actual = set(rows[0]) if rows else set()
    missing = sorted(required - actual)
    if not rows:
        _INPUT_ISSUES.append({"reason": "empty_input", "required_columns": sorted(required)})
    if missing:
        _INPUT_ISSUES.append({"reason": "missing_columns", "columns": missing})
    for row_number, row in enumerate(rows, 2):
        for key in numeric_columns:
            value = row.get(key)
            if value in (None, "") and key in optional_numeric:
                continue
            try:
                parsed = float(value) if value not in (None, "") else math.nan
            except (TypeError, ValueError):
                parsed = math.nan
            if not math.isfinite(parsed):
                _INPUT_ISSUES.append({"reason": "invalid_numeric", "row": row_number, "column": key, "value": value})
    if _INPUT_ISSUES:
        return _demo_rows(demo_rows)
    return rows


def number(value: object, default: float = 0.0) -> float:
    try:
        parsed = float(value)
        return parsed if math.isfinite(parsed) else default
    except (TypeError, ValueError):
        return default


def text(value: object) -> str:
    return value if isinstance(value, str) else ""


def _normalize_finding(item: object, index: int, source: str) -> dict[str, object]:
    if isinstance(item, dict):
        evidence = item.get("evidence", item)
        severity = item.get("severity", "medium")
        finding_id = item.get("id", f"{source}-{index}")
        impact = item.get("impact", "Review the domain result and confirm whether the issue changes the research conclusion.")
        recommended_fix = item.get("recommended_fix", "Inspect the cited record, correct the input or assumptions, and rerun the check.")
    else:
        evidence = item
        severity = "medium"
        finding_id = f"{source}-{index}"
        impact = "The detected condition may affect the reliability of the quantitative result."
        recommended_fix = "Review the condition, document the decision, and rerun after correction when applicable."
    return {
        "id": finding_id,
        "severity": severity,
        "evidence": evidence,
        "impact": impact,
        "recommended_fix": recommended_fix,
    }


def _json_safe(value: object) -> object:
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    return value


def build_report(result: dict[str, object]) -> dict[str, object]:
    evidence_issues = list(_INPUT_ISSUES)
    parameter_errors = result.get("_parameter_errors", [])
    if parameter_errors:
        evidence_issues.extend(parameter_errors if isinstance(parameter_errors, list) else [parameter_errors])

    issue_keys = ("findings", "violations", "warnings", "flags", "timing_findings")
    findings: list[dict[str, object]] = []
    if evidence_issues:
        findings.extend(_normalize_finding(item, index, "insufficient-evidence") for index, item in enumerate(evidence_issues, 1))
    else:
        for key in issue_keys:
            value = result.get(key)
            if value in (None, "", [], {}):
                continue
            values = value if isinstance(value, list) else [value]
            findings.extend(_normalize_finding(item, index, key) for index, item in enumerate(values, 1))
    passed = result.get("passed")
    if evidence_issues:
        status = "insufficient-evidence"
    elif passed is False:
        status = "fail"
    elif findings:
        status = "warning"
    else:
        status = "pass"

    count_keys = ("rows", "records", "orders", "events", "quotes", "symbols", "simulations", "baseline_count", "current_count")
    input_summary = {key: result[key] for key in count_keys if key in result}
    metrics = {
        key: value for key, value in result.items()
        if not key.startswith("_") and not isinstance(value, (list, dict)) and key != "passed"
    }
    domain_result: dict[str, object] = {"analysis_skipped": True} if evidence_issues else result
    report = {
        "status": status,
        "input_summary": input_summary,
        "assumptions": result.get("_assumptions", {"event_scope": "not supplied"}),
        "metrics": metrics,
        "findings": findings,
        "limitations": result.get("_limitations", [
            "This script covers split and cash-dividend consistency only."
        ]),
        "next_actions": ["Supply valid required fields or parameters and rerun."] if evidence_issues else (
            result.get("_next_actions", ["Reconcile flagged dates against an authoritative corporate-action ledger."])
            if findings else []
        ),
        "domain_result": domain_result,
    }
    return _json_safe(report)  # type: ignore[return-value]


def emit(result: dict[str, object], out: str | None) -> None:
    payload = json.dumps(build_report(result), ensure_ascii=False, indent=2, allow_nan=False)
    if out:
        Path(out).write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)

DEMO = [
    {"symbol": "AAA", "date": "2024-01-01", "close": "100", "adj_close": "50", "split_factor": "1", "cash_dividend": "0"},
    {"symbol": "AAA", "date": "2024-01-02", "close": "50", "adj_close": "50", "split_factor": "2", "cash_dividend": "0"},
    {"symbol": "AAA", "date": "2024-01-03", "close": "80", "adj_close": "80", "split_factor": "1", "cash_dividend": "0"},
]

REQUIRED_COLUMNS = {'adj_close', 'cash_dividend', 'close', 'date', 'split_factor', 'symbol'}
NUMERIC_COLUMNS = {'adj_close', 'cash_dividend', 'close', 'split_factor'}
OPTIONAL_NUMERIC_COLUMNS = set()


def analyze(
    rows: list[dict[str, str]],
    return_tolerance: float = 0.02,
    jump_threshold: float = 0.40,
) -> dict[str, object]:
    errors: list[object] = []
    if not rows:
        errors.append("at least two rows for one symbol are required")
    if not math.isfinite(return_tolerance) or return_tolerance < 0:
        errors.append("return-tolerance must be finite and non-negative")
    if not math.isfinite(jump_threshold) or jump_threshold <= 0:
        errors.append("jump-threshold must be finite and positive")
    seen: set[tuple[str, str]] = set()
    symbol_counts: dict[str, int] = {}
    for row_number, row in enumerate(rows, 2):
        raw_symbol = text(row.get("symbol"))
        symbol = raw_symbol.strip()
        date_value = text(row.get("date"))
        key = (symbol, date_value)
        symbol_counts[symbol] = symbol_counts.get(symbol, 0) + 1
        if not symbol:
            errors.append({"reason": "empty_symbol", "row": row_number})
        elif raw_symbol != symbol:
            errors.append({"reason": "symbol_surrounding_whitespace", "row": row_number})
        try:
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date_value):
                raise ValueError("date must use YYYY-MM-DD")
            datetime.strptime(date_value, "%Y-%m-%d")
        except ValueError:
            errors.append({"reason": "invalid_date", "row": row_number})
        if key in seen:
            errors.append({"reason": "duplicate_symbol_date", "row": row_number})
        seen.add(key)
        if number(row.get("split_factor")) <= 0:
            errors.append({"reason": "non_positive_split_factor", "row": row_number})
        if number(row.get("cash_dividend")) < 0:
            errors.append({"reason": "negative_cash_dividend", "row": row_number})
        if number(row.get("close")) <= 0 or number(row.get("adj_close")) <= 0:
            errors.append({"reason": "non_positive_price", "row": row_number})
    for symbol, count in symbol_counts.items():
        if symbol and count < 2:
            errors.append({"reason": "insufficient_symbol_history", "symbol": symbol, "rows": count})
    if errors:
        return {"_parameter_errors": errors}

    findings: list[dict[str, object]] = []
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        grouped.setdefault(text(row.get("symbol")).strip(), []).append(row)
    for symbol, items in grouped.items():
        items.sort(key=lambda x: x.get("date", ""))
        for prev, cur in zip(items, items[1:]):
            p0, p1 = number(prev.get("close")), number(cur.get("close"))
            a0, a1 = number(prev.get("adj_close")), number(cur.get("adj_close"))
            split = number(cur.get("split_factor"), 1.0)
            reasons: list[str] = []
            if p0 and abs(p1 / p0 - 1) > jump_threshold and split == 1 and number(cur.get("cash_dividend")) == 0:
                reasons.append("large_unexplained_raw_price_jump")
            raw_ret = (p1 * split + number(cur.get("cash_dividend"))) / p0 - 1 if p0 else 0
            adj_ret = a1 / a0 - 1 if a0 else 0
            if abs(raw_ret - adj_ret) > return_tolerance: reasons.append("adjusted_return_mismatch")
            if reasons: findings.append({"symbol": symbol, "date": cur.get("date"), "reasons": reasons,
                                         "raw_total_return": raw_ret, "adjusted_return": adj_ret})
    return {
        "rows": len(rows),
        "symbols": len(grouped),
        "findings": findings,
        "passed": not findings,
        "_assumptions": {
            "return_tolerance": return_tolerance,
            "jump_threshold": jump_threshold,
            "split_factor_convention": "new shares per old share on the current row",
            "cash_dividend_timing": "cash dividend belongs to the current row ex-date",
        },
        "_limitations": [
            "The executable check covers cash dividends, splits/reverse splits, raw close and adjusted close.",
            "Rights issues, spin-offs, mergers, symbol changes and share-count adjustments require additional event fields and remain unverified.",
            "Vendor adjustment-factor direction must be mapped to the stated split convention before use.",
        ],
        "_next_actions": [
            "Reconcile each mismatch against an authoritative event ledger and vendor adjustment-factor history.",
            "Treat complex events outside the input schema as insufficient evidence, not as a pass.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit corporate-action price adjustments.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input")
    source.add_argument("--demo", action="store_true")
    parser.add_argument("--out")
    parser.add_argument("--return-tolerance", type=float, default=0.02)
    parser.add_argument("--jump-threshold", type=float, default=0.40)
    args = parser.parse_args()
    emit(analyze(
        load_rows(args.input, DEMO),
        args.return_tolerance,
        args.jump_threshold,
    ), args.out)


if __name__ == "__main__": main()
