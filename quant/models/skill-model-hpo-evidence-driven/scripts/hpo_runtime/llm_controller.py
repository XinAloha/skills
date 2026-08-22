"""Compatibility hooks for Codex-external LLM decisions.

The skill does not call local LLM APIs from Python. Codex
decisions are exchanged through evidence/template/decision JSON files.
"""

from __future__ import annotations

from typing import Any, Mapping

from config_utils import ConfigError


def llm_enabled(cfg: Mapping[str, Any]) -> bool:
    llm_cfg = cfg.get("llm", {}) if isinstance(cfg.get("llm", {}), Mapping) else {}
    return bool(llm_cfg.get("enabled", False))


def request_space_update(cfg: Mapping[str, Any], evidence: Mapping[str, Any]) -> dict[str, Any]:
    raise ConfigError(
        "Local API LLM calls are not supported by this Skill; "
        "use decision_provider.type=codex_external so Codex writes decision JSON files."
    )
