from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "scripts" / "hpo_runtime"
sys.path.insert(0, str(RUNTIME))

from config_utils import ConfigError
from data_adapter import PanelData, _validate_panel_data
from extension_api import ModelCapabilities
from extension_registry import ExtensionRegistry
from plugin_loader import configure_extensions


def test_registry_resolves_model_alias_and_rejects_duplicates():
    class Plugin:
        name = "custom"
        aliases = ("alias",)
        capabilities = ModelCapabilities()

        def default_search_space(self):
            return {"alpha": {"type": "choice", "values": [1.0]}}

        def normalize_params(self, params):
            return dict(params)

        def create(self, params, seed):
            return object()

        def prepare_features(self, features, cfg):
            return features

    registry = ExtensionRegistry()
    plugin = Plugin()
    registry.register_model_plugin(plugin)
    assert registry.canonical_model_name("ALIAS") == "custom"
    assert registry.get_model_plugin("custom") is plugin
    with pytest.raises(ConfigError, match="already registered"):
        registry.register_model_plugin(plugin)


def test_external_modules_require_explicit_opt_in():
    cfg = {
        "_config_dir": str(ROOT),
        "extensions": {
            "plugin_roots": [str(ROOT / "extension_templates")],
            "modules": ["example_extensions"],
        },
    }
    with pytest.raises(ConfigError, match="allow_external"):
        configure_extensions(cfg)


def test_explicit_external_module_records_provenance():
    cfg = {
        "_config_dir": str(ROOT),
        "extensions": {
            "allow_external": True,
            "plugin_roots": [str(ROOT / "extension_templates")],
            "modules": ["example_extensions"],
        },
    }
    manifest = configure_extensions(cfg)
    module = manifest["external_modules"][0]
    assert module["module"] == "example_extensions"
    assert module["sha256"]
    assert "example_ridge" in manifest["registered_components"]["model_plugins"]

    next_cfg = {"_config_dir": str(ROOT), "extensions": {}}
    next_manifest = configure_extensions(next_cfg)
    assert "example_ridge" not in next_manifest["registered_components"]["model_plugins"]


def test_provider_contract_rejects_non_numeric_features():
    data = PanelData(
        panel=pd.DataFrame(
            {
                "date": [20200102],
                "ticker": ["A"],
                "y": [0.1],
                "bad": ["text"],
            }
        ),
        feature_columns=["bad"],
        warnings=[],
        metadata={},
    )
    with pytest.raises(ConfigError, match="must be numeric"):
        _validate_panel_data(data, "bad_provider")
