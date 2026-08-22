from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd


EXAMPLE_DIR = Path(__file__).resolve().parent


def discover_cases(config):
    factor_dir = Path(config.get("factor_dir", EXAMPLE_DIR / "factors"))
    return [
        {
            "case_id": path.stem,
            "path": str(path),
            "periods": [int(config.get("period", 9))],
            "sensitive_points": [int(config.get("period", 9))],
        }
        for path in sorted(factor_dir.glob("factor_*.py"))
    ]


def load_input(case, config):
    rows = int(config.get("rows", 160))
    seed = int(config.get("seed", 20260709))
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2020-01-01", periods=rows, freq="D")
    t = np.arange(rows, dtype=float)

    close = 100.0 + 0.03 * t + 2.0 * np.sin(t / 9.0) + rng.normal(0.0, 0.35, rows).cumsum()
    open_ = np.r_[close[0], close[:-1]]
    high = np.maximum(open_, close) + 0.5
    low = np.minimum(open_, close) - 0.5
    volume = 1000.0 + 50.0 * np.sin(t / 7.0) + rng.lognormal(mean=4.0, sigma=0.2, size=rows)

    return pd.DataFrame(
        {
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
        },
        index=idx,
    )


def input_length(input_obj, case, config):
    return len(input_obj)


def run_target(input_obj, case, config):
    module = _load_module(Path(case["path"]))
    return module.compute_factor(input_obj, period=int(config.get("period", 9)))


def make_prefix(input_obj, cut, case, config):
    return input_obj.iloc[: cut + 1].copy()


def mutate_future(input_obj, cut, case, config):
    out = input_obj.copy(deep=True)
    if cut + 1 >= len(out):
        return out

    tail_index = out.index[cut + 1 :]
    n = len(tail_index)
    x = np.arange(n, dtype=float)
    base = float(out["close"].iloc[cut])
    close = base + 1000.0 + 4.0 * x + 80.0 * np.sin(x / 2.0)
    open_ = np.r_[base, close[:-1]]
    high = np.maximum(open_, close) + 20.0
    low = np.minimum(open_, close) - 20.0
    volume = 1_000_000.0 + 1000.0 * x

    out.loc[tail_index, ["open", "high", "low", "close", "volume"]] = np.column_stack(
        [open_, high, low, close, volume]
    )
    return out


def compare_outputs(full_output, test_output, cut, case, config):
    atol = float(config.get("atol", 1e-8))
    left = full_output["signal"].iloc[: cut + 1]
    right = test_output["signal"].reindex(left.index).iloc[: cut + 1]
    diff = (left - right).abs().replace([np.inf, -np.inf], np.nan).fillna(0.0)
    bad = diff[diff > atol]
    return {
        "max_abs_diff": float(diff.max()) if len(diff) else 0.0,
        "bad_points": int(len(bad)),
        "first_bad_idx": "" if bad.empty else str(bad.index[0]),
        "compared_points": int(len(diff)),
    }


def _load_module(path: Path):
    name = f"example_factor_{path.stem}_{abs(hash(str(path))) & 0xFFFFFFFF:x}"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module
