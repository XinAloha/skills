"""Offline demo — self-contained (no repo package required)."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from rolling_beta import render_text, rolling_beta  # noqa: E402

rng = np.random.default_rng(21)
market = rng.normal(0, 0.01, size=300)
high = 1.6 * market + rng.normal(0, 0.005, size=300)
low = 0.35 * market + rng.normal(0, 0.008, size=300)
down = market < 0
low[down] = 0.9 * market[down] + rng.normal(0, 0.008, size=int(down.sum()))
print("\n########## CASE A: high beta asset ##########")
print(render_text(rolling_beta(high, market, window=60)))
print("\n########## CASE B: asymmetric beta asset ##########")
print(render_text(rolling_beta(low, market, window=60)))
