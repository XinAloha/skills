#!/usr/bin/env python3
"""Calibrate execution costs using prior quotes or bar observations."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd


def _read(path: str, required: list[str]) -> pd.DataFrame:
    frame = pd.read_csv(path)
    missing = sorted(set(required) - set(frame.columns))
    if missing:
        raise ValueError(f"{path}: missing columns {missing}")
    return frame


def _asof(executions: pd.DataFrame, reference: pd.DataFrame, value_cols: list[str]) -> pd.DataFrame:
    if reference is None or reference.empty:
        return executions
    left = executions.sort_values(["timestamp", "symbol"]).copy()
    right = reference.sort_values(["timestamp", "symbol"]).copy()
    return pd.merge_asof(left, right[["symbol", "timestamp"] + value_cols], on="timestamp", by="symbol", direction="backward", suffixes=("", "_ref"))


def calibrate_costs(
    executions: pd.DataFrame,
    quotes: Optional[pd.DataFrame] = None,
    bars: Optional[pd.DataFrame] = None,
    commission_bps: float = 0.0,
) -> dict[str, pd.DataFrame | dict]:
    executions = executions.copy()
    required = ["timestamp", "symbol", "side", "quantity", "price"]
    missing = sorted(set(required) - set(executions.columns))
    if missing:
        raise ValueError(f"executions: missing columns {missing}")
    executions["timestamp"] = pd.to_datetime(executions["timestamp"], errors="raise", utc=True)
    executions["quantity"] = pd.to_numeric(executions["quantity"], errors="raise")
    executions["price"] = pd.to_numeric(executions["price"], errors="raise")
    if (executions[["quantity", "price"]] <= 0).any().any():
        raise ValueError("quantity and price must be positive")
    executions["side_sign"] = executions["side"].astype(str).str.lower().map({"buy": 1.0, "sell": -1.0})
    if executions["side_sign"].isna().any():
        raise ValueError("side must be buy or sell")
    if quotes is not None:
        quotes = quotes.copy()
        quotes["timestamp"] = pd.to_datetime(quotes["timestamp"], errors="raise", utc=True)
        for c in ["bid", "ask"]:
            quotes[c] = pd.to_numeric(quotes[c], errors="raise")
        if (quotes[["bid", "ask"]] <= 0).any().any() or (quotes["ask"] < quotes["bid"]).any():
            raise ValueError("quotes must have positive bid <= ask")
        executions = _asof(executions, quotes, ["bid", "ask"])
    if bars is not None:
        bars = bars.copy()
        bars["timestamp"] = pd.to_datetime(bars["timestamp"], errors="raise", utc=True)
        for c in ["close", "volume"]:
            bars[c] = pd.to_numeric(bars[c], errors="raise")
        executions = _asof(executions, bars, ["close", "volume"])
    bid = executions["bid"] if "bid" in executions else pd.Series(np.nan, index=executions.index)
    ask = executions["ask"] if "ask" in executions else pd.Series(np.nan, index=executions.index)
    close = executions["close"] if "close" in executions else pd.Series(np.nan, index=executions.index)
    volume = executions["volume"] if "volume" in executions else pd.Series(np.nan, index=executions.index)
    executions["mid"] = np.where(bid.notna() & ask.notna(), (bid + ask) / 2.0, np.nan)
    executions["reference_price"] = executions["mid"].fillna(close)
    executions["slippage_bps"] = executions["side_sign"] * (executions["price"] - executions["reference_price"]) / executions["reference_price"] * 10000.0
    executions["spread_bps"] = (ask - bid) / executions["mid"] * 10000.0
    executions["participation"] = executions["quantity"] / volume
    executions["commission_bps"] = float(commission_bps)
    executions["total_cost_bps"] = executions["slippage_bps"] + executions["commission_bps"]

    valid = executions.dropna(subset=["participation", "slippage_bps"]).copy()
    impact_intercept = impact_slope = None
    if len(valid) >= 2 and (valid["participation"] > 0).all():
        x = np.sqrt(valid["participation"].to_numpy(dtype=float))
        y = valid["slippage_bps"].abs().to_numpy(dtype=float)
        impact_intercept, impact_slope = np.polyfit(x, y, 1)[1], np.polyfit(x, y, 1)[0]
    bins = pd.qcut(valid["participation"], q=min(5, valid["participation"].nunique()), duplicates="drop") if len(valid) else pd.Series(dtype=object)
    curve = valid.assign(participation_bin=bins).groupby("participation_bin", observed=True).agg(
        observations=("total_cost_bps", "size"), median_cost_bps=("total_cost_bps", "median"), p95_cost_bps=("total_cost_bps", lambda s: s.quantile(0.95)), median_participation=("participation", "median")
    ).reset_index() if len(valid) else pd.DataFrame(columns=["participation_bin", "observations", "median_cost_bps", "p95_cost_bps", "median_participation"])
    finite_cost = executions["total_cost_bps"].replace([np.inf, -np.inf], np.nan).dropna()
    summary = {
        "fills": int(len(executions)),
        "reference_coverage": float(executions["reference_price"].notna().mean()) if len(executions) else 0.0,
        "median_total_cost_bps": float(finite_cost.median()) if len(finite_cost) else None,
        "p95_total_cost_bps": float(finite_cost.quantile(0.95)) if len(finite_cost) else None,
        "impact_intercept_bps": float(impact_intercept) if impact_intercept is not None else None,
        "impact_sqrt_participation_slope_bps": float(impact_slope) if impact_slope is not None else None,
        "max_observed_participation": float(valid["participation"].max()) if len(valid) else None,
        "warnings": (["no prior quote or bar reference for some fills"] if executions["reference_price"].isna().any() else []),
    }
    return {"executions": executions, "curve": curve, "summary": summary}


def _demo() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    executions = pd.DataFrame({"timestamp": pd.date_range("2026-01-02 09:31", periods=6, freq="min", tz="UTC"), "symbol": ["AAA"] * 6, "side": ["buy", "sell", "buy", "sell", "buy", "sell"], "quantity": [100, 150, 200, 250, 300, 350], "price": [100.06, 99.94, 100.12, 99.88, 100.18, 99.82]})
    quotes = pd.DataFrame({"timestamp": pd.date_range("2026-01-02 09:30", periods=6, freq="min", tz="UTC"), "symbol": ["AAA"] * 6, "bid": [99.98] * 6, "ask": [100.02] * 6})
    bars = pd.DataFrame({"timestamp": pd.date_range("2026-01-02 09:30", periods=6, freq="min", tz="UTC"), "symbol": ["AAA"] * 6, "close": [100.0] * 6, "volume": [10000, 11000, 12000, 13000, 14000, 15000]})
    return executions, quotes, bars


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--executions")
    parser.add_argument("--quotes")
    parser.add_argument("--bars")
    parser.add_argument("--commission-bps", type=float, default=0.0)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--demo", action="store_true")
    args = parser.parse_args()
    if args.demo:
        executions, quotes, bars = _demo()
    else:
        if not args.executions:
            parser.error("--executions is required unless --demo is used")
        executions = _read(args.executions, ["timestamp", "symbol", "side", "quantity", "price"])
        quotes = _read(args.quotes, ["timestamp", "symbol", "bid", "ask"]) if args.quotes else None
        bars = _read(args.bars, ["timestamp", "symbol", "close", "volume"]) if args.bars else None
    result = calibrate_costs(executions, quotes, bars, args.commission_bps)
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    result["executions"].to_csv(out / "execution_costs.csv", index=False)
    result["curve"].to_csv(out / "cost_curve.csv", index=False)
    (out / "summary.json").write_text(json.dumps(result["summary"], indent=2), encoding="utf-8")
    print(json.dumps(result["summary"], indent=2))


if __name__ == "__main__":
    main()
