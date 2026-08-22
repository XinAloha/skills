from __future__ import annotations

import argparse
import csv
import json
import math
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
    result_evidence_issues = result.get("_evidence_issues", [])
    if result_evidence_issues:
        evidence_issues.extend(
            result_evidence_issues
            if isinstance(result_evidence_issues, list)
            else [result_evidence_issues]
        )
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
        "assumptions": result.get("_assumptions", {"input_timezone": "not supplied"}),
        "metrics": metrics,
        "findings": findings,
        "limitations": result.get("_limitations", [
            "The script audits normalized OHLCV bars; it does not adjudicate exchange halts or trade-level sequencing."
        ]),
        "next_actions": ["Supply valid required fields or parameters and rerun."] if evidence_issues else (
            result.get("_next_actions", ["Review flagged bars against the exchange calendar and source feed, then rerun."])
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
    {"symbol": "000001.SZ", "trading_date": "2024-01-02", "session": "morning", "timestamp": "2024-01-02T09:30:00", "open": "10", "high": "10.2", "low": "9.9", "close": "10.1", "volume": "1000"},
    {"symbol": "000001.SZ", "trading_date": "2024-01-02", "session": "morning", "timestamp": "2024-01-02T09:31:00", "open": "10.1", "high": "10.0", "low": "10.2", "close": "10.15", "volume": "-5"},
    {"symbol": "000001.SZ", "trading_date": "2024-01-02", "session": "morning", "timestamp": "2024-01-02T09:33:00", "open": "10.2", "high": "10.3", "low": "10.1", "close": "10.25", "volume": "900"},
]

REQUIRED_COLUMNS = {'close', 'high', 'low', 'open', 'session', 'symbol', 'timestamp', 'trading_date', 'volume'}
NUMERIC_COLUMNS = {'close', 'high', 'low', 'open', 'volume'}
OPTIONAL_NUMERIC_COLUMNS = set()


def analyze(rows: list[dict[str, str]], expected_seconds: int) -> dict[str, object]:
    if expected_seconds <= 0:
        return {"_parameter_errors": ["expected-seconds must be positive"]}
    findings: list[dict[str, object]] = []
    evidence_issues: list[dict[str, object]] = []
    groups: dict[tuple[str, str, str], list[dict[str, str]]] = {}
    for row in rows:
        key = (row.get("symbol", ""), row.get("trading_date", ""), row.get("session", ""))
        groups.setdefault(key, []).append(row)

    for (symbol, trading_date, session), group_rows in sorted(groups.items()):
        parsed_timestamps: list[datetime] = []
        for row in group_rows:
            try:
                parsed_timestamps.append(datetime.fromisoformat(row.get("timestamp", "")))
            except ValueError:
                pass
        timezone_awareness = {
            moment.utcoffset() is not None for moment in parsed_timestamps
        }
        mixed_timezone_awareness = len(timezone_awareness) > 1
        if mixed_timezone_awareness:
            evidence_issues.append({
                "reason": "mixed_timezone_awareness",
                "symbol": symbol,
                "trading_date": trading_date,
                "session": session,
                "required_fix": "Use either timezone-aware timestamps or timezone-naive timestamps consistently within each group.",
            })

        input_previous: datetime | None = None
        for row in group_rows:
            ts = row.get("timestamp", "")
            try:
                input_moment = datetime.fromisoformat(ts)
            except ValueError:
                input_moment = None
            if (
                not mixed_timezone_awareness
                and input_previous
                and input_moment
                and input_moment <= input_previous
            ):
                findings.append({
                    "symbol": symbol,
                    "trading_date": trading_date,
                    "session": session,
                    "timestamp": ts,
                    "reasons": ["non_increasing_timestamp"],
                })
            if input_moment and not mixed_timezone_awareness:
                input_previous = input_moment

        seen: set[str] = set()
        previous: datetime | None = None
        for row in sorted(group_rows, key=lambda item: item.get("timestamp", "")):
            ts = row.get("timestamp", "")
            reasons: list[str] = []
            if not symbol or not trading_date or not session:
                reasons.append("blank_group_key")
            if ts in seen:
                reasons.append("duplicate_timestamp")
            seen.add(ts)
            try:
                moment = datetime.fromisoformat(ts)
            except ValueError:
                moment = None
                reasons.append("invalid_timestamp")
            if previous and moment and not mixed_timezone_awareness:
                gap_seconds = (moment - previous).total_seconds()
                if gap_seconds <= 0:
                    reasons.append("non_increasing_timestamp")
                elif gap_seconds > expected_seconds * 1.5:
                    reasons.append("missing_bar_gap")
            if moment:
                session_key = session.strip().lower().replace("-", "_")
                explicit_night_session = (
                    session_key in {"night", "night_session", "overnight"}
                    or session_key.startswith("night_")
                )
                if (
                    moment.date().isoformat() != trading_date
                    and not explicit_night_session
                ):
                    reasons.append("timestamp_trading_date_mismatch")
                if not mixed_timezone_awareness:
                    previous = moment
            o, h, l, c, v = (number(row.get(field)) for field in ("open", "high", "low", "close", "volume"))
            if min(o, h, l, c) <= 0:
                reasons.append("non_positive_price")
            if h < max(o, c) or l > min(o, c) or h < l:
                reasons.append("ohlc_invariant_violation")
            if v < 0:
                reasons.append("negative_volume")
            if reasons:
                findings.append({
                    "symbol": symbol,
                    "trading_date": trading_date,
                    "session": session,
                    "timestamp": ts,
                    "reasons": reasons,
                })
    return {
        "rows": len(rows),
        "groups": len(groups),
        "symbols": len({symbol for symbol, _, _ in groups}),
        "findings": findings,
        "passed": not findings,
        "expected_seconds": expected_seconds,
        "_evidence_issues": evidence_issues,
        "_assumptions": {
            "expected_bar_interval_seconds": expected_seconds,
            "timestamp_format": "ISO-8601",
            "session_labels": "provided by input; not inferred",
            "night_session_rule": "night, night_session, overnight, or night_* may map a prior natural date to the supplied trading_date",
        },
        "_limitations": [
            "Gaps are flags, not proof of bad data; scheduled breaks and exchange halts require calendar evidence.",
            "The input contract is OHLCV bars, not tick trades or Level-2 order-book events.",
            "Timezone-aware timestamps are compared by their offsets, but timezone conversion and trading-calendar normalization remain outside this offline script.",
            "Night-session trading-date mapping is accepted only when the input session label explicitly identifies a night session.",
        ],
        "_next_actions": [
            "Check flagged timestamps against the exchange calendar and vendor feed.",
            "Correct source data or session labels in a new file and rerun the audit.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit intraday OHLCV bars.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input")
    source.add_argument("--demo", action="store_true")
    parser.add_argument("--out")
    parser.add_argument("--expected-seconds", type=int, default=60)
    args = parser.parse_args()
    emit(analyze(load_rows(args.input, DEMO), args.expected_seconds), args.out)


if __name__ == "__main__": main()
