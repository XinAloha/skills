"""CLI wrapper for explicit holdout evaluation."""

from __future__ import annotations

import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
RUNTIME_DIR = SCRIPT_DIR / "hpo_runtime"
sys.path.insert(0, str(RUNTIME_DIR))

from run_holdout_evaluation import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
