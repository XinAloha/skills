from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class SplitData:
    train: pd.DataFrame
    valid: pd.DataFrame
    oos: pd.DataFrame


def read_wide(path: str | Path) -> pd.DataFrame:
    frame = pd.read_parquet(path)
    frame.index = pd.to_datetime(frame.index)
    frame.columns = frame.columns.astype(str).str.upper()
    return frame.sort_index().replace([np.inf, -np.inf], np.nan)


def select_universe(
    label: pd.DataFrame,
    train_start: str,
    train_end: str,
    min_coverage: float,
    symbols: Iterable[str] | None = None,
) -> list[str]:
    train = label.loc[train_start:train_end]
    if symbols is not None:
        requested = [symbol.upper() for symbol in symbols]
        missing = sorted(set(requested).difference(label.columns))
        if missing:
            raise ValueError(f"Unknown symbols: {missing}")
        return requested
    coverage = train.notna().mean()
    selected = coverage[coverage >= min_coverage].sort_index().index.tolist()
    if not selected:
        raise ValueError("Universe selection removed every symbol")
    return selected


def purge_tail(frame: pd.DataFrame, bars: int) -> pd.DataFrame:
    if bars <= 0 or frame.empty:
        return frame
    dates = frame.index.get_level_values("datetime").unique().sort_values()
    if len(dates) <= bars:
        return frame.iloc[0:0]
    return frame.loc[frame.index.get_level_values("datetime") <= dates[-bars - 1]]


def build_temporal_fold_masks(
    dates: pd.Index,
    fold: dict,
    embargo_bars: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Build causal fit/score masks and purge the fit tail by trading dates."""
    date_index = pd.DatetimeIndex(dates)
    fit_mask = np.asarray(
        (date_index >= pd.Timestamp(fold["fit_start"]))
        & (date_index <= pd.Timestamp(fold["fit_end"]))
    )
    score_mask = np.asarray(
        (date_index >= pd.Timestamp(fold["score_start"]))
        & (date_index <= pd.Timestamp(fold["score_end"]))
    )
    fit_dates = date_index[fit_mask].unique().sort_values()
    score_dates = date_index[score_mask].unique().sort_values()
    if len(fit_dates) == 0 or len(score_dates) == 0:
        raise ValueError(f"Temporal CV fold has no observations: {fold}")
    if embargo_bars < 0:
        raise ValueError("embargo_bars must be non-negative")
    if embargo_bars:
        if len(fit_dates) <= embargo_bars:
            raise ValueError(f"Temporal CV fold is too short for embargo_bars={embargo_bars}: {fold}")
        fit_mask &= np.asarray(date_index <= fit_dates[-embargo_bars - 1])
        fit_dates = date_index[fit_mask].unique().sort_values()
    if fit_dates[-1] >= score_dates[0]:
        raise ValueError(f"Temporal CV fit period must precede its score period: {fold}")
    return fit_mask, score_mask


def stack_wide(frame: pd.DataFrame, symbols: Iterable[str]) -> pd.Series:
    available = [symbol for symbol in symbols if symbol in frame.columns]
    stacked = frame.reindex(columns=available).stack(future_stack=True)
    stacked.index = stacked.index.set_names(["datetime", "symbol"])
    return stacked.sort_index()


def split_panel(series: pd.Series, split: dict, embargo_bars: int) -> SplitData:
    panel = series.rename("value").to_frame()
    dates = panel.index.get_level_values("datetime")

    def select(start: str, end: str | None) -> pd.DataFrame:
        mask = dates >= pd.Timestamp(start)
        if end is not None:
            mask &= dates <= pd.Timestamp(end)
        return panel.loc[mask]

    train = purge_tail(select(split["train_start"], split["train_end"]), embargo_bars)
    valid = purge_tail(select(split["valid_start"], split["valid_end"]), embargo_bars)
    oos = select(split["oos_start"], split.get("oos_end"))
    return SplitData(train=train, valid=valid, oos=oos)


class FactorStore:
    def __init__(
        self,
        factor_dir: str | Path | None,
        symbols: Iterable[str],
        factor_names: Iterable[str] | None = None,
    ):
        self.factor_dir = Path(factor_dir) if factor_dir is not None else None
        self.symbols = list(symbols)
        if factor_names is None:
            if self.factor_dir is None:
                raise ValueError("factor_dir is required when prepared_feature_cache is unavailable")
            self.factor_names = sorted(path.stem for path in self.factor_dir.glob("*.parquet"))
        else:
            self.factor_names = [str(name) for name in factor_names]
            if len(set(self.factor_names)) != len(self.factor_names):
                raise ValueError("Prepared feature cache contains duplicate factor names")
        if not self.factor_names:
            raise FileNotFoundError("No factors found in factor_dir or prepared_feature_cache")
        self._cache: dict[str, pd.Series] = {}

    def load_wide(self, factor_name: str) -> pd.DataFrame:
        if self.factor_dir is None:
            raise FileNotFoundError("Raw factor files are unavailable in prepared-cache-only mode")
        path = self.factor_dir / f"{factor_name}.parquet"
        return read_wide(path).reindex(columns=self.symbols)

    def load(self, factor_name: str) -> pd.Series:
        if factor_name not in self._cache:
            if self.factor_dir is None:
                raise FileNotFoundError("Raw factor files are unavailable in prepared-cache-only mode")
            path = self.factor_dir / f"{factor_name}.parquet"
            self._cache[factor_name] = stack_wide(read_wide(path), self.symbols).rename(factor_name)
        return self._cache[factor_name]

    def clear_cache(self) -> None:
        self._cache.clear()
