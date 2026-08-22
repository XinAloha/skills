"""Controlled loading of built-in and explicitly enabled external extensions."""

from __future__ import annotations

import hashlib
import importlib
import re
import sys
from pathlib import Path
from typing import Any, Mapping, MutableMapping

from config_utils import ConfigError
from extension_api import EXTENSION_API_VERSION
from extension_registry import REGISTRY, ExtensionRegistry


_MODULE_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_.]*$")


def ensure_builtin_extensions(registry: ExtensionRegistry = REGISTRY) -> None:
    if registry._builtins_registered:
        return
    from builtin_extensions import register_builtin_extensions

    register_builtin_extensions(registry)
    registry._builtins_registered = True


def _component_config(value: Any, default_name: str) -> dict[str, Any]:
    if value in (None, ""):
        return {"name": default_name, "params": {}}
    if isinstance(value, str):
        return {"name": value, "params": {}}
    if not isinstance(value, Mapping):
        raise ConfigError("Extension component config must be a name string or mapping")
    name = str(value.get("name") or default_name).strip()
    params = value.get("params") or {}
    if not isinstance(params, Mapping):
        raise ConfigError(f"Extension component params for {name!r} must be a mapping")
    return {"name": name, "params": dict(params)}


def factor_provider_config(cfg: Mapping[str, Any]) -> dict[str, Any]:
    data_cfg = cfg.get("data") if isinstance(cfg.get("data"), Mapping) else {}
    return _component_config(data_cfg.get("provider"), "file_panel")


def feature_pipeline_config(cfg: Mapping[str, Any]) -> dict[str, Any]:
    feature_cfg = cfg.get("features") if isinstance(cfg.get("features"), Mapping) else {}
    return _component_config(feature_cfg.get("pipeline"), "cross_sectional")


def model_plugin_name(cfg: Mapping[str, Any]) -> str:
    model_cfg = cfg.get("model") if isinstance(cfg.get("model"), Mapping) else {}
    search_cfg = cfg.get("search") if isinstance(cfg.get("search"), Mapping) else {}
    return str(model_cfg.get("plugin") or search_cfg.get("model_type") or model_cfg.get("type") or "lgbm")


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_external_module(module_name: str, roots: list[Path], registry: ExtensionRegistry) -> dict[str, Any]:
    if not _MODULE_PATTERN.fullmatch(module_name):
        raise ConfigError(f"Invalid external extension module name: {module_name!r}")
    existing = sys.modules.get(module_name)
    existing_file = Path(getattr(existing, "__file__", "")).resolve() if existing is not None else None
    existing_allowed = bool(
        existing_file
        and any(existing_file == root or root in existing_file.parents for root in roots)
    )
    original_path = list(sys.path)
    try:
        for root in reversed(roots):
            sys.path.insert(0, str(root))
        importlib.invalidate_caches()
        if existing is not None and existing_allowed:
            module = importlib.reload(existing)
        else:
            sys.modules.pop(module_name, None)
            try:
                module = importlib.import_module(module_name)
            except Exception:
                if existing is not None:
                    sys.modules[module_name] = existing
                raise
    finally:
        sys.path[:] = original_path
    module_file = Path(getattr(module, "__file__", "")).resolve()
    allowed = any(module_file == root or root in module_file.parents for root in roots)
    if not allowed:
        if existing is not None:
            sys.modules[module_name] = existing
        else:
            sys.modules.pop(module_name, None)
        raise ConfigError(f"External extension module resolved outside configured plugin_roots: {module_file}")
    declared_api = getattr(module, "HPO_EXTENSION_API_VERSION", None)
    if declared_api != EXTENSION_API_VERSION:
        raise ConfigError(
            f"External extension module {module_name!r} declares API "
            f"{declared_api!r}; expected {EXTENSION_API_VERSION}"
        )
    register = getattr(module, "register", None)
    if not callable(register):
        raise ConfigError(f"External extension module {module_name!r} must expose register(registry)")
    register(registry)
    record = {
        "module": module_name,
        "file": str(module_file),
        "sha256": _file_sha256(module_file),
        "version": getattr(module, "__version__", None),
        "api_version": declared_api,
    }
    return record


def configure_extensions(cfg: MutableMapping[str, Any], registry: ExtensionRegistry = REGISTRY) -> dict[str, Any]:
    registry.clear()
    ensure_builtin_extensions(registry)
    raw = cfg.get("extensions") or {}
    if not isinstance(raw, Mapping):
        raise ConfigError("extensions config must be a mapping")
    allow_external = bool(raw.get("allow_external", False))
    raw_modules = raw.get("modules") or []
    raw_roots = raw.get("plugin_roots") or []
    if not isinstance(raw_modules, list) or not isinstance(raw_roots, list):
        raise ConfigError("extensions.modules and extensions.plugin_roots must be lists")
    module_names = list(raw_modules)
    root_values = list(raw_roots)
    if (module_names or root_values) and not allow_external:
        raise ConfigError("External extensions require extensions.allow_external=true")
    if allow_external and (not module_names or not root_values):
        raise ConfigError("External extensions require non-empty plugin_roots and modules")
    base_dir = Path(str(cfg.get("_config_dir", "."))).expanduser().resolve()
    roots: list[Path] = []
    for raw_root in root_values:
        root = Path(str(raw_root)).expanduser()
        root = root.resolve() if root.is_absolute() else (base_dir / root).resolve()
        if not root.is_dir():
            raise ConfigError(f"External extension plugin root is not a directory: {root}")
        roots.append(root)
    loaded = [_load_external_module(str(name), roots, registry) for name in module_names]
    extension_cfg = dict(raw)
    extension_cfg["allow_external"] = allow_external
    extension_cfg["plugin_roots"] = [str(root) for root in roots]
    extension_cfg["modules"] = [str(name) for name in module_names]
    cfg["extensions"] = extension_cfg
    manifest = {
        "api_version": EXTENSION_API_VERSION,
        "external_enabled": allow_external,
        "external_modules": loaded,
        "registered_components": registry.inventory(),
    }
    cfg["_extension_manifest"] = manifest
    return manifest
