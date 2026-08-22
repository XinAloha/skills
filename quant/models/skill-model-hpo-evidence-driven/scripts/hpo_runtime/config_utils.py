"""Configuration and filesystem helpers for the model autoresearch harness."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Iterable, Mapping


class ConfigError(ValueError):
    """Raised when configuration is missing required explicit settings."""


def load_config(path: str | os.PathLike[str]) -> dict[str, Any]:
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover
        raise ConfigError("PyYAML is required to read config.yaml. Install pyyaml.") from exc

    config_path = Path(path).expanduser().resolve()
    if not config_path.exists():
        raise ConfigError(f"Config file does not exist: {config_path}")
    with config_path.open("r", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    if not isinstance(cfg, dict):
        raise ConfigError(f"Config must be a mapping: {config_path}")
    cfg.setdefault("_config_path", str(config_path))
    cfg.setdefault("_config_dir", str(config_path.parent))
    return cfg


def write_resolved_config(cfg: Mapping[str, Any], path: str | os.PathLike[str]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    serializable = {k: v for k, v in cfg.items() if not k.startswith("_")}
    try:
        import yaml

        text = yaml.safe_dump(serializable, allow_unicode=True, sort_keys=False)
    except ImportError:  # pragma: no cover
        text = json.dumps(serializable, ensure_ascii=False, indent=2)
    output.write_text(text, encoding="utf-8")


def require_mapping(cfg: Mapping[str, Any], path: Iterable[str]) -> Mapping[str, Any]:
    value: Any = cfg
    parts = list(path)
    for key in parts:
        if not isinstance(value, Mapping) or key not in value:
            raise ConfigError(f"Missing required config mapping: {'.'.join(parts)}")
        value = value[key]
    if not isinstance(value, Mapping):
        raise ConfigError(f"Config value must be a mapping: {'.'.join(parts)}")
    return value


def require_value(cfg: Mapping[str, Any], path: Iterable[str]) -> Any:
    value: Any = cfg
    parts = list(path)
    for key in parts:
        if not isinstance(value, Mapping) or key not in value:
            raise ConfigError(f"Missing required config value: {'.'.join(parts)}")
        value = value[key]
    if value is None or value == "":
        raise ConfigError(f"Config value must be explicit: {'.'.join(parts)}")
    return value


def optional_value(cfg: Mapping[str, Any], path: Iterable[str], default: Any = None) -> Any:
    value: Any = cfg
    for key in path:
        if not isinstance(value, Mapping) or key not in value:
            return default
        value = value[key]
    return default if value is None else value


def resolve_path(path_value: str | os.PathLike[str] | None, base_dir: str | os.PathLike[str]) -> Path | None:
    if path_value is None or path_value == "":
        return None
    path = Path(path_value).expanduser()
    if not path.is_absolute():
        path = Path(base_dir).expanduser().resolve() / path
    return path.resolve()


def file_sha256(path: str | os.PathLike[str], block_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as fh:
        while True:
            block = fh.read(block_size)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def json_default(value: Any) -> Any:
    if hasattr(value, "item"):
        return value.item()
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def write_json(data: Mapping[str, Any] | list[Any], path: str | os.PathLike[str]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=json_default), encoding="utf-8")
