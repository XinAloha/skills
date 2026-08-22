#!/usr/bin/env python3
"""CLI entry point for upstream mRMR or SAGE factor selection."""

from __future__ import annotations

import argparse
import json

from factor_selection_runtime import run_factor_selection


def main() -> int:
    parser = argparse.ArgumentParser(description="Select factors with local standard mRMR or Marginal-SAGE")
    parser.add_argument("--input", required=True, help="Path to a JSON configuration file")
    args = parser.parse_args()
    summary = run_factor_selection(args.input)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
