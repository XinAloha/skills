"""Offline demo — self-contained (no repo package required)."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from walk_forward import render_text, walk_forward  # noqa: E402

rng = np.random.default_rng(7)
T, N = 420, 50
noise = rng.normal(0, 1, size=(T, N))
fwd = rng.normal(0, 0.02, size=(T, N))
print("\n########## CASE A: noise signal (expect FAIL) ##########")
print(render_text(walk_forward(noise, fwd, train_size=120, test_size=40, step=40, embargo=5)))
true_signal = fwd + rng.normal(0, 0.03, size=(T, N))
print("\n########## CASE B: predictive signal (expect PASS) ##########")
print(render_text(walk_forward(true_signal, fwd, train_size=120, test_size=40, step=40, embargo=5)))
