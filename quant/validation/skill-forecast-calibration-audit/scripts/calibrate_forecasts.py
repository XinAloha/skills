#!/usr/bin/env python3
"""Audit probability forecasts with proper scores and calibration tables."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd


def _read(path: str) -> pd.DataFrame:
    frame = pd.read_csv(path)
    required = {"date", "probability", "outcome"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"input: missing columns {missing}")
    return frame


def _metrics(frame: pd.DataFrame, threshold: float) -> dict[str, float | int | None]:
    if frame.empty:
        return {"n": 0, "brier": None, "log_loss": None, "accuracy": None, "positive_rate": None}
    p = frame["probability"].to_numpy(float)
    y = frame["outcome"].to_numpy(int)
    clipped = np.clip(p, 1e-15, 1 - 1e-15)
    predicted = (p >= threshold).astype(int)
    return {"n": int(len(frame)), "brier": float(np.mean((p - y) ** 2)), "log_loss": float(-np.mean(y * np.log(clipped) + (1 - y) * np.log(1 - clipped))), "accuracy": float(np.mean(predicted == y)), "positive_rate": float(np.mean(y)), "predicted_positive_rate": float(np.mean(predicted))}


def _calibration_coefficients(frame: pd.DataFrame) -> tuple[float | None, float | None]:
    if len(frame) < 3 or frame["outcome"].nunique() < 2:
        return None, None
    x = np.log(np.clip(frame["probability"].to_numpy(float), 1e-6, 1 - 1e-6) / np.clip(1 - frame["probability"].to_numpy(float), 1e-6, 1 - 1e-6))
    y = frame["outcome"].to_numpy(float)
    design = np.column_stack([np.ones(len(x)), x])
    beta = np.zeros(2)
    for _ in range(50):
        z = np.clip(design @ beta, -30, 30)
        mu = 1.0 / (1.0 + np.exp(-z))
        w = np.clip(mu * (1.0 - mu), 1e-8, None)
        hessian = design.T @ (w[:, None] * design) + np.eye(2) * 1e-8
        step = np.linalg.solve(hessian, design.T @ (y - mu))
        beta += step
        if np.max(np.abs(step)) < 1e-8:
            break
    return float(beta[0]), float(beta[1])


def audit_forecasts(frame: pd.DataFrame, threshold: float = 0.5, time_bins: int = 5, regime_column: Optional[str] = None) -> dict[str, pd.DataFrame | dict]:
    frame = frame.copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="raise", utc=True)
    frame["probability"] = pd.to_numeric(frame["probability"], errors="raise")
    frame["outcome"] = pd.to_numeric(frame["outcome"], errors="raise")
    if not bool(frame["probability"].between(0, 1).all()):
        raise ValueError("probability values must be in [0, 1]")
    if not frame["outcome"].isin([0, 1]).all():
        raise ValueError("outcome values must be 0 or 1")
    frame = frame.sort_values("date").reset_index(drop=True)
    p = np.clip(frame["probability"].to_numpy(float), 1e-15, 1 - 1e-15)
    frame["predicted_class"] = (frame["probability"] >= threshold).astype(int)
    frame["brier_term"] = (frame["probability"] - frame["outcome"]) ** 2
    frame["log_loss_term"] = -(frame["outcome"] * np.log(p) + (1 - frame["outcome"]) * np.log(1 - p))
    edges = np.linspace(0, 1, 11)
    labels = [f"{edges[i]:.1f}-{edges[i+1]:.1f}" for i in range(len(edges) - 1)]
    frame["probability_bin"] = pd.cut(frame["probability"], bins=edges, labels=labels, include_lowest=True, right=True)
    reliability = frame.groupby("probability_bin", observed=False).agg(observations=("outcome", "size"), mean_forecast=("probability", "mean"), observed_rate=("outcome", "mean")).reset_index()
    reliability["gap"] = reliability["observed_rate"] - reliability["mean_forecast"]
    n = len(frame)
    reliability["weighted_abs_gap"] = reliability["gap"].abs() * reliability["observations"] / n
    intercept, slope = _calibration_coefficients(frame)
    if len(frame) and time_bins > 1:
        frame["time_bin"] = pd.qcut(np.arange(len(frame)), q=min(time_bins, len(frame)), labels=False, duplicates="drop") + 1
        time_metrics = frame.groupby("time_bin", as_index=False).apply(lambda g: pd.Series(_metrics(g, threshold)), include_groups=False).reset_index(drop=True)
        time_metrics["date_start"] = frame.groupby("time_bin")["date"].min().to_numpy()
        time_metrics["date_end"] = frame.groupby("time_bin")["date"].max().to_numpy()
    else:
        time_metrics = pd.DataFrame([{"time_bin": 1, **_metrics(frame, threshold), "date_start": frame["date"].min() if len(frame) else None, "date_end": frame["date"].max() if len(frame) else None}])
    groups = pd.DataFrame()
    if regime_column and regime_column in frame.columns:
        groups = frame.groupby(regime_column, dropna=False).apply(lambda g: pd.Series(_metrics(g, threshold)), include_groups=False).reset_index()
    summary = {**_metrics(frame, threshold), "ece": float(reliability["weighted_abs_gap"].sum()) if n else None, "mce": float(reliability["gap"].abs().max()) if n else None, "calibration_intercept": intercept, "calibration_slope": slope, "threshold": threshold, "time_bins": int(time_bins), "warnings": (["fewer than 3 observations or only one class; calibration coefficients unavailable"] if intercept is None else [])}
    return {"scored": frame, "reliability": reliability, "time": time_metrics, "groups": groups, "summary": summary}


def _demo() -> pd.DataFrame:
    dates = pd.date_range("2026-01-01", periods=20, freq="D", tz="UTC")
    probability = np.linspace(0.05, 0.95, 20)
    outcome = (np.arange(20) % 3 != 0).astype(int)
    return pd.DataFrame({"date": dates, "probability": probability, "outcome": outcome, "regime": ["risk_on" if i % 2 else "risk_off" for i in range(20)]})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument("--time-bins", type=int, default=5)
    parser.add_argument("--regime-column")
    parser.add_argument("--demo", action="store_true")
    args = parser.parse_args()
    frame = _demo() if args.demo else _read(args.input) if args.input else None
    if frame is None:
        parser.error("--input is required unless --demo is used")
    result = audit_forecasts(frame, args.threshold, args.time_bins, args.regime_column)
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    result["scored"].to_csv(out / "scored_predictions.csv", index=False)
    result["reliability"].to_csv(out / "reliability.csv", index=False)
    result["time"].to_csv(out / "time_metrics.csv", index=False)
    if len(result["groups"]):
        result["groups"].to_csv(out / "regime_metrics.csv", index=False)
    (out / "summary.json").write_text(json.dumps(result["summary"], indent=2), encoding="utf-8")
    print(json.dumps(result["summary"], indent=2))


if __name__ == "__main__":
    main()
