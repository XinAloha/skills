"""In-process registry for HPO extension implementations."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from config_utils import ConfigError


ComponentFactory = Callable[[Mapping[str, Any]], Any]


class ExtensionRegistry:
    def __init__(self) -> None:
        self._factor_providers: dict[str, ComponentFactory] = {}
        self._feature_pipelines: dict[str, ComponentFactory] = {}
        self._model_plugins: dict[str, Any] = {}
        self._model_aliases: dict[str, str] = {}
        self._builtins_registered = False

    @staticmethod
    def _name(value: str) -> str:
        name = str(value).strip().lower()
        if not name:
            raise ConfigError("Extension component name must not be empty")
        return name

    def register_factor_provider(self, name: str, factory: ComponentFactory, *, replace: bool = False) -> None:
        key = self._name(name)
        if not callable(factory):
            raise ConfigError(f"Factor provider factory must be callable: {key}")
        if key in self._factor_providers and not replace:
            raise ConfigError(f"Factor provider is already registered: {key}")
        self._factor_providers[key] = factory

    def register_feature_pipeline(self, name: str, factory: ComponentFactory, *, replace: bool = False) -> None:
        key = self._name(name)
        if not callable(factory):
            raise ConfigError(f"Feature pipeline factory must be callable: {key}")
        if key in self._feature_pipelines and not replace:
            raise ConfigError(f"Feature pipeline is already registered: {key}")
        self._feature_pipelines[key] = factory

    def register_model_plugin(self, plugin: Any, *, replace: bool = False) -> None:
        key = self._name(getattr(plugin, "name", ""))
        required_methods = ("default_search_space", "normalize_params", "create", "prepare_features")
        missing = [method for method in required_methods if not callable(getattr(plugin, method, None))]
        if missing or getattr(plugin, "capabilities", None) is None:
            raise ConfigError(
                f"Model plugin {key!r} is missing capabilities or methods: {missing}"
            )
        aliases = {key, *(self._name(alias) for alias in getattr(plugin, "aliases", ()))}
        collisions = sorted(alias for alias in aliases if alias in self._model_aliases and self._model_aliases[alias] != key)
        if collisions and not replace:
            raise ConfigError(f"Model plugin aliases are already registered: {collisions}")
        if key in self._model_plugins and not replace:
            raise ConfigError(f"Model plugin is already registered: {key}")
        self._model_plugins[key] = plugin
        for alias in aliases:
            self._model_aliases[alias] = key

    def create_factor_provider(self, name: str, params: Mapping[str, Any] | None = None) -> Any:
        key = self._name(name)
        if key not in self._factor_providers:
            raise ConfigError(f"Unknown factor provider {key!r}; registered: {sorted(self._factor_providers)}")
        return self._factor_providers[key](dict(params or {}))

    def create_feature_pipeline(self, name: str, params: Mapping[str, Any] | None = None) -> Any:
        key = self._name(name)
        if key not in self._feature_pipelines:
            raise ConfigError(f"Unknown feature pipeline {key!r}; registered: {sorted(self._feature_pipelines)}")
        return self._feature_pipelines[key](dict(params or {}))

    def canonical_model_name(self, name: str) -> str:
        key = self._name(name)
        if key not in self._model_aliases:
            raise ConfigError(f"Unknown model plugin {key!r}; registered: {sorted(self._model_plugins)}")
        return self._model_aliases[key]

    def get_model_plugin(self, name: str) -> Any:
        return self._model_plugins[self.canonical_model_name(name)]

    def inventory(self) -> dict[str, list[str]]:
        return {
            "factor_providers": sorted(self._factor_providers),
            "feature_pipelines": sorted(self._feature_pipelines),
            "model_plugins": sorted(self._model_plugins),
        }

    def clear(self) -> None:
        self._factor_providers.clear()
        self._feature_pipelines.clear()
        self._model_plugins.clear()
        self._model_aliases.clear()
        self._builtins_registered = False


REGISTRY = ExtensionRegistry()
