"""Offline demo — self-contained (no repo package required)."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from stability_audit import audit_stability, render_text  # noqa: E402

rng = np.random.default_rng(11)
T, N = 120, 40
sticky = np.zeros((T, N))
sticky[0] = rng.normal(0, 1, size=N)
for t in range(1, T):
    sticky[t] = 0.85 * sticky[t - 1] + rng.normal(0, 0.3, size=N)
noise = rng.normal(0, 1, size=(T, N))
print("\n########## CASE A: sticky signal (expect STABLE) ##########")
print(render_text(audit_stability(sticky, top_frac=0.1, cost_bps=15)))
print("\n########## CASE B: reshuffled noise (expect UNSTABLE) ##########")
print(render_text(audit_stability(noise, top_frac=0.1, cost_bps=15)))
