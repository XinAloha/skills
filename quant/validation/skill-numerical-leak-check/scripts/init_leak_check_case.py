#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


ADAPTER_TEMPLATE = '''from __future__ import annotations

from copy import deepcopy
from pathlib import Path


def discover_cases(config):
    """Return one or many cases to check.

    Example for batch factors:
        root = Path(config["factor_dir"])
        return [{"case_id": p.stem, "path": str(p)} for p in sorted(root.glob("*.py"))]
    """
    return config.get("cases") or [{"case_id": "example_case"}]


def load_input(case, config):
    """Load the full input object for this case."""
    raise NotImplementedError("load project input here")


def input_length(input_obj, case, config):
    """Return the length of the time axis."""
    return len(input_obj)


def run_target(input_obj, case, config):
    """Run the target computation with the provided input object."""
    raise NotImplementedError("call the factor/feature/label/pipeline here")


def make_prefix(input_obj, cut, case, config):
    """Return an input object containing only history <= cut."""
    return input_obj.iloc[: cut + 1].copy()


def mutate_future(input_obj, cut, case, config):
    """Return an input object whose history <= cut is unchanged and future is replaced."""
    out = input_obj.copy(deep=True)
    # Replace this with domain-appropriate future mutation.
    # For DataFrames, mutate rows after cut strongly enough to expose future dependency.
    return out


def compare_outputs(full_output, test_output, cut, case, config):
    """Compare historical outputs <= cut and return max_abs_diff/bad_points."""
    atol = float(config.get("atol", 1e-8))
    left = full_output.iloc[: cut + 1]
    right = test_output.reindex(left.index).iloc[: cut + 1]
    diff = (left - right).abs()
    max_abs_diff = float(diff.max().max() if hasattr(diff, "columns") else diff.max())
    bad_points = int((diff > atol).sum().sum() if hasattr(diff, "columns") else (diff > atol).sum())
    first_bad_idx = ""
    if bad_points:
        bad = diff > atol
        if hasattr(bad, "columns"):
            stacked = bad.stack()
            first_bad_idx = str(stacked[stacked].index[0])
        else:
            first_bad_idx = str(bad[bad].index[0])
    return {"max_abs_diff": max_abs_diff, "bad_points": bad_points, "first_bad_idx": first_bad_idx}
'''


CONFIG_TEMPLATE = {
    "atol": 1e-8,
    "warn_atol": 1e-5,
    "seed": 20260709,
    "random_checkpoints": 0,
    "sensitive_points": [],
    "strict_ranges": [],
    "cases": [{"case_id": "example_case"}],
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize a numerical leak-check workspace.")
    parser.add_argument("out_dir", type=Path)
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    adapter_path = args.out_dir / "leak_check_adapter.py"
    config_path = args.out_dir / "leak_check_config.json"
    if not adapter_path.exists():
        adapter_path.write_text(ADAPTER_TEMPLATE, encoding="utf-8")
    if not config_path.exists():
        config_path.write_text(json.dumps(CONFIG_TEMPLATE, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"created {adapter_path}")
    print(f"created {config_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
