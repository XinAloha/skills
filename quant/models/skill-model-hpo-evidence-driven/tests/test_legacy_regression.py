from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from run_hpo_search import _config_from_json_input, run_search  # noqa: E402


@pytest.mark.parametrize(
    ("example_name", "dependency", "model_type", "expected_score", "best_trial_id"),
    [
        (
            "hpo_lgbm_smoke.json",
            "lightgbm",
            "lgbm",
            83.74456307782646,
            "lgbm_trial_0000",
        ),
        (
            "hpo_mlp_smoke.json",
            "torch",
            "mlp",
            3.5240485801188663,
            "mlp_trial_0000",
        ),
    ],
)
def test_legacy_v1_smoke_matches_historical_result(
    tmp_path: Path,
    example_name: str,
    dependency: str,
    model_type: str,
    expected_score: float,
    best_trial_id: str,
):
    pytest.importorskip(dependency)
    output_root = tmp_path / model_type
    config_path, resolved_output_root = _config_from_json_input(
        ROOT / "examples" / example_name,
        str(output_root),
    )

    summary = run_search(config_path, resolved_output_root)

    assert summary["compatibility_profile"] == "legacy_v1"
    assert summary["evaluation_objective"] == "rankic_ir"
    assert summary["status"] == "evaluated"
    assert summary["num_trials_run"] == 4
    assert summary["num_successful_trials"] == 4
    assert summary["num_failed_trials"] == 0
    assert summary["best_trial_id"] == best_trial_id
    assert summary["best_score"] == pytest.approx(expected_score, abs=1e-12)
    assert summary["holdout_mode"] == "automatic"
    assert summary["holdout_status"] == "evaluated"

    run_dir = resolved_output_root / summary["run_id"]
    manifest = json.loads((run_dir / "search_manifest.json").read_text())
    assert manifest["trial_seed_policy"] == "legacy_trial_index"
    assert manifest["confirmation"]["enabled"] is False
    assert (run_dir / "final_holdout_metrics.json").exists()
    assert (run_dir / "final_holdout_predictions.csv").exists()
