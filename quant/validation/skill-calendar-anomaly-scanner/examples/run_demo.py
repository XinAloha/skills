"""Offline demo — self-contained (no repo package required)."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from calendar_scan import render_text, scan_calendar  # noqa: E402

rng = np.random.default_rng(31)
dates = pd.bdate_range("2015-01-01", periods=1800)
rets = rng.normal(0, 0.01, size=len(dates))
rets[dates.weekday == 4] += 0.006
print("\n########## CASE: Friday premium injected ##########")
print(render_text(scan_calendar(dates, rets)))
