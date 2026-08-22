#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from alpha_runtime.runtime import run_alpha_compute  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compute Alpha101/Alpha191 factor values based on JoinQuant formulas from long-form OHLCV CSV data."
    )
    parser.add_argument("--input", required=True, help="Path to input JSON.")
    parser.add_argument("--output", default=None, help="Optional output directory override.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = run_alpha_compute(args.input, output_dir=args.output)
    except Exception as exc:
        payload = {"ok": False, "error": str(exc)}
        print(json.dumps(payload, ensure_ascii=False, indent=2), flush=True)
        return 1

    public_result = dict(result)
    public_result.pop("nan_counts", None)
    print(json.dumps(public_result, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
