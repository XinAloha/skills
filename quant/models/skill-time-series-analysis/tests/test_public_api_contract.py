from __future__ import annotations

import ast
from pathlib import Path

import skill_time_series_analysis as ts

ROOT = Path(__file__).resolve().parents[1]

# Public symbols can be covered either by direct test references or by this
# explicit contract list when behavior is exercised through a higher-level API.
CONTRACT_COVERED_BY_BEHAVIOR: set[str] = set()


def _referenced_test_symbols() -> set[str]:
    symbols: set[str] = set()
    for path in (ROOT / "tests").glob("test_*.py"):
        if path.name == Path(__file__).name:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                symbols.update(alias.asname or alias.name for alias in node.names)
            elif isinstance(node, ast.Import):
                symbols.update(alias.asname or alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.Name):
                symbols.add(node.id)
            elif isinstance(node, ast.Attribute):
                symbols.add(node.attr)
    return symbols


def test_public_api_symbols_are_registered_in_tests() -> None:
    public_symbols = set(ts.__all__)
    covered_symbols = _referenced_test_symbols() | CONTRACT_COVERED_BY_BEHAVIOR

    assert not (CONTRACT_COVERED_BY_BEHAVIOR - public_symbols)
    assert not (public_symbols - covered_symbols)
    for symbol in public_symbols:
        assert hasattr(ts, symbol), symbol
