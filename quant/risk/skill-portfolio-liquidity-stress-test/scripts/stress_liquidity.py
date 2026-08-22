from __future__ import annotations

import argparse
import csv
import json
import math
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
        "assumptions": result.get("_assumptions", {"adv_unit": "not supplied"}),
        "metrics": metrics,
        "findings": findings,
        "limitations": result.get("_limitations", [
            "This is a deterministic scenario estimate, not an execution guarantee."
        ]),
        "next_actions": ["Supply valid required fields or parameters and rerun."] if evidence_issues else (
            result.get("_next_actions", ["Review the shortfall and rerun alternative scenarios."])
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
            error_result = {"_parameter_errors": [{
                "reason": "output_write_error",
                "error_type": type(exc).__name__,
            }]}
            print(json.dumps(build_report(error_result), ensure_ascii=False, indent=2, allow_nan=False))
    else:
        print(payload)

DEMO = [
    {"symbol": "AAA", "position_value": "20000000", "adv": "5000000", "spread_bps": "8", "volatility": "0.03"},
    {"symbol": "BBB", "position_value": "10000000", "adv": "1000000", "spread_bps": "20", "volatility": "0.05"},
]

REQUIRED_COLUMNS = {'adv', 'position_value', 'spread_bps', 'symbol', 'volatility'}
NUMERIC_COLUMNS = {'adv', 'position_value', 'spread_bps', 'volatility'}
OPTIONAL_NUMERIC_COLUMNS = set()


def analyze(
    rows: list[dict[str, str]],
    participation: float,
    volume_shock: float,
    horizon_days: int,
    eta: float,
    redemption_value: float | None = None,
) -> dict[str, object]:
    errors: list[object] = []
    if not math.isfinite(participation) or not 0 < participation <= 1:
        errors.append("participation must be finite and in (0, 1]")
    if not math.isfinite(volume_shock) or volume_shock <= 0:
        errors.append("volume-shock must be finite and positive")
    horizon_value: float | None = None
    if isinstance(horizon_days, bool) or not isinstance(horizon_days, int) or horizon_days <= 0:
        errors.append("horizon-days must be a positive integer")
    else:
        try:
            horizon_value = float(horizon_days)
        except OverflowError:
            horizon_value = None
        if horizon_value is None or not math.isfinite(horizon_value):
            errors.append("horizon-days exceeds the model's finite numeric range")
    if not math.isfinite(eta) or eta < 0:
        errors.append("eta must be finite and non-negative")
    if redemption_value is not None and (not math.isfinite(redemption_value) or redemption_value < 0):
        errors.append("redemption-value must be finite and non-negative")
    seen_symbols: set[str] = set()
    normalized_rows: list[dict[str, object]] = []
    for row_number, row in enumerate(rows, 2):
        symbol = text(row.get("symbol")).strip()
        if not symbol:
            errors.append({"reason": "empty_symbol", "row": row_number})
        elif symbol in seen_symbols:
            errors.append({"reason": "duplicate_symbol", "row": row_number, "symbol": symbol})
        seen_symbols.add(symbol)
        values = {key: finite_number(row.get(key)) for key in ("position_value", "adv", "spread_bps", "volatility")}
        for key, value in values.items():
            if value is None:
                errors.append({"reason": "invalid_numeric", "row": row_number, "column": key})
        if values["position_value"] is not None and values["position_value"] < 0:
            errors.append({"reason": "negative_position_value", "row": row_number})
        if values["adv"] is not None and values["adv"] <= 0:
            errors.append({"reason": "non_positive_adv", "row": row_number})
        if values["spread_bps"] is not None and values["spread_bps"] < 0:
            errors.append({"reason": "negative_spread_bps", "row": row_number})
        if values["volatility"] is not None and values["volatility"] < 0:
            errors.append({"reason": "negative_volatility", "row": row_number})
        normalized_rows.append({"symbol": symbol, **values})
    try:
        total_position = math.fsum(float(row["position_value"] or 0) for row in normalized_rows)
    except OverflowError:
        total_position = math.inf
    if not math.isfinite(total_position):
        errors.append("total position value must be finite")
    elif total_position <= 0:
        errors.append("total position value must be positive")
    if errors: return {"_parameter_errors": errors}
    assert horizon_value is not None
    target = redemption_value if redemption_value is not None else total_position
    allocatable_target = min(target, total_position)
    details = []
    for row in normalized_rows:
        position = float(row["position_value"] or 0)
        adv = float(row["adv"] or 0) * volume_shock
        spread = float(row["spread_bps"] or 0)
        sigma = float(row["volatility"] or 0)
        if not math.isfinite(adv) or adv <= 0:
            errors.append({"reason": "invalid_stressed_adv", "symbol": row["symbol"]})
            continue
        daily_capacity = adv * participation
        if not math.isfinite(daily_capacity) or daily_capacity <= 0:
            errors.append({"reason": "invalid_daily_capacity", "symbol": row["symbol"]})
            continue
        days = position / daily_capacity if position else 0.0
        if not math.isfinite(days):
            errors.append({"reason": "non_finite_days_to_liquidate", "symbol": row["symbol"]})
            continue
        capacity = position if daily_capacity > position / horizon_value else daily_capacity * horizon_value
        capacity_ratio = capacity / position if position else 1.0
        desired_sale = allocatable_target * (position / total_position)
        planned_sale = min(desired_sale, capacity)
        execution_fraction = min((planned_sale / horizon_value) / adv, participation) if planned_sale else 0.0
        impact_bps = (eta * sigma) * math.sqrt(execution_fraction) * 10000
        cost_rate = (spread / 2 + impact_bps) / 10000
        item_cost = planned_sale * cost_rate
        derived = (capacity, capacity_ratio, desired_sale, planned_sale, execution_fraction, impact_bps, cost_rate, item_cost)
        if not all(math.isfinite(value) for value in derived):
            errors.append({"reason": "non_finite_derived_value", "symbol": row["symbol"]})
            continue
        details.append({
            "symbol": row["symbol"],
            "position_weight": position / total_position,
            "days_to_liquidate": days,
            "horizon_liquidated_ratio": capacity_ratio,
            "horizon_liquidation_capacity": capacity,
            "redemption_allocation": desired_sale,
            "redemption_cash_raised": planned_sale,
            "impact_bps": impact_bps,
            "estimated_cost": item_cost,
        })
    if errors:
        return {"_parameter_errors": errors}
    try:
        capacity_total = math.fsum(float(item["horizon_liquidation_capacity"]) for item in details)
        redemption_raised = math.fsum(float(item["redemption_cash_raised"]) for item in details)
        cost = math.fsum(float(item["estimated_cost"]) for item in details)
    except OverflowError:
        return {"_parameter_errors": ["portfolio aggregates must be finite"]}
    if not all(math.isfinite(value) for value in (capacity_total, redemption_raised, cost)):
        return {"_parameter_errors": ["portfolio aggregates must be finite"]}
    if capacity_total > total_position and not math.isclose(capacity_total, total_position, rel_tol=1e-12, abs_tol=1e-12):
        return {"_parameter_errors": ["horizon capacity cannot exceed portfolio value"]}
    capacity_total = min(capacity_total, total_position)
    if redemption_raised > target and not math.isclose(redemption_raised, target, rel_tol=1e-12, abs_tol=1e-12):
        return {"_parameter_errors": ["redemption cash raised cannot exceed the target"]}
    redemption_raised = min(redemption_raised, target)
    shortfall = max(target - redemption_raised, 0.0)
    warnings: list[dict[str, object]] = []
    if shortfall > 0:
        warnings.append({
            "id": "redemption-shortfall",
            "severity": "high",
            "evidence": {
                "redemption_target": target,
                "redemption_cash_raised": redemption_raised,
                "cash_shortfall": shortfall,
            },
            "impact": "The scenario cannot raise the requested cash within the selected horizon.",
            "recommended_fix": "Extend the horizon, reduce the redemption target, lower concentration, or test a different participation/depth assumption.",
        })
    return {
        "rows": len(rows),
        "symbols": len(rows),
        "participation": participation,
        "volume_shock": volume_shock,
        "horizon_days": horizon_days,
        "portfolio_value": total_position,
        "portfolio_liquidated_ratio": capacity_total / total_position,
        "horizon_cash_raised": capacity_total,
        "redemption_target": target,
        "redemption_cash_raised": redemption_raised,
        "cash_shortfall": shortfall,
        "estimated_cost": cost,
        "warnings": warnings,
        "details": details,
        "passed": True,
        "_assumptions": {
            "participation_rate": participation,
            "volume_shock_multiplier": volume_shock,
            "horizon_days": horizon_days,
            "impact_eta": eta,
            "adv_unit": "currency value per trading day, same currency as position_value",
            "spread_bps": "full bid-ask spread; half-spread is charged",
            "redemption_allocation": "pro rata by position value, capped by each symbol's stressed horizon capacity",
            "impact_rate": "square-root impact uses the planned daily participation fraction capped by participation",
        },
        "_limitations": [
            "ADV and position_value must be normalized to the same currency-value unit; futures/options require contract multipliers before use.",
            "Square-root impact is a scenario model, not a calibrated execution forecast.",
            "Correlated liquidation, intraday volume curves, borrow, price limits and cross-asset netting are not modeled.",
        ],
        "_next_actions": [
            "Run sensitivity cases for participation, volume shock, horizon and impact eta.",
            "Replace proxy spreads with broker or venue data when available and document the provenance.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Stress portfolio liquidation under depth shocks.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input")
    source.add_argument("--demo", action="store_true")
    parser.add_argument("--out")
    parser.add_argument("--participation", type=float, default=0.1)
    parser.add_argument("--volume-shock", type=float, default=0.5)
    parser.add_argument("--horizon-days", type=int, default=5)
    parser.add_argument("--eta", type=float, default=0.5)
    parser.add_argument("--redemption-value", type=float)
    args = parser.parse_args()
    emit(analyze(
        load_rows(args.input, DEMO),
        args.participation,
        args.volume_shock,
        args.horizon_days,
        args.eta,
        args.redemption_value,
    ), args.out)


if __name__ == "__main__": main()
