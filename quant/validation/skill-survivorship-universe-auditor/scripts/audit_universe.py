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
    try:
        with open(path, "r", encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
    except (OSError, UnicodeError, csv.Error) as exc:
        _INPUT_ISSUES.append({"reason": "input_read_error", "error_type": type(exc).__name__})
        return _demo_rows(demo_rows)
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


def finite_number(value: object) -> float | None:
    try:
        parsed = float(value)
        return parsed if math.isfinite(parsed) else None
    except (TypeError, ValueError):
        return None


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
    input_summary = {} if evidence_issues else {key: result[key] for key in count_keys if key in result}
    metrics = {} if evidence_issues else {
        key: value for key, value in result.items()
        if not key.startswith("_") and not isinstance(value, (list, dict)) and key != "passed"
    }
    domain_result: dict[str, object] = {"analysis_skipped": True} if evidence_issues else result
    report = {
        "status": status,
        "input_summary": input_summary,
        "assumptions": result.get("_assumptions", {"membership_rule": "not supplied"}),
        "metrics": metrics,
        "findings": findings,
        "limitations": result.get("_limitations", [
            "The audit can only assess lifecycle and membership rows supplied in the input."
        ]),
        "next_actions": ["Supply valid required fields or parameters and rerun."] if evidence_issues else (
            result.get("_next_actions", ["Correct lifecycle or membership rows and rerun."])
            if findings else []
        ),
        "domain_result": domain_result,
    }
    return _json_safe(report)  # type: ignore[return-value]


def emit(result: dict[str, object], out: str | None) -> None:
    payload = json.dumps(build_report(result), ensure_ascii=False, indent=2, allow_nan=False)
    if out:
        try:
            Path(out).write_text(payload + "\n", encoding="utf-8")
        except OSError as exc:
            error_result = {"_parameter_errors": [{"reason": "output_write_error", "error_type": type(exc).__name__}]}
            print(json.dumps(build_report(error_result), ensure_ascii=False, indent=2, allow_nan=False))
    else:
        print(payload)

DEMO = [
    {"symbol": "AAA", "date": "2024-01-31", "eligible": "1", "listed_at": "2020-01-01", "delisted_at": "", "return": "0.03", "delisting_return": ""},
    {"symbol": "DEAD", "date": "2024-03-29", "eligible": "1", "listed_at": "2018-01-01", "delisted_at": "2024-03-29", "return": "", "delisting_return": ""},
    {"symbol": "LATE", "date": "2023-12-29", "eligible": "1", "listed_at": "2024-02-01", "delisted_at": "", "return": "0.02", "delisting_return": ""},
]

REQUIRED_COLUMNS = {'date', 'delisted_at', 'delisting_return', 'eligible', 'listed_at', 'return', 'symbol'}
NUMERIC_COLUMNS = {'delisting_return', 'eligible', 'return'}
OPTIONAL_NUMERIC_COLUMNS = {'delisting_return', 'return'}


def day(value: str, *, optional: bool = False) -> datetime | None:
    if optional and not value:
        return None
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("date must use YYYY-MM-DD")
    return datetime.strptime(value, "%Y-%m-%d")


def analyze(rows: list[dict[str, str]]) -> dict[str, object]:
    errors: list[object] = []
    normalized_rows: list[dict[str, object]] = []
    seen_identity_dates: set[tuple[str, str]] = set()
    seen_symbol_dates: set[tuple[str, str]] = set()
    stable_ids_by_symbol: dict[str, set[str]] = {}
    if not rows:
        errors.append("at least one membership observation is required")
    for row_number, row in enumerate(rows, 2):
        symbol = text(row.get("symbol")).strip()
        stable_id = text(row.get("stable_id")).strip()
        eligible = text(row.get("eligible")).strip()
        date_value = text(row.get("date"))
        listed_value = text(row.get("listed_at"))
        delisted_value = text(row.get("delisted_at"))
        identity = stable_id or symbol
        if not symbol:
            errors.append({"reason": "empty_symbol", "row": row_number})
        if eligible not in {"0", "1"}:
            errors.append({"reason": "eligible_must_be_binary", "row": row_number, "value": eligible})
        try:
            date = day(date_value)
            listed = day(listed_value)
            delisted = day(delisted_value, optional=True)
        except ValueError as exc:
            errors.append({"reason": "invalid_date", "row": row_number, "message": str(exc)})
            continue
        if listed and delisted and listed > delisted:
            errors.append({"reason": "listing_after_delisting", "row": row_number})
        identity_date = (identity, date_value)
        symbol_date = (symbol, date_value)
        if identity_date in seen_identity_dates:
            errors.append({"reason": "duplicate_identity_date", "row": row_number, "identity": identity, "date": date_value})
        seen_identity_dates.add(identity_date)
        if symbol_date in seen_symbol_dates:
            errors.append({"reason": "duplicate_symbol_date", "row": row_number, "symbol": symbol, "date": date_value})
        seen_symbol_dates.add(symbol_date)
        stable_ids_by_symbol.setdefault(symbol, set()).add(stable_id)
        parsed_returns: dict[str, float | None] = {}
        for column in ("return", "delisting_return"):
            raw_value = row.get(column)
            if raw_value in (None, ""):
                parsed_returns[column] = None
                continue
            parsed = finite_number(raw_value)
            if parsed is None or parsed < -1:
                errors.append({"reason": "invalid_return", "row": row_number, "column": column})
            parsed_returns[column] = parsed
        normalized_rows.append({
            "symbol": symbol,
            "stable_id": stable_id,
            "identity": identity,
            "date_text": date_value,
            "date": date,
            "eligible": eligible,
            "listed_text": listed_value,
            "listed": listed,
            "delisted_text": delisted_value,
            "delisted": delisted,
            **parsed_returns,
        })
    lifecycle_by_identity: dict[str, set[tuple[str, str]]] = {}
    for row in normalized_rows:
        lifecycle_by_identity.setdefault(str(row["identity"]), set()).add((str(row["listed_text"]), str(row["delisted_text"])))
    for identity, lifecycles in lifecycle_by_identity.items():
        if len(lifecycles) > 1:
            errors.append({"reason": "inconsistent_lifecycle_metadata", "identity": identity})
    for symbol, stable_ids in stable_ids_by_symbol.items():
        if symbol and len(stable_ids) > 1:
            errors.append({"reason": "inconsistent_stable_id_mapping", "symbol": symbol})
    if errors:
        return {"_parameter_errors": errors}

    findings: list[dict[str, object]] = []
    point_in_time: dict[str, list[str]] = {}
    delisting_bias_pairs: list[tuple[float, float]] = []
    for row in normalized_rows:
        date = row["date"]
        listed = row["listed"]
        delisted = row["delisted"]
        date_text = str(row["date_text"])
        point_in_time.setdefault(date_text, [])
        lifecycle_reasons: list[str] = []
        return_reasons: list[str] = []
        if date < listed and row["eligible"] == "1":
            lifecycle_reasons.append("eligible_before_listing")
        if delisted and date > delisted and row["eligible"] == "1":
            lifecycle_reasons.append("eligible_after_delisting")
        is_valid_member = row["eligible"] == "1" and not lifecycle_reasons
        if is_valid_member and delisted and date == delisted and row["delisting_return"] is None:
            return_reasons.append("missing_delisting_return")
        if is_valid_member and delisted and date == delisted and row["return"] is None:
            return_reasons.append("missing_ordinary_return")
        if is_valid_member:
            point_in_time[date_text].append(str(row["symbol"]))
        if (
            is_valid_member
            and delisted
            and date == delisted
            and row["return"] is not None
            and row["delisting_return"] is not None
        ):
            delisting_bias_pairs.append((float(row["return"]), float(row["delisting_return"])))
        reasons = lifecycle_reasons + return_reasons
        if reasons:
            findings.append({"symbol": row["symbol"], "date": row["date_text"], "reasons": reasons})

    for symbols_on_date in point_in_time.values():
        symbols_on_date.sort()
    point_in_time = dict(sorted(point_in_time.items()))
    symbols = {str(r["identity"]) for r in normalized_rows}
    delisted_symbols = {str(r["identity"]) for r in normalized_rows if r["delisted"]}
    bias_estimate = None
    if delisting_bias_pairs:
        try:
            bias_estimate = math.fsum(ordinary - delisting for ordinary, delisting in delisting_bias_pairs) / len(delisting_bias_pairs)
        except OverflowError:
            return {"_parameter_errors": ["delisting bias estimate must be finite"]}
        if not math.isfinite(bias_estimate):
            return {"_parameter_errors": ["delisting bias estimate must be finite"]}
    has_stable_id = bool(normalized_rows) and all(row["stable_id"] for row in normalized_rows)
    limitations = [
        "The point-in-time universe is reconstructed only for dates explicitly present in the input.",
        "Missing securities cannot be detected without a complete historical security master or benchmark membership source.",
        "Delisting-return bias is quantified only when both ordinary and delisting returns are supplied on the delisting date.",
    ]
    if not has_stable_id:
        limitations.append(
            "stable_id is absent, so ticker or identifier changes cannot be linked reliably."
        )
    return {
        "rows": len(rows),
        "symbols": len(symbols),
        "delisted_symbols": len(delisted_symbols),
        "point_in_time_universe": point_in_time,
        "delisting_bias_observations": len(delisting_bias_pairs),
        "mean_return_overstatement_without_delisting_return": bias_estimate,
        "findings": findings,
        "passed": not findings,
        "_assumptions": {
            "eligible_encoding": "0 or 1",
            "membership_grain": "one symbol-date row",
            "lifecycle_boundaries": "listing and delisting dates are inclusive",
        },
        "_limitations": limitations,
        "_next_actions": [
            "Correct lifecycle violations and supply missing delisting returns from an authoritative source.",
            "Add stable_id and complete historical snapshots before claiming the universe is survivorship-bias-free.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit historical universes for survivorship and delisting bias.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input")
    source.add_argument("--demo", action="store_true")
    parser.add_argument("--out")
    args = parser.parse_args()
    emit(analyze(load_rows(args.input, DEMO)), args.out)


if __name__ == "__main__": main()
