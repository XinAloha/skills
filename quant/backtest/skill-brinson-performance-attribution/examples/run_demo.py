"""Offline demo — self-contained (no repo package required)."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from brinson import brinson_fachler, multiperiod_brinson, render_text  # noqa: E402

alloc_df = pd.DataFrame(
    [
        {"sector": "Tech", "w_p": 0.40, "w_b": 0.20, "r_p": 0.08, "r_b": 0.08},
        {"sector": "Banks", "w_p": 0.20, "w_b": 0.30, "r_p": 0.02, "r_b": 0.02},
        {"sector": "Energy", "w_p": 0.20, "w_b": 0.25, "r_p": 0.01, "r_b": 0.01},
        {"sector": "Consumer", "w_p": 0.20, "w_b": 0.25, "r_p": 0.03, "r_b": 0.03},
    ]
)
sel_df = pd.DataFrame(
    [
        {"sector": "Tech", "w_p": 0.25, "w_b": 0.25, "r_p": 0.10, "r_b": 0.05},
        {"sector": "Banks", "w_p": 0.25, "w_b": 0.25, "r_p": 0.04, "r_b": 0.03},
        {"sector": "Energy", "w_p": 0.25, "w_b": 0.25, "r_p": 0.02, "r_b": 0.02},
        {"sector": "Consumer", "w_p": 0.25, "w_b": 0.25, "r_p": 0.05, "r_b": 0.04},
    ]
)
print("\n########## CASE A: allocation tilt ##########")
print(render_text(brinson_fachler(alloc_df)))
p2 = alloc_df.copy()
p2["r_p"] = p2["r_p"] + 0.01
p2["r_b"] = p2["r_b"] + 0.005
print("\n########## CASE B: multi-period Carino link ##########")
print(render_text(multiperiod_brinson([alloc_df, sel_df, p2], method="fachler")))
