"""Build the single fixed train/validation split used by both modes."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping

import pandas as pd

from .config_utils import ConfigError
from .data_adapter import normalize_dates


@dataclass(frozen=True)
class Window:
    window_id: int
    train_dates: tuple[int, ...]
    valid_dates: tuple[int, ...]

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["train_dates"] = list(self.train_dates)
        value["valid_dates"] = list(self.valid_dates)
        value["train_start"] = self.train_dates[0]
        value["train_end"] = self.train_dates[-1]
        value["valid_start"] = self.valid_dates[0]
        value["valid_end"] = self.valid_dates[-1]
        return value


def _date(value: Any, field: str) -> int:
    if value in (None, ""):
        raise ConfigError(f"validation.{field} is required")
    return int(normalize_dates(pd.Series([value])).iloc[0])


def _between(dates: list[int], start: int, end: int, label: str) -> tuple[int, ...]:
    selected = tuple(date for date in dates if start <= date <= end)
    if not selected:
        raise ConfigError(f"No dates are available for {label}: {start}-{end}")
    return selected


def build_windows(panel: pd.DataFrame, cfg: Mapping[str, Any]) -> list[Window]:
    dates = sorted(int(value) for value in panel["date"].unique())
    validation = cfg["validation"]
    train_start = _date(validation.get("train_start"), "train_start")
    train_end = _date(validation.get("train_end"), "train_end")
    valid_start = _date(validation.get("valid_start"), "valid_start")
    valid_end = _date(validation.get("valid_end"), "valid_end")
    if not train_start <= train_end < valid_start <= valid_end:
        raise ConfigError("Fixed split requires train_start <= train_end < valid_start <= valid_end")
    embargo = int(validation.get("embargo_days", 0))
    gap = [date for date in dates if train_end < date < valid_start]
    if len(gap) < embargo:
        raise ConfigError(f"Fixed split has {len(gap)} embargo dates; {embargo} required")
    return [
        Window(
            0,
            _between(dates, train_start, train_end, "train"),
            _between(dates, valid_start, valid_end, "valid"),
        )
    ]
