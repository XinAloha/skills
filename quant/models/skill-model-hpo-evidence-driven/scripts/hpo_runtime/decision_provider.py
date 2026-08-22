"""Decision-provider abstraction for rule and Codex-external modes."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Mapping

from config_utils import ConfigError, json_default, write_json
from llm_space_decider import build_llm_guarded_evidence, validate_guarded_decision
from space_controller import decide_next_space


class ExternalDecisionRequired(ConfigError):
    """Raised when Codex-external mode stops after writing an evidence file."""

    def __init__(
        self,
        *,
        stage: str,
        evidence_path: Path,
        decision_path: Path,
        template_path: Path,
        message: str,
    ) -> None:
        super().__init__(message)
        self.stage = stage
        self.evidence_path = evidence_path
        self.decision_path = decision_path
        self.template_path = template_path

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": "external_decision_required",
            "stage": self.stage,
            "evidence_path": str(self.evidence_path),
            "decision_path": str(self.decision_path),
            "template_path": str(self.template_path),
            "message": str(self),
        }


def resolve_decision_provider_config(cfg: Mapping[str, Any], *, run_dir: Path) -> dict[str, Any]:
    raw = dict(_mapping(cfg.get("decision_provider")))
    controller_cfg = _mapping(cfg.get("space_controller"))
    llm_cfg = _mapping(cfg.get("llm"))

    provider_type = str(raw.get("type") or raw.get("mode") or "").strip().lower()
    if not provider_type:
        controller_mode = str(controller_cfg.get("mode", "rule")).strip().lower()
        if controller_mode == "codex_external" or bool(llm_cfg.get("enabled", False)):
            provider_type = "codex_external"
        else:
            provider_type = "rule"
    aliases = {
        "rule": "rule",
        "local_rule": "rule",
        "codex": "codex_external",
        "codex_external": "codex_external",
        "external": "codex_external",
    }
    if provider_type in {"openai", "openai_compatible", "llm"}:
        raise ConfigError("This Skill supports Codex external decisions only; use decision_provider.type=codex_external")
    if provider_type not in aliases:
        allowed = ", ".join(sorted(set(aliases.values())))
        raise ConfigError(f"decision_provider.type must be one of: {allowed}")

    provider_type = aliases[provider_type]
    decision_dir_value = raw.get("decision_dir") or "codex_decisions"
    decision_dir = Path(str(decision_dir_value)).expanduser()
    if not decision_dir.is_absolute():
        decision_dir = run_dir / decision_dir

    wait_for_decision = bool(raw.get("wait_for_decision", False))
    timeout_seconds = float(raw.get("timeout_seconds", 0.0 if not wait_for_decision else 3600.0))
    poll_interval_seconds = float(raw.get("poll_interval_seconds", 5.0))
    if timeout_seconds < 0:
        raise ConfigError("decision_provider.timeout_seconds must be non-negative")
    if poll_interval_seconds <= 0:
        raise ConfigError("decision_provider.poll_interval_seconds must be positive")

    on_missing = str(raw.get("on_missing") or ("stop" if wait_for_decision else "fallback")).strip().lower()
    on_invalid = str(raw.get("on_invalid") or "fallback").strip().lower()
    if on_missing not in {"fallback", "stop"}:
        raise ConfigError("decision_provider.on_missing must be fallback or stop")
    if on_invalid not in {"fallback", "stop"}:
        raise ConfigError("decision_provider.on_invalid must be fallback or stop")

    return {
        "type": provider_type,
        "decision_dir": str(decision_dir.resolve()),
        "wait_for_decision": wait_for_decision,
        "timeout_seconds": timeout_seconds,
        "poll_interval_seconds": poll_interval_seconds,
        "on_missing": on_missing,
        "on_invalid": on_invalid,
    }


def decide_space_with_provider(
    *,
    cfg: Mapping[str, Any],
    provider_config: Mapping[str, Any],
    trial_evidence: Mapping[str, Any],
    current_space: Mapping[str, Any],
    base_space: Mapping[str, Any],
    controller_config: Mapping[str, Any],
    model_type: str,
    decision_memory: list[Mapping[str, Any]],
) -> dict[str, Any]:
    provider_type = str(provider_config.get("type", "rule"))
    if provider_type == "rule":
        rule = _rule_decision(
            trial_evidence=trial_evidence,
            current_space=current_space,
            base_space=base_space,
            controller_config=controller_config,
            model_type=model_type,
        )
        return {
            "source": "rule",
            "accepted": True,
            "validation_errors": [],
            "raw_llm_decision": None,
            "validated_decision": rule,
        }
    if provider_type != "codex_external":
        raise ConfigError(f"Unsupported decision_provider.type: {provider_type}")

    evidence = build_llm_guarded_evidence(
        trial_evidence=trial_evidence,
        current_space=current_space,
        base_space=base_space,
        decision_memory=decision_memory,
        controller_config=controller_config,
    )
    paths = _space_decision_paths(provider_config, int(trial_evidence.get("round_id", 0)))
    _write_external_evidence(paths, evidence, _space_decision_template(evidence))
    raw_decision = _read_external_decision_or_none(paths, provider_config)
    if raw_decision is None:
        if str(provider_config.get("on_missing")) == "stop":
            raise ExternalDecisionRequired(
                stage=f"space_round_{int(trial_evidence.get('round_id', 0)):04d}",
                evidence_path=paths["evidence_path"],
                decision_path=paths["decision_path"],
                template_path=paths["template_path"],
                message="Codex-external space decision is required before continuing.",
            )
        return _fallback_space_record(
            trial_evidence=trial_evidence,
            current_space=current_space,
            base_space=base_space,
            controller_config=controller_config,
            model_type=model_type,
            errors=[f"external_decision_missing:{paths['decision_path']}"],
            raw_decision=None,
            evidence=evidence,
        )

    validated, errors = validate_guarded_decision(
        raw_decision,
        current_space=current_space,
        base_space=base_space,
        controller_config=controller_config,
        trial_evidence=trial_evidence,
    )
    if validated is None or errors:
        if str(provider_config.get("on_invalid")) == "stop":
            write_json(
                {
                    "raw_decision": raw_decision,
                    "validation_errors": errors,
                    "decision_path": str(paths["decision_path"]),
                },
                paths["error_path"],
            )
            raise ExternalDecisionRequired(
                stage=f"space_round_{int(trial_evidence.get('round_id', 0)):04d}",
                evidence_path=paths["evidence_path"],
                decision_path=paths["decision_path"],
                template_path=paths["template_path"],
                message="Codex-external space decision failed validation and must be corrected.",
            )
        return _fallback_space_record(
            trial_evidence=trial_evidence,
            current_space=current_space,
            base_space=base_space,
            controller_config=controller_config,
            model_type=model_type,
            errors=errors,
            raw_decision=raw_decision,
            evidence=evidence,
        )
    return {
        "source": "codex_external",
        "accepted": True,
        "validation_errors": [],
        "raw_llm_decision": raw_decision,
        "validated_decision": validated,
        "llm_evidence": evidence,
        "external_paths": _stringify_paths(paths),
    }


def request_final_selection_with_provider(
    *,
    cfg: Mapping[str, Any],
    provider_config: Mapping[str, Any],
    evidence: Mapping[str, Any],
) -> tuple[dict[str, Any] | None, str, str | None, dict[str, Any]]:
    provider_type = str(provider_config.get("type", "rule"))
    if provider_type == "rule":
        return None, "score_best_fallback", "final_selector_provider_is_rule", {}
    if provider_type != "codex_external":
        raise ConfigError(f"Unsupported decision_provider.type: {provider_type}")

    paths = _final_decision_paths(provider_config)
    _write_external_evidence(paths, evidence, _final_decision_template(evidence))
    raw_decision = _read_external_decision_or_none(paths, provider_config)
    if raw_decision is None:
        if str(provider_config.get("on_missing")) == "stop":
            raise ExternalDecisionRequired(
                stage="final_selection",
                evidence_path=paths["evidence_path"],
                decision_path=paths["decision_path"],
                template_path=paths["template_path"],
                message="Codex-external final-selection decision is required before continuing.",
            )
        return None, "codex_external_fallback", f"external_decision_missing:{paths['decision_path']}", _stringify_paths(paths)
    return raw_decision, "codex_external", None, _stringify_paths(paths)


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ConfigError(f"Decision file must contain a JSON object: {path}")
    return value


def _read_external_decision_or_none(paths: Mapping[str, Path], provider_config: Mapping[str, Any]) -> dict[str, Any] | None:
    decision_path = paths["decision_path"]
    if decision_path.exists():
        return _read_json(decision_path)

    if not bool(provider_config.get("wait_for_decision", False)):
        return None
    timeout = float(provider_config.get("timeout_seconds", 3600.0))
    poll_interval = float(provider_config.get("poll_interval_seconds", 5.0))
    started = time.monotonic()
    while True:
        if decision_path.exists():
            return _read_json(decision_path)
        if timeout and time.monotonic() - started >= timeout:
            return None
        time.sleep(poll_interval)


def _write_external_evidence(paths: Mapping[str, Path], evidence: Mapping[str, Any], template: Mapping[str, Any]) -> None:
    paths["evidence_path"].parent.mkdir(parents=True, exist_ok=True)
    write_json(evidence, paths["evidence_path"])
    if not paths["template_path"].exists():
        write_json(template, paths["template_path"])
    instructions_path = paths.get("instructions_path")
    if instructions_path is not None and not instructions_path.exists():
        write_json(_codex_instruction_payload(paths), instructions_path)


def _codex_instruction_payload(paths: Mapping[str, Path]) -> dict[str, Any]:
    return {
        "instruction": "Read evidence_path, write a strict JSON decision to decision_path, then rerun or resume the search command.",
        "evidence_path": str(paths["evidence_path"]),
        "decision_path": str(paths["decision_path"]),
        "template_path": str(paths["template_path"]),
        "must_follow_template_schema": True,
    }


def _rule_decision(
    *,
    trial_evidence: Mapping[str, Any],
    current_space: Mapping[str, Any],
    base_space: Mapping[str, Any],
    controller_config: Mapping[str, Any],
    model_type: str,
) -> dict[str, Any]:
    return decide_next_space(
        evidence=trial_evidence,
        current_space=current_space,
        base_space=base_space,
        controller_config=controller_config,
        model_type=model_type,
    )


def _fallback_space_record(
    *,
    trial_evidence: Mapping[str, Any],
    current_space: Mapping[str, Any],
    base_space: Mapping[str, Any],
    controller_config: Mapping[str, Any],
    model_type: str,
    errors: list[str],
    raw_decision: Mapping[str, Any] | None,
    evidence: Mapping[str, Any],
) -> dict[str, Any]:
    rule = _rule_decision(
        trial_evidence=trial_evidence,
        current_space=current_space,
        base_space=base_space,
        controller_config=controller_config,
        model_type=model_type,
    )
    validated, guard_errors = validate_guarded_decision(
        rule,
        current_space=current_space,
        base_space=base_space,
        controller_config=controller_config,
        trial_evidence=trial_evidence,
    )
    if validated is None:
        validated = {
            "action": "keep",
            "reason": "fallback_rule_decision_failed_guard",
            "next_search_space": None,
            "changed_params": [],
            "next_round_trials": controller_config.get("max_next_round_trials"),
            "hypothesis": None,
            "risk_flags": ["fallback_guard_failed"],
        }
    return {
        "source": "codex_external_rule_fallback",
        "accepted": False,
        "validation_errors": list(errors) + list(guard_errors),
        "raw_llm_decision": dict(raw_decision or {}),
        "validated_decision": validated,
        "llm_evidence": evidence,
    }


def _space_decision_paths(provider_config: Mapping[str, Any], round_id: int) -> dict[str, Path]:
    decision_dir = Path(str(provider_config["decision_dir"]))
    prefix = f"round_{round_id:04d}_space"
    return {
        "evidence_path": decision_dir / f"{prefix}_evidence.json",
        "decision_path": decision_dir / f"{prefix}_decision.json",
        "template_path": decision_dir / f"{prefix}_decision.template.json",
        "instructions_path": decision_dir / f"{prefix}_codex_instructions.json",
        "error_path": decision_dir / f"{prefix}_decision_error.json",
    }


def _final_decision_paths(provider_config: Mapping[str, Any]) -> dict[str, Path]:
    decision_dir = Path(str(provider_config["decision_dir"]))
    return {
        "evidence_path": decision_dir / "final_selection_evidence.json",
        "decision_path": decision_dir / "final_selection_decision.json",
        "template_path": decision_dir / "final_selection_decision.template.json",
        "instructions_path": decision_dir / "final_selection_codex_instructions.json",
        "error_path": decision_dir / "final_selection_decision_error.json",
    }


def _space_decision_template(evidence: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "action": "keep",
        "reason": "Explain the evidence-grounded decision.",
        "next_search_space": None,
        "next_round_trials": evidence.get("max_next_round_trials"),
        "hypothesis": "Optional hypothesis for the next round.",
        "risk_flags": ["optional_risk_flag"],
    }


def _final_decision_template(evidence: Mapping[str, Any]) -> dict[str, Any]:
    policy = _mapping(evidence.get("selection_policy"))
    allowed = list(policy.get("allowed_selected_trial_ids") or [])
    return {
        "selected_trial_id": allowed[0] if allowed else "",
        "reason": "Explain why this existing center trial is selected.",
        "risk_flags": ["optional_risk_flag"],
        "confidence": "medium",
    }


def _stringify_paths(paths: Mapping[str, Path]) -> dict[str, str]:
    return {key: str(value) for key, value in paths.items()}
