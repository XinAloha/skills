#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Print a compact summary for leak_check_results.csv.")
    parser.add_argument("results_csv", type=Path)
    args = parser.parse_args()

    rows = list(csv.DictReader(args.results_csv.open("r", encoding="utf-8")))
    by_case: dict[str, str] = {}
    priority = {"ERROR": 4, "FAIL": 3, "WARN": 2, "PASS": 1}
    for row in rows:
        case_id = row.get("case_id", "")
        status = row.get("status", "UNKNOWN")
        if priority.get(status, 0) > priority.get(by_case.get(case_id, ""), 0):
            by_case[case_id] = status

    counts: dict[str, int] = {}
    for status in by_case.values():
        counts[status] = counts.get(status, 0) + 1

    issues = [row for row in rows if row.get("status") in {"WARN", "FAIL", "ERROR"}]
    print(json.dumps({"cases": len(by_case), "case_status_counts": counts, "issue_rows": len(issues)}, ensure_ascii=False, indent=2))
    for row in issues[:20]:
        print(
            f"{row.get('status')} case={row.get('case_id')} "
            f"type={row.get('test_type')} cut={row.get('cut')} "
            f"max_abs_diff={row.get('max_abs_diff')} first_bad_idx={row.get('first_bad_idx')} "
            f"error={row.get('error')}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
