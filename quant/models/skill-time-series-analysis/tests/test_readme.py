from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _mermaid_blocks(markdown: str) -> list[str]:
    return re.findall(r"```mermaid\n(.*?)\n```", markdown, flags=re.DOTALL)


def _assert_basic_flowchart_parseable(block: str) -> None:
    lines = [line.strip() for line in block.strip().splitlines() if line.strip()]

    assert lines[0] == "flowchart TD"
    assert block.count("[") == block.count("]")
    assert block.count("{") == block.count("}")
    assert block.count('"') % 2 == 0

    edge_pattern = re.compile(
        r'^[A-Za-z0-9_]+(?:\[(?:"[^"]+")\]|\{(?:"[^"]+")\})?'
        r"\s+-->\s+"
        r'[A-Za-z0-9_]+(?:\[(?:"[^"]+")\]|\{(?:"[^"]+")\})?$'
    )
    for line in lines[1:]:
        assert edge_pattern.match(line), line


def test_readme_workflow_uses_mermaid_diagram() -> None:
    for filename in ["README.md", "README.en.md"]:
        text = (ROOT / filename).read_text(encoding="utf-8")
        blocks = _mermaid_blocks(text)

        assert blocks, f"{filename} should contain a Mermaid workflow diagram"
        _assert_basic_flowchart_parseable(blocks[0])
        assert "No diagram type detected" not in text
