from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


NON_NUMERIC_COLUMNS = {
    "date",
    "symbol",
    "name",
    "trade_status",
    "dominant_id",
    "exchange",
    "trading_code",
    "underlying_symbol",
    "trading_date",
    "minute",
    "datetime",
}

REQUIRED_COLUMNS = {"date", "symbol", "open", "high", "low", "close", "volume"}


def resolve_path(path_value: str, *, input_dir: Path, skill_root: Path) -> Path:
    path = Path(str(path_value).strip()).expanduser()
    if path.is_absolute():
        return path

    input_relative = (input_dir / path).resolve()
    if input_relative.exists():
        return input_relative

    root_relative = (skill_root / path).resolve()
    if root_relative.exists():
        return root_relative

    examples_relative = (skill_root / "examples" / path).resolve()
    if examples_relative.exists():
        return examples_relative

    return root_relative


def normalize_date_series(values: pd.Series) -> pd.Series:
    text = values.astype(str).str.strip()
    return text.str.replace("-", "", regex=False)


def load_market_data_frame(
    input_data: dict[str, Any],
    *,
    input_dir: Path,
    skill_root: Path,
) -> pd.DataFrame:
    csv_path_raw = str(input_data.get("market_data_csv_path", "")).strip()
    if not csv_path_raw:
        raise ValueError("market_data_csv_path is required.")

    csv_path = resolve_path(csv_path_raw, input_dir=input_dir, skill_root=skill_root)
    if not csv_path.is_file():
        raise FileNotFoundError(f"market_data_csv_path not found: {csv_path}")

    df = pd.read_csv(csv_path, dtype={"date": str, "symbol": str})
    if df.empty:
        raise ValueError("market_data_csv_path points to an empty CSV.")

    missing = sorted(REQUIRED_COLUMNS.difference(df.columns))
    if missing:
        raise ValueError(f"market data CSV is missing required columns: {missing}")

    df = df.copy()
    df["date"] = normalize_date_series(df["date"])
    df["symbol"] = df["symbol"].astype(str)

    start_date = str(input_data.get("start_date", "")).strip()
    end_date = str(input_data.get("end_date", "")).strip()
    symbols = input_data.get("symbols", [])

    if start_date:
        df = df[df["date"] >= normalize_date_series(pd.Series([start_date])).iloc[0]]
    if end_date:
        df = df[df["date"] <= normalize_date_series(pd.Series([end_date])).iloc[0]]
    if symbols:
        symbol_set = {str(symbol) for symbol in symbols}
        df = df[df["symbol"].isin(symbol_set)]

    if df.empty:
        raise ValueError("No market data remains after applying date/symbol filters.")

    numeric_cols = [c for c in df.columns if c not in NON_NUMERIC_COLUMNS]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return df.sort_values(["date", "symbol"]).reset_index(drop=True)


def build_matrices(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    df = df.copy()
    df["date"] = df["date"].astype(str)
    df["symbol"] = df["symbol"].astype(str)
    df = df.sort_values(["date", "symbol"])

    numeric_cols = [c for c in df.columns if c not in NON_NUMERIC_COLUMNS]
    matrices: dict[str, pd.DataFrame] = {}
    for col in numeric_cols:
        try:
            matrices[col] = df.pivot(index="date", columns="symbol", values=col).astype(float)
        except (TypeError, ValueError):
            continue

    if not {"open", "high", "low", "close", "volume"}.issubset(matrices):
        missing = sorted({"open", "high", "low", "close", "volume"}.difference(matrices))
        raise ValueError(f"market data cannot build required matrices: {missing}")

    has_true_amount = "amount" in matrices
    adjfactor = matrices.get("adjfactor", 1.0)

    if not has_true_amount and all(k in matrices for k in ("close", "volume")):
        if "adjfactor" in matrices:
            matrices["amount"] = matrices["close"] / adjfactor.replace(0, np.nan) * matrices["volume"]
        else:
            matrices["amount"] = matrices["close"] * matrices["volume"]

    if "vwap" not in matrices and all(k in matrices for k in ("amount", "volume")):
        volume = matrices["volume"].replace(0, np.nan)
        if "adjfactor" in matrices:
            matrices["vwap"] = matrices["amount"] / volume * adjfactor
        else:
            matrices["vwap"] = matrices["amount"] / volume

    return matrices


def convert_to_unadjusted_price(matrices: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    if "adjfactor" not in matrices:
        return matrices

    unadjusted = dict(matrices)
    adjfactor = unadjusted["adjfactor"].replace(0, np.nan)

    for field in ("open", "high", "low", "close", "pre_close", "limit_up", "limit_down"):
        if field in unadjusted:
            unadjusted[field] = unadjusted[field] / adjfactor

    if "amount" in unadjusted and "volume" in unadjusted:
        unadjusted["vwap"] = unadjusted["amount"] / unadjusted["volume"].replace(0, np.nan)
    elif "vwap" in unadjusted:
        unadjusted["vwap"] = unadjusted["vwap"] / adjfactor

    return unadjusted


def load_benchmark_matrices(
    input_data: dict[str, Any],
    *,
    input_dir: Path,
    skill_root: Path,
    symbols: list[str],
) -> dict[str, pd.DataFrame] | None:
    benchmark_csv_path = str(input_data.get("benchmark_csv_path", "")).strip()
    if not benchmark_csv_path:
        return None

    path = resolve_path(benchmark_csv_path, input_dir=input_dir, skill_root=skill_root)
    if not path.is_file():
        raise FileNotFoundError(f"benchmark_csv_path not found: {path}")

    bm_df = pd.read_csv(path, dtype={"date": str, "symbol": str})
    if bm_df.empty or "date" not in bm_df.columns:
        raise ValueError("benchmark CSV must include at least date and close/open columns.")

    bm_df = bm_df.copy()
    bm_df["date"] = normalize_date_series(bm_df["date"])
    bm_df = bm_df.sort_values("date")

    matrices: dict[str, pd.DataFrame] = {}
    for field in ("close", "open"):
        if field not in bm_df.columns:
            continue
        bm_df[field] = pd.to_numeric(bm_df[field], errors="coerce")
        if "symbol" in bm_df.columns:
            matrix = bm_df.pivot(index="date", columns="symbol", values=field)
            if len(matrix.columns) == 1:
                base = matrix.iloc[:, 0]
                matrix = pd.DataFrame({symbol: base for symbol in symbols}, index=base.index)
        else:
            base = bm_df.set_index("date")[field]
            matrix = pd.DataFrame({symbol: base for symbol in symbols}, index=base.index)
        matrices[field] = matrix.astype(float)

    return matrices or None
