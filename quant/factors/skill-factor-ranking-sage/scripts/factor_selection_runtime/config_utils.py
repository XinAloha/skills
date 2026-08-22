"""Configuration and artifact helpers for the two upstream selection methods."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

import numpy as np


class ConfigError(ValueError):
    """Raised when a factor-selection configuration is invalid."""


DEFAULT_CONFIG: dict[str, Any] = {
    "run_name": "factor_selection",
    "random_seed": 42,
    "mode": "mrmr",
    "selection_count": 20,
    "data": {
        "date_col": "date",
        "ticker_col": "symbol",
        "label_col": "y",
        "feature_include": [],
        "feature_exclude": [],
    },
    "validation": {"method": "fixed", "embargo_days": 0},
    "mrmr": {
        "relevance": "f",
        "redundancy": "c",
        "denominator": "mean",
    },
    "model": {"type": "lgbm", "params": {}},
    "sage": {
        "loss": "mse",
        "background_size": 128,
        "evaluation_size": 10000,
        "batch_size": 512,
        "n_permutations": None,
        "detect_convergence": True,
        "convergence_threshold": 0.025,
    },
}


def _deep_merge(base: dict[str, Any], override: Mapping[str, Any]) -> dict[str, Any]:
    result = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, Mapping) and isinstance(result.get(key), Mapping):
            result[key] = _deep_merge(dict(result[key]), value)
        else:
            result[key] = deepcopy(value)
    return result


def _resolve_path(value: Any, base_dir: Path) -> str:
    path = Path(str(value)).expanduser()
    if not path.is_absolute():
        path = base_dir / path
    return str(path.resolve())


def load_config(path: str | Path) -> dict[str, Any]:
    config_path = Path(path).expanduser().resolve()
    if not config_path.exists():
        raise FileNotFoundError(f"Input configuration does not exist: {config_path}")
    if config_path.suffix.lower() != ".json":
        raise ConfigError("Only JSON configuration files are supported")
    raw = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(raw, Mapping):
        raise ConfigError("The input configuration must be a JSON object")
    cfg = _deep_merge(DEFAULT_CONFIG, raw)
    cfg["_config_path"] = str(config_path)
    cfg["_config_dir"] = str(config_path.parent)

    mode = str(cfg.get("mode", "")).lower()
    if mode not in {"mrmr", "sage"}:
        raise ConfigError("mode must be one of: mrmr, sage")
    cfg["mode"] = mode

    input_cfg = cfg.get("input")
    if not isinstance(input_cfg, Mapping):
        raise ConfigError("input must be an object")
    for key in ("feature_path", "label_path"):
        if not input_cfg.get(key):
            raise ConfigError(f"input.{key} is required")
        cfg["input"][key] = _resolve_path(input_cfg[key], config_path.parent)
    cfg["output_root"] = _resolve_path(
        cfg.get("output_root", "outputs/factor_selection"), config_path.parent
    )

    if str(cfg["validation"].get("method", "fixed")).lower() != "fixed":
        raise ConfigError("validation.method must be fixed")
    cfg["validation"]["method"] = "fixed"
    for field in ("train_start", "train_end", "valid_start", "valid_end"):
        if cfg["validation"].get(field) in (None, ""):
            raise ConfigError(f"validation.{field} is required")
    if int(cfg["validation"].get("embargo_days", 0)) < 0:
        raise ConfigError("validation.embargo_days must be non-negative")

    cfg["selection_count"] = int(cfg.get("selection_count", 0))
    if cfg["selection_count"] < 1:
        raise ConfigError("selection_count must be at least 1")

    if mode == "mrmr":
        mrmr_cfg = cfg["mrmr"]
        unknown = set(mrmr_cfg) - {"relevance", "redundancy", "denominator"}
        if unknown:
            raise ConfigError(f"Unsupported mrmr options: {sorted(unknown)}")
        if mrmr_cfg.get("relevance") != "f":
            raise ConfigError("mrmr.relevance must be f for the local implementation")
        if mrmr_cfg.get("redundancy") != "c":
            raise ConfigError("mrmr.redundancy must be c")
        if mrmr_cfg.get("denominator") not in {"mean", "max"}:
            raise ConfigError("mrmr.denominator must be mean or max")
    else:
        model_type = str(cfg["model"].get("type", "")).lower()
        if model_type not in {"lgbm", "mlp"}:
            raise ConfigError("model.type must be lgbm or mlp in sage mode")
        cfg["model"]["type"] = model_type
        sage_cfg = cfg["sage"]
        unknown = set(sage_cfg) - {
            "loss",
            "background_size",
            "evaluation_size",
            "batch_size",
            "n_permutations",
            "detect_convergence",
            "convergence_threshold",
        }
        if unknown:
            raise ConfigError(f"Unsupported sage options: {sorted(unknown)}")
        if sage_cfg.get("loss") != "mse":
            raise ConfigError("sage.loss must be mse for the supported regression models")
        for field in ("background_size", "evaluation_size", "batch_size"):
            if int(sage_cfg[field]) < 1:
                raise ConfigError(f"sage.{field} must be at least 1")
        if sage_cfg.get("n_permutations") is not None:
            value = int(sage_cfg["n_permutations"])
            if value < 1:
                raise ConfigError("sage.n_permutations must be null or at least 1")
            sage_cfg["n_permutations"] = value
        threshold = float(sage_cfg["convergence_threshold"])
        if not 0 < threshold < 1:
            raise ConfigError("sage.convergence_threshold must be in (0, 1)")
    return cfg


def file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): json_safe(item) for key, item in value.items() if not str(key).startswith("_")}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return None if not np.isfinite(value) else float(value)
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, float) and not np.isfinite(value):
        return None
    return value


def write_json(path: str | Path, value: Any) -> None:
    Path(path).write_text(
        json.dumps(json_safe(value), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
