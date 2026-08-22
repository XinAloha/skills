from __future__ import annotations

import argparse
import csv
import json
import math
import re
import statistics
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
        _INPUT_ISSUES.append({
            "reason": "input_read_error",
            "error_type": type(exc).__name__,
        })
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
    input_summary = {key: result[key] for key in count_keys if key in result}
    metrics = {
        key: value for key, value in result.items()
        if not key.startswith("_") and not isinstance(value, (list, dict)) and key != "passed"
    }
    domain_result: dict[str, object] = {"analysis_skipped": True} if evidence_issues else result
    report = {
        "status": status,
        "input_summary": input_summary,
        "assumptions": result.get("_assumptions", {"event_window": "not supplied"}),
        "metrics": metrics,
        "findings": findings,
        "limitations": result.get("_limitations", [
            "Event-study estimates are descriptive and depend on event-date provenance."
        ]),
        "next_actions": ["Supply valid required fields or parameters and rerun."] if evidence_issues else (
            result.get("_next_actions", ["Verify event dates and rerun after correcting the panel."])
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
            error_result = {
                "_parameter_errors": [{
                    "reason": "output_write_error",
                    "error_type": type(exc).__name__,
                }]
            }
            print(json.dumps(
                build_report(error_result),
                ensure_ascii=False,
                indent=2,
                allow_nan=False,
            ))
    else:
        print(payload)

DEMO = [
    {"event_id": "A1", "symbol": "AAA", "action": "add", "announcement_date": "2024-01-01", "effective_date": "2024-01-10", "relative_day": "0", "return": "0.03", "benchmark_return": "0.005", "volume_ratio": "2.0"},
    {"event_id": "A1", "symbol": "AAA", "action": "add", "announcement_date": "2024-01-01", "effective_date": "2024-01-10", "relative_day": "1", "return": "0.01", "benchmark_return": "0.002", "volume_ratio": "1.5"},
    {"event_id": "D1", "symbol": "BBB", "action": "delete", "announcement_date": "2024-01-01", "effective_date": "2024-01-10", "relative_day": "0", "return": "-0.02", "benchmark_return": "0.004", "volume_ratio": "2.5"},
]

REQUIRED_COLUMNS = {'action', 'announcement_date', 'benchmark_return', 'effective_date', 'event_id', 'relative_day', 'return', 'symbol', 'volume_ratio'}
NUMERIC_COLUMNS = {'benchmark_return', 'relative_day', 'return', 'volume_ratio', 'weight_before', 'weight_after'}
OPTIONAL_NUMERIC_COLUMNS = {'weight_before', 'weight_after'}


def analyze(rows: list[dict[str, str]], start: int, end: int) -> dict[str, object]:
    if start > end:
        return {"_parameter_errors": ["start must be less than or equal to end"]}
    events: dict[tuple[str, str], list[dict[str, str]]] = {}
    errors: list[object] = []
    if not rows:
        errors.append("at least one event observation is required")
    valid_actions = {"add", "delete", "weight_change"}
    valid_anchors = {"announcement", "effective"}
    seen_observations: set[tuple[str, str, int]] = set()
    for row_number, row in enumerate(rows, 2):
        event_id = text(row.get("event_id")).strip()
        symbol = text(row.get("symbol")).strip()
        action = text(row.get("action")).strip()
        raw_anchor = text(row.get("relative_to")).strip()
        anchor = raw_anchor or "unspecified"
        announcement_value = text(row.get("announcement_date"))
        effective_value = text(row.get("effective_date"))
        if not event_id:
            errors.append({"reason": "empty_event_id", "row": row_number})
        if not symbol:
            errors.append({"reason": "empty_symbol", "row": row_number})
        if action not in valid_actions:
            errors.append({"reason": "unsupported_action", "row": row_number, "value": action})
        if raw_anchor and raw_anchor not in valid_anchors:
            errors.append({"reason": "invalid_relative_to", "row": row_number, "value": raw_anchor})
        try:
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", announcement_value):
                raise ValueError("announcement_date must use YYYY-MM-DD")
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", effective_value):
                raise ValueError("effective_date must use YYYY-MM-DD")
            announcement = datetime.strptime(announcement_value, "%Y-%m-%d")
            effective = datetime.strptime(effective_value, "%Y-%m-%d")
        except ValueError:
            errors.append({"reason": "invalid_event_date", "row": row_number})
            continue
        if announcement > effective:
            errors.append({"reason": "announcement_after_effective_date", "row": row_number})
        relative_day_value = finite_number(row.get("relative_day"))
        if relative_day_value is None or not relative_day_value.is_integer():
            errors.append({"reason": "invalid_relative_day", "row": row_number})
        else:
            relative_day = int(relative_day_value)
            observation_key = (event_id, anchor, relative_day)
            if observation_key in seen_observations:
                errors.append({"reason": "duplicate_event_anchor_day", "row": row_number})
            seen_observations.add(observation_key)
        for column in ("return", "benchmark_return", "volume_ratio"):
            value = finite_number(row.get(column))
            if value is None:
                errors.append({"reason": "invalid_numeric", "row": row_number, "column": column})
            elif column == "volume_ratio" and value < 0:
                errors.append({"reason": "negative_volume_ratio", "row": row_number})
        for column in ("weight_before", "weight_after"):
            value = row.get(column)
            if value not in (None, "") and finite_number(value) is None:
                errors.append({"reason": "invalid_optional_numeric", "row": row_number, "column": column})
        normalized_row = dict(row)
        normalized_row.update({
            "event_id": event_id,
            "symbol": symbol,
            "action": action,
            "relative_to": "" if anchor == "unspecified" else anchor,
            "announcement_date": announcement_value,
            "effective_date": effective_value,
        })
        events.setdefault((event_id, anchor), []).append(normalized_row)
    if errors:
        return {"_parameter_errors": errors}

    event_rows: dict[str, list[dict[str, str]]] = {}
    for (event_id, _anchor), items in events.items():
        event_rows.setdefault(event_id, []).extend(items)
    for event_id, items in event_rows.items():
        signatures = {
            (
                item.get("symbol"),
                item.get("action"),
                item.get("announcement_date"),
                item.get("effective_date"),
            )
            for item in items
        }
        if len(signatures) > 1:
            errors.append({"reason": "inconsistent_event_metadata", "event_id": event_id})
        for column in ("weight_before", "weight_after"):
            weight_values = {
                finite_number(item.get(column))
                for item in items
                if item.get(column) not in (None, "")
            }
            if len(weight_values) > 1:
                errors.append({
                    "reason": "inconsistent_weight_metadata",
                    "event_id": event_id,
                    "column": column,
                })
    if errors:
        return {"_parameter_errors": errors}

    windows: dict[tuple[str, str], list[dict[str, str]]] = {}
    for key, items in events.items():
        window = [r for r in items if start <= int(finite_number(r.get("relative_day")) or 0) <= end]
        if not window:
            errors.append({"reason": "empty_event_window", "event_id": key[0], "anchor": key[1], "window": [start, end]})
        windows[key] = window
    if errors:
        return {"_parameter_errors": errors}

    details: list[dict[str, object]] = []
    for (event_id, anchor), items in events.items():
        window = windows[(event_id, anchor)]
        car = sum(number(r.get("return"))-number(r.get("benchmark_return")) for r in window)
        volume = statistics.mean([number(r.get("volume_ratio"), 1.0) for r in window]) if window else None
        anchors = sorted({r.get("relative_to") for r in window if r.get("relative_to")})
        weight_before = next((number(r.get("weight_before")) for r in items if r.get("weight_before") not in (None, "")), None)
        weight_after = next((number(r.get("weight_after")) for r in items if r.get("weight_after") not in (None, "")), None)
        details.append({
            "event_id": event_id,
            "symbol": items[0].get("symbol"),
            "action": items[0].get("action"),
            "anchor": anchor,
            "anchors": anchors or ["unspecified"],
            "observations": len(window),
            "car": car,
            "mean_volume_ratio": volume,
            "weight_change": (
                weight_after - weight_before
                if weight_before is not None and weight_after is not None
                else None
            ),
        })
    if errors:
        return {"_parameter_errors": errors}
    summary: dict[object, dict[object, dict[str, object]]] = {}
    for action in {d["action"] for d in details}:
        summary[action] = {}
        for anchor in {d["anchor"] for d in details if d["action"] == action}:
            matching = [d for d in details if d["action"] == action and d["anchor"] == anchor]
            vals = [d["car"] for d in matching]
            summary[action][anchor] = {
                "events": len({d["event_id"] for d in matching}),
                "mean_car": statistics.mean(vals) if vals else None,
            }

    anchor_summary: dict[str, dict[str, object]] = {}
    normalized_rows = [row for items in events.values() for row in items]
    for anchor in valid_anchors:
        observations = [
            number(row.get("return")) - number(row.get("benchmark_return"))
            for row in normalized_rows
            if row.get("relative_to") == anchor
            and start <= int(number(row.get("relative_day"))) <= end
        ]
        if observations:
            anchor_summary[anchor] = {
                "observations": len(observations),
                "mean_abnormal_return": statistics.mean(observations),
            }

    has_unspecified_anchor = any(not row.get("relative_to") for row in normalized_rows)
    limitations = [
        "CAR is the arithmetic sum of return minus benchmark_return within the supplied relative-day window.",
        "Small event counts are descriptive; statistical inference and overlapping-event controls are not implemented.",
        "Announcement dates must come from an official notice rather than the first observed weight change.",
    ]
    if has_unspecified_anchor:
        limitations.append(
            "relative_to is absent for at least one observation, so those rows cannot be attributed to announcement or effective-date effects."
        )
    return {
        "rows": len(rows),
        "window": [start, end],
        "events": details,
        "action_summary": summary,
        "anchor_summary": anchor_summary,
        "timing_findings": [],
        "passed": True,
        "_assumptions": {
            "window_start": start,
            "window_end": end,
            "abnormal_return": "return - benchmark_return",
            "event_anchor": "relative_to when supplied; otherwise unspecified",
        },
        "_limitations": limitations,
        "_next_actions": [
            "Verify announcement and effective dates against official index notices.",
            "Provide relative_to for separate announcement/effective analyses and add weight fields when studying weight changes.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Study index rebalance event effects.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input")
    source.add_argument("--demo", action="store_true")
    parser.add_argument("--out")
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--end", type=int, default=1)
    args = parser.parse_args()
    emit(analyze(load_rows(args.input, DEMO), args.start, args.end), args.out)


if __name__ == "__main__": main()
