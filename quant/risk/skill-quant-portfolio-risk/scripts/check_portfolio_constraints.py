#!/usr/bin/env python3
"""Check common institutional portfolio constraints from a CSV weight file."""

from __future__ import annotations

import argparse
import csv
import math
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check target weights, exposure limits, sector concentration, and position count."
    )
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--asset-col", default="asset_id")
    parser.add_argument("--weight-col", default="target_weight")
    parser.add_argument("--sector-col", default="sector")
    parser.add_argument("--max-abs-weight", type=float)
    parser.add_argument("--max-gross", type=float)
    parser.add_argument("--min-net", type=float)
    parser.add_argument("--max-net", type=float)
    parser.add_argument("--target-net", type=float)
    parser.add_argument("--net-tolerance", type=float, default=1e-8)
    parser.add_argument("--max-sector-gross", type=float)
    parser.add_argument("--max-positions", type=int)
    return parser.parse_args()


def validate(args: argparse.Namespace) -> int:
    if not args.csv_path.exists():
        print(f"ERROR: file not found: {args.csv_path}")
        return 1
    if args.net_tolerance < 0:
        print("ERROR: --net-tolerance must be nonnegative")
        return 1
    for name, value in (
        ("--max-abs-weight", args.max_abs_weight),
        ("--max-gross", args.max_gross),
        ("--max-sector-gross", args.max_sector_gross),
    ):
        if value is not None and value < 0:
            print(f"ERROR: {name} must be nonnegative")
            return 1
    if args.max_positions is not None and args.max_positions < 0:
        print("ERROR: --max-positions must be nonnegative")
        return 1
    if args.max_sector_gross is not None and args.sector_col == "":
        print("ERROR: --sector-col is required with --max-sector-gross")
        return 1

    errors: list[str] = []
    weights: list[tuple[str, float, str]] = []
    seen: set[str] = set()
    try:
        with args.csv_path.open("r", newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            headers = set(reader.fieldnames or [])
            required = {args.asset_col, args.weight_col}
            if args.max_sector_gross is not None:
                required.add(args.sector_col)
            missing = sorted(required - headers)
            if missing:
                print("ERROR: missing columns: " + ", ".join(missing))
                return 1

            for row_number, row in enumerate(reader, start=2):
                asset = (row.get(args.asset_col) or "").strip()
                weight_text = (row.get(args.weight_col) or "").strip()
                sector = (row.get(args.sector_col) or "").strip() if args.sector_col in headers else ""
                if not asset:
                    errors.append(f"row {row_number}: blank asset identifier")
                    continue
                if asset in seen:
                    errors.append(f"row {row_number}: duplicate asset {asset!r}")
                seen.add(asset)
                try:
                    weight = float(weight_text)
                except ValueError:
                    errors.append(f"row {row_number}: invalid weight {weight_text!r}")
                    continue
                if not math.isfinite(weight):
                    errors.append(f"row {row_number}: weight must be finite")
                    continue
                if args.max_sector_gross is not None and not sector:
                    errors.append(f"row {row_number}: blank sector")
                weights.append((asset, weight, sector))
                if args.max_abs_weight is not None and abs(weight) > args.max_abs_weight + args.net_tolerance:
                    errors.append(f"row {row_number}: absolute weight exceeds limit")

    except (OSError, csv.Error) as exc:
        print(f"ERROR: could not read CSV: {exc}")
        return 1

    if not weights:
        errors.append("portfolio has no valid weight rows")
        print("ERROR: portfolio has no valid weight rows")
        return 1

    net = sum(weight for _, weight, _ in weights)
    gross = sum(abs(weight) for _, weight, _ in weights)
    long_gross = sum(weight for _, weight, _ in weights if weight > 0)
    short_gross = -sum(weight for _, weight, _ in weights if weight < 0)
    positions = sum(1 for _, weight, _ in weights if weight != 0)

    if args.max_gross is not None and gross > args.max_gross + args.net_tolerance:
        errors.append("gross exposure exceeds limit")
    if args.min_net is not None and net < args.min_net - args.net_tolerance:
        errors.append("net exposure is below limit")
    if args.max_net is not None and net > args.max_net + args.net_tolerance:
        errors.append("net exposure exceeds limit")
    if args.target_net is not None and abs(net - args.target_net) > args.net_tolerance:
        errors.append("net exposure misses target")
    if args.max_positions is not None and positions > args.max_positions:
        errors.append("number of nonzero positions exceeds limit")

    sector_gross: dict[str, float] = {}
    for _, weight, sector in weights:
        sector_gross[sector] = sector_gross.get(sector, 0.0) + abs(weight)
    if args.max_sector_gross is not None:
        for sector, value in sorted(sector_gross.items()):
            if value > args.max_sector_gross + args.net_tolerance:
                errors.append(f"sector {sector!r} gross exposure exceeds limit")

    print(
        f"positions={positions} gross={gross:.10g} net={net:.10g} "
        f"long={long_gross:.10g} short={short_gross:.10g}"
    )
    if args.max_sector_gross is not None:
        for sector, value in sorted(sector_gross.items()):
            print(f"sector[{sector}]_gross={value:.10g}")
    for error in errors:
        print("ERROR: " + error)
    if errors:
        print(f"FAILED: {len(errors)} error(s)")
        return 1
    print("PASSED")
    return 0


def main() -> int:
    return validate(parse_args())


if __name__ == "__main__":
    sys.exit(main())
