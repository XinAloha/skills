#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path


CASE_RE = re.compile(r"^## 用例 \d+：.+$", re.M)


def main() -> int:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / "references" / "test-cases.md"
    text = target.read_text(encoding="utf-8")

    cases = CASE_RE.findall(text)
    if len(cases) < 6:
        print(f"测试用例不足：在 {target} 中只找到 {len(cases)} 个案例，至少需要 6 个")
        return 1

    required_markers = ["**提示**:", "**期望**:", "**必须包含**:", "**必须避免**:"]
    missing = [marker for marker in required_markers if marker not in text]
    if missing:
        print(f"缺少必要标记：{', '.join(missing)}")
        return 1

    print(f"通过：{target} 中共有 {len(cases)} 个测试用例")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
