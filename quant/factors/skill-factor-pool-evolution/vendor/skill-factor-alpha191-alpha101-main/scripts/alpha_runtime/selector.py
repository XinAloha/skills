from __future__ import annotations

from typing import Any

from .alpha101_formulas import normalize_alpha101_names
from .alpha191_formulas import normalize_alpha191_names


ALPHA_SET_ALIASES = {
    "101": "alpha101",
    "alpha101": "alpha101",
    "alpha_101": "alpha101",
    "worldquant101": "alpha101",
    "191": "alpha191",
    "alpha191": "alpha191",
    "alpha_191": "alpha191",
}


def normalize_alpha_sets(raw_sets: Any) -> list[str]:
    if raw_sets in (None, "", []):
        return ["alpha101", "alpha191"]
    if isinstance(raw_sets, str):
        raw_sets = [raw_sets]

    normalized: list[str] = []
    for raw in raw_sets:
        key = str(raw).strip().lower().replace("-", "").replace("_", "")
        alpha_set = ALPHA_SET_ALIASES.get(key)
        if not alpha_set:
            raise ValueError(f"Unsupported alpha set: {raw!r}. Use alpha101, alpha191, or both.")
        if alpha_set not in normalized:
            normalized.append(alpha_set)

    return normalized


def _split_qualified_name(raw_name: str) -> tuple[str | None, str]:
    text = str(raw_name).strip()
    if ":" not in text:
        return None, text
    prefix, name = text.split(":", 1)
    alpha_set = normalize_alpha_sets([prefix])[0]
    return alpha_set, name


def _normalize_names_for_set(alpha_set: str, names: list[str] | None) -> list[str]:
    if alpha_set == "alpha101":
        return normalize_alpha101_names(names)
    if alpha_set == "alpha191":
        return normalize_alpha191_names(names)
    raise ValueError(f"Unsupported alpha set: {alpha_set}")


def resolve_alpha_selection(config: dict[str, Any]) -> dict[str, list[str]]:
    alpha_sets = normalize_alpha_sets(config.get("alpha_sets"))
    raw_names = config.get("alpha_names", config.get("alpha_columns", []))
    raw_excludes = config.get("exclude_alpha_names", [])

    if isinstance(raw_names, str):
        raw_names = [] if raw_names.strip().lower() in {"", "all", "*"} else [raw_names]
    if isinstance(raw_excludes, str):
        raw_excludes = [raw_excludes]

    selected: dict[str, list[str]] = {}
    for alpha_set in alpha_sets:
        if not raw_names:
            selected[alpha_set] = _normalize_names_for_set(alpha_set, None)
            continue

        set_specific: list[str] = []
        for raw_name in raw_names:
            qualified_set, alpha_name = _split_qualified_name(str(raw_name))
            if qualified_set is None or qualified_set == alpha_set:
                set_specific.append(alpha_name)
        if set_specific:
            selected[alpha_set] = _normalize_names_for_set(alpha_set, set_specific)

    if not selected:
        raise ValueError("alpha_names did not match any selected alpha_sets.")

    excludes: dict[str, set[str]] = {alpha_set: set() for alpha_set in selected}
    for raw_name in raw_excludes or []:
        qualified_set, alpha_name = _split_qualified_name(str(raw_name))
        target_sets = [qualified_set] if qualified_set else list(selected)
        for alpha_set in target_sets:
            if alpha_set not in excludes:
                continue
            excludes[alpha_set].update(_normalize_names_for_set(alpha_set, [alpha_name]))

    for alpha_set, excluded in list(excludes.items()):
        selected[alpha_set] = [name for name in selected[alpha_set] if name not in excluded]
        if not selected[alpha_set]:
            raise ValueError(f"No {alpha_set} factors remain after applying exclude_alpha_names.")

    return selected
