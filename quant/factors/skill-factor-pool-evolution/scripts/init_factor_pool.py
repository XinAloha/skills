#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


SKILL_ROOT = Path(__file__).resolve().parents[1]


DEFAULT_SEED_ALPHA_NAMES = [
    "alpha101:alpha_001",
    "alpha101:alpha_002",
    "alpha101:alpha_003",
    "alpha101:alpha_004",
    "alpha101:alpha_005",
    "alpha101:alpha_006",
    "alpha101:alpha_007",
    "alpha101:alpha_008",
    "alpha101:alpha_009",
    "alpha101:alpha_010",
    "alpha101:alpha_011",
    "alpha101:alpha_012",
    "alpha101:alpha_013",
    "alpha101:alpha_014",
    "alpha101:alpha_015",
    "alpha101:alpha_016",
    "alpha101:alpha_017",
    "alpha101:alpha_018",
    "alpha101:alpha_019",
    "alpha101:alpha_020",
]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a demo input pack for skill-factor-pool-evolution."
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory where the sample market data and evolution_input.json will be written.",
    )
    parser.add_argument(
        "--sample-instruments",
        type=int,
        default=6,
        help="Number of instruments in the generated sample panel.",
    )
    parser.add_argument(
        "--sample-days",
        type=int,
        default=140,
        help="Number of business days in the generated sample panel.",
    )
    return parser.parse_args()


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _build_demo_market_csv(path: Path, instruments: int, days: int) -> None:
    frame = _generate_sample_ohlcv(instruments=instruments, days=days, seed=42)
    output = frame.copy()
    output["date"] = pd.to_datetime(output["date"]).dt.strftime("%Y-%m-%d")
    keep_columns = [
        "date",
        "symbol",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "preClosePrice",
        "isOpen",
        "secShortName",
    ]
    output.loc[:, keep_columns].to_csv(path, index=False)


def _generate_sample_ohlcv(
    instruments: int = 6,
    days: int = 140,
    seed: int = 42,
    start_date: str = "2020-01-02",
) -> pd.DataFrame:
    if instruments <= 0 or days <= 0:
        raise ValueError("sample instruments and sample days must be positive")

    rng = np.random.default_rng(seed)
    dates = pd.bdate_range(start=start_date, periods=days)
    rows: list[pd.DataFrame] = []
    symbols = [f"{index + 1:06d}.XSHE" for index in range(instruments)]

    for symbol in symbols:
        base_price = rng.uniform(20.0, 120.0)
        returns = rng.normal(loc=0.0005, scale=0.018, size=days)
        close = base_price * np.cumprod(1.0 + np.clip(returns, -0.20, 0.20))
        open_price = close * (1.0 + rng.normal(loc=0.0, scale=0.006, size=days))
        open_gap = np.clip(rng.normal(loc=0.0, scale=0.006, size=days), -0.03, 0.03)
        pre_close = open_price / (1.0 + open_gap)
        upper_base = np.maximum(open_price, close)
        lower_base = np.minimum(open_price, close)
        high = upper_base * (1.0 + rng.uniform(0.001, 0.025, size=days))
        low = np.maximum(lower_base * (1.0 - rng.uniform(0.001, 0.025, size=days)), 0.01)
        volume = rng.integers(100_000, 5_000_000, size=days)
        rows.append(
            pd.DataFrame(
                {
                    "date": dates,
                    "symbol": symbol,
                    "open": open_price,
                    "high": high,
                    "low": low,
                    "close": close,
                    "volume": volume,
                    "preClosePrice": pre_close,
                    "isOpen": 1,
                    "secShortName": f"样本{symbol.split('.')[0]}",
                }
            )
        )

    return pd.concat(rows, ignore_index=True).sort_values(["date", "symbol"]).reset_index(drop=True)


def main() -> int:
    args = _parse_args()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    market_data_path = output_dir / "sample_market_data.csv"
    config_path = output_dir / "evolution_input.json"
    custom_seed_template_path = output_dir / "custom_seed_factors_template.json"

    _build_demo_market_csv(
        market_data_path,
        instruments=args.sample_instruments,
        days=args.sample_days,
    )

    config = {
        "market_data_csv_path": str(market_data_path),
        "alpha_library_root": "",
        "benchmark_csv_path": "",
        "custom_seed_factors_json_path": "",
        "output_dir": str(output_dir / "outputs" / "factor_pool_recommendation_demo"),
        "mode": "prepare",
        "generated_candidates_json_path": "",
        "seed_alpha_names": DEFAULT_SEED_ALPHA_NAMES,
        "rounds": 1,
        "random_seed": 42,
        "recommendation_top_k": 0,
        "mutate_strong_pool_only": False,
        "mutation_prompt_note": "Preserve the factor's core economic logic and only improve one or two structural components.",
        "crossover_prompt_note": "Use the stronger factor as the main logic anchor and borrow only complementary low-correlation structure.",
        "use_abs_metrics": True,
        "target_horizon_days": 5,
        "target_price_col": "open",
        "min_cross_section_samples": 3,
        "mi_bins": 10,
        "n_jobs": 1,
        "show_progress": True,
    }
    custom_seed_template = {
        "factors": [
            {
                "alpha_id": "custom_demo_factor",
                "name": "factor_custom_demo",
                "description": "Replace with your own seed factor.",
                "formula": "close / open - 1",
                "code": (
                    "def factor_custom_demo(df):\n"
                    "    df_copy = df.copy()\n"
                    "    factor_name = \"factor_custom_demo\"\n"
                    "    df_copy.loc[:, factor_name] = df_copy[\"close\"] / df_copy[\"open\"] - 1.0\n"
                    "    return df_copy[factor_name]\n"
                ),
                "metadata": {"note": "Replace this factor with your own code."},
            }
        ]
    }

    _write_json(config_path, config)
    _write_json(custom_seed_template_path, custom_seed_template)

    print(json.dumps({
        "ok": True,
        "output_dir": str(output_dir),
        "market_data_csv_path": str(market_data_path),
        "config_path": str(config_path),
        "custom_seed_template_path": str(custom_seed_template_path),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
