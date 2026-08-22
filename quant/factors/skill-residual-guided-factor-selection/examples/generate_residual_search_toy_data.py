#!/usr/bin/env python3
"""Generate a deterministic wide-Parquet Residual-guided factor selection smoke dataset."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "residual_search" / "toy_data"
FACTOR_DIR = OUTPUT / "factors"


def main() -> None:
    rng = np.random.default_rng(20260721)
    dates = pd.bdate_range("2020-01-01", periods=120)
    symbols = [f"S{index:02d}" for index in range(12)]
    shape = (len(dates), len(symbols))
    market = rng.normal(size=shape)
    complement = rng.normal(size=shape)
    slow = np.cumsum(rng.normal(scale=0.12, size=shape), axis=0)
    factors = {
        "factor_base": market + rng.normal(scale=0.25, size=shape),
        "factor_complement": complement + rng.normal(scale=0.25, size=shape),
        "factor_redundant": market + rng.normal(scale=0.45, size=shape),
        "factor_slow": slow,
        "factor_noise_1": rng.normal(size=shape),
        "factor_noise_2": rng.normal(size=shape),
        "factor_noise_3": rng.normal(size=shape),
        "factor_noise_4": rng.normal(size=shape),
    }
    label = 0.018 * market - 0.014 * complement + rng.normal(scale=0.012, size=shape)

    FACTOR_DIR.mkdir(parents=True, exist_ok=True)
    for name, values in factors.items():
        pd.DataFrame(values, index=dates, columns=symbols).to_parquet(
            FACTOR_DIR / f"{name}.parquet"
        )
    pd.DataFrame(label, index=dates, columns=symbols).to_parquet(
        OUTPUT / "labels.parquet"
    )
    print(f"Wrote {len(factors)} factors and labels to {OUTPUT}")


if __name__ == "__main__":
    main()
