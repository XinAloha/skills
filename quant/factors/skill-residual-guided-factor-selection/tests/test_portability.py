from __future__ import annotations

from pathlib import Path

import yaml

from residual_factor_selection.config import load_config


def test_residual_factor_selection_config_resolves_all_portable_paths(tmp_path: Path) -> None:
    config_path = tmp_path / "experiment.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "data": {
                    "label_path": "data/labels.parquet",
                    "formula_source_repo": "formulas",
                    "prepared_feature_cache": "cache/features.parquet",
                },
                "beam": {
                    "checkpoint_path": "checkpoints/beam",
                    "resume_history": "checkpoints/beam_history.csv",
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    resolved = load_config(config_path)

    assert resolved["data"]["label_path"] == str(tmp_path / "data/labels.parquet")
    assert resolved["data"]["formula_source_repo"] == str(tmp_path / "formulas")
    assert resolved["data"]["prepared_feature_cache"] == str(
        tmp_path / "cache/features.parquet"
    )
    assert resolved["beam"]["checkpoint_path"] == str(tmp_path / "checkpoints/beam")
    assert resolved["beam"]["resume_history"] == str(
        tmp_path / "checkpoints/beam_history.csv"
    )
