"""CLI wrapper for evidence-driven model hyperparameter search.

The bundled runtime accepts a YAML config. This wrapper also accepts a JSON
input file so agent workflows can use a stable, portable entrypoint.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping


SCRIPT_DIR = Path(__file__).resolve().parent
RUNTIME_DIR = SCRIPT_DIR / "hpo_runtime"
sys.path.insert(0, str(RUNTIME_DIR))

from search_runner import run_search  # noqa: E402


WRAPPER_KEYS = {"output_root", "config"}
PATH_KEYS = {"feature_path", "label_path", "market_path", "universe_path"}


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Input JSON must be an object: {path}")
    return data


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError("PyYAML is required for YAML configs. Install pyyaml.") from exc
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"YAML config must be a mapping: {path}")
    return data


def _write_yaml(data: Mapping[str, Any], path: Path) -> None:
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError("PyYAML is required to write generated YAML configs. Install pyyaml.") from exc
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(dict(data), allow_unicode=True, sort_keys=False), encoding="utf-8")


def _resolve_relative_path(value: Any, base_dir: Path) -> Any:
    if not isinstance(value, str) or not value:
        return value
    path = Path(value).expanduser()
    if path.is_absolute():
        return str(path)
    return str((base_dir / path).resolve())


def _resolve_config_paths(cfg: dict[str, Any], base_dir: Path) -> dict[str, Any]:
    out = json.loads(json.dumps(cfg, ensure_ascii=False))
    for section_name in ("input", "data"):
        section = out.get(section_name)
        if not isinstance(section, dict):
            continue
        for key in PATH_KEYS:
            if key in section:
                section[key] = _resolve_relative_path(section[key], base_dir)
    extensions = out.get("extensions")
    if isinstance(extensions, dict) and isinstance(extensions.get("plugin_roots"), list):
        extensions["plugin_roots"] = [
            _resolve_relative_path(value, base_dir)
            for value in extensions["plugin_roots"]
        ]
    return out


def _config_from_json_input(path: Path, output_root_override: str | None) -> tuple[Path, Path]:
    raw = _load_json(path)
    base_dir = path.parent
    cfg_raw = raw.get("config") if isinstance(raw.get("config"), dict) else {k: v for k, v in raw.items() if k not in WRAPPER_KEYS}
    if not isinstance(cfg_raw, dict):
        raise ValueError("JSON input field 'config' must be an object when provided")
    cfg = _resolve_config_paths(cfg_raw, base_dir)

    output_root_value = output_root_override or raw.get("output_root") or "outputs"
    output_root = Path(_resolve_relative_path(output_root_value, base_dir)).resolve()
    generated_dir = output_root / "_generated_configs"
    generated_name = f"{path.stem}_{datetime.now().strftime('%Y%m%d%H%M%S')}.yaml"
    generated_config = generated_dir / generated_name
    _write_yaml(cfg, generated_config)
    return generated_config, output_root


def _config_from_yaml(path: Path, output_root_override: str | None) -> tuple[Path, Path]:
    raw = _load_yaml(path)
    output_root_value = output_root_override or raw.get("output_root") or "outputs"
    output_root = Path(_resolve_relative_path(output_root_value, path.parent)).resolve()
    return path, output_root


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run evidence-driven model hyperparameter search")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input", help="Portable JSON input file")
    source.add_argument("--config", help="Native YAML config file")
    parser.add_argument("--output-root", default=None, help="Override output root directory")
    args = parser.parse_args(argv)

    if args.input:
        config_path, output_root = _config_from_json_input(Path(args.input).expanduser().resolve(), args.output_root)
    else:
        config_path, output_root = _config_from_yaml(Path(args.config).expanduser().resolve(), args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    summary = run_search(config_path, output_root)
    run_dir = output_root / str(summary["run_id"])

    print(f"run_id: {summary['run_id']}")
    print(f"run_dir: {run_dir}")
    print(f"model_type: {summary.get('model_type')}")
    print(f"status: {summary.get('status')}")
    print(f"num_trials_run: {summary.get('num_trials_run')}")
    print(f"num_successful_trials: {summary.get('num_successful_trials')}")
    print(f"num_failed_trials: {summary.get('num_failed_trials')}")
    if summary.get("best_trial_id"):
        print(f"best_trial_id: {summary['best_trial_id']}")
        print(f"best_score: {summary['best_score']}")
    print(f"space_controller_mode: {summary.get('space_controller_mode')}")
    print(f"decision_provider_type: {summary.get('decision_provider_type')}")
    if summary.get("status") == "external_decision_required":
        required = summary.get("external_decision_required") or {}
        print(f"external_evidence_path: {required.get('evidence_path')}")
        print(f"external_decision_path: {required.get('decision_path')}")
    return 0 if summary.get("status") != "failed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
