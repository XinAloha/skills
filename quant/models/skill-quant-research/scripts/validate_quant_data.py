#!/usr/bin/env python3
"""Validate common integrity properties of a CSV time-series dataset."""

from __future__ import annotations

import argparse
import csv
import math
import sys
from datetime import datetime
from pathlib import Path


def parse_timestamp(value: str) -> datetime:
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    return datetime.fromisoformat(text)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check timestamps, duplicate keys, prices, volume, and ordering in a CSV."
    )
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--time-col", default="timestamp")
    parser.add_argument("--asset-col", default="asset_id")
    parser.add_argument("--price-col", default="close")
    parser.add_argument("--volume-col", default="volume")
    parser.add_argument(
        "--single-series",
        action="store_true",
        help="Do not require an asset column and use timestamp as the unique key.",
    )
    parser.add_argument(
        "--require-sorted",
        action="store_true",
        help="Fail if rows are not sorted by asset and timestamp.",
    )
    parser.add_argument(
        "--require-timezone",
        action="store_true",
        help="Fail if a timestamp has no explicit timezone.",
    )
    return parser.parse_args()


def validate(args: argparse.Namespace) -> int:
    if not args.csv_path.exists():
        print(f"ERROR: file not found: {args.csv_path}")
        return 1

    errors: list[str] = []
    warnings: list[str] = []
    seen: set[tuple[str, datetime]] = set()
    previous_key: tuple[str, datetime] | None = None
    row_count = 0
    asset_values: set[str] = set()
    date_values: set[datetime] = set()

    try:
        with args.csv_path.open("r", newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            headers = set(reader.fieldnames or [])
            required = {args.time_col, args.price_col}
            if not args.single_series:
                required.add(args.asset_col)
            missing = sorted(required - headers)
            if missing:
                print("ERROR: missing columns: " + ", ".join(missing))
                return 1

            for row_number, row in enumerate(reader, start=2):
                row_count += 1
                asset = "__single_series__" if args.single_series else (row.get(args.asset_col) or "").strip()
                timestamp_text = (row.get(args.time_col) or "").strip()
                price_text = (row.get(args.price_col) or "").strip()
                volume_text = (row.get(args.volume_col) or "").strip() if args.volume_col in headers else ""

                if not asset:
                    errors.append(f"row {row_number}: blank asset identifier")
                if not timestamp_text:
                    errors.append(f"row {row_number}: blank timestamp")
                    continue
                try:
                    timestamp = parse_timestamp(timestamp_text)
                except ValueError:
                    errors.append(f"row {row_number}: invalid timestamp {timestamp_text!r}")
                    continue
                if timestamp.tzinfo is None:
                    message = f"row {row_number}: timestamp has no timezone"
                    (errors if args.require_timezone else warnings).append(message)

                if not price_text:
                    errors.append(f"row {row_number}: blank price")
                else:
                    try:
                        price = float(price_text)
                        if not math.isfinite(price) or price <= 0:
                            errors.append(f"row {row_number}: price must be finite and positive")
                    except ValueError:
                        errors.append(f"row {row_number}: invalid price {price_text!r}")

                if volume_text:
                    try:
                        volume = float(volume_text)
                        if not math.isfinite(volume) or volume < 0:
                            errors.append(f"row {row_number}: volume must be finite and nonnegative")
                    except ValueError:
                        errors.append(f"row {row_number}: invalid volume {volume_text!r}")

                key = (asset, timestamp)
                if key in seen:
                    errors.append(f"row {row_number}: duplicate key {asset!r}, {timestamp_text!r}")
                seen.add(key)
                asset_values.add(asset)
                date_values.add(timestamp)
                if args.require_sorted and previous_key is not None and key < previous_key:
                    errors.append(f"row {row_number}: rows are not sorted by asset and timestamp")
                previous_key = key
    except (OSError, csv.Error) as exc:
        print(f"ERROR: could not read CSV: {exc}")
        return 1

    print(f"rows={row_count} assets={len(asset_values)} timestamps={len(date_values)}")
    for warning in warnings:
        print("WARNING: " + warning)
    for error in errors:
        print("ERROR: " + error)
    if errors:
        print(f"FAILED: {len(errors)} error(s), {len(warnings)} warning(s)")
        return 1
    print(f"PASSED: {len(warnings)} warning(s)")
    return 0


def main() -> int:
    return validate(parse_args())


if __name__ == "__main__":
    sys.exit(main())
