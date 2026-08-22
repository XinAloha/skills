from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from factor_selection_runtime import run_factor_selection
from factor_selection_runtime.config_utils import ConfigError, load_config


ROOT = Path(__file__).resolve().parents[1]


def _config(name: str) -> dict:
    return json.loads((ROOT / "examples" / name).read_text(encoding="utf-8"))


def _write_config(tmp_path: Path, config: dict, name: str = "run.json") -> Path:
    config["output_root"] = str(tmp_path / "outputs")
    config["input"]["feature_path"] = str(ROOT / "examples" / "toy_factors.csv")
    config["input"]["label_path"] = str(ROOT / "examples" / "toy_labels.csv")
    path = tmp_path / name
    path.write_text(json.dumps(config), encoding="utf-8")
    return path


def test_only_mrmr_and_sage_modes_are_accepted(tmp_path: Path) -> None:
    config = _config("factor_selection_mrmr_smoke.json")
    config["mode"] = "hybrid_retrain"
    path = _write_config(tmp_path, config)
    with pytest.raises(ConfigError, match="mode must be one of"):
        load_config(path)


def test_mrmr_smoke_uses_local_contract(tmp_path: Path) -> None:
    summary = run_factor_selection(
        _write_config(tmp_path, _config("factor_selection_mrmr_smoke.json"))
    )
    run_dir = Path(summary["run_dir"])
    names = {path.name for path in run_dir.iterdir()}
    assert {"mrmr_ranking.csv", "mrmr_redundancy_matrix.csv", "selected_factors.json"} <= names
    assert "sage_values.csv" not in names
    assert not any("drop_one" in name or "coalition" in name or "pruning" in name for name in names)
    ranking = pd.read_csv(run_dir / "mrmr_ranking.csv")
    assert list(ranking.columns) == ["rank", "factor", "relevance"]
    assert len(ranking) == 3
    selected = json.loads((run_dir / "selected_factors.json").read_text(encoding="utf-8"))
    assert selected["mode"] == "mrmr"
    assert selected["selected_factors"] == ranking["factor"].tolist()


@pytest.mark.parametrize(
    "example",
    ["factor_selection_lgbm_smoke.json", "factor_selection_mlp_smoke.json"],
)
def test_sage_smoke_uses_local_contract(tmp_path: Path, example: str) -> None:
    if "lgbm" in example:
        pytest.importorskip("lightgbm")
    summary = run_factor_selection(_write_config(tmp_path, _config(example), example))
    run_dir = Path(summary["run_dir"])
    names = {path.name for path in run_dir.iterdir()}
    assert {"sage_values.csv", "sage_metadata.json", "selected_factors.json"} <= names
    assert "mrmr_ranking.csv" not in names
    assert not any("drop_one" in name or "coalition" in name or "pruning" in name for name in names)
    values = pd.read_csv(run_dir / "sage_values.csv")
    assert list(values.columns) == ["rank", "factor", "sage_value", "sage_std"]
    assert len(values) == 5
    assert values["sage_value"].is_monotonic_decreasing
    selected = json.loads((run_dir / "selected_factors.json").read_text(encoding="utf-8"))
    assert selected["mode"] == "sage"
    assert selected["selected_factors"] == values.head(3)["factor"].tolist()


def test_local_config_rejects_removed_options(tmp_path: Path) -> None:
    config = _config("factor_selection_mrmr_smoke.json")
    config["mrmr"]["relevance"] = "rf"
    path = _write_config(tmp_path, config)
    with pytest.raises(ConfigError, match="relevance must be f"):
        load_config(path)

    config = _config("factor_selection_mrmr_smoke.json")
    config["mrmr"]["n_jobs"] = 2
    path = _write_config(tmp_path, config, "removed_option.json")
    with pytest.raises(ConfigError, match="Unsupported mrmr options"):
        load_config(path)
