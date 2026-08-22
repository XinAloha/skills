"""B10 测试聚合入口（向后兼容）。

历史使用方式 ``python scripts/test.py`` 仍能跑通：本脚本动态从 ``scripts/tests``
子目录里发现以 ``test_`` 开头的函数，逐个调用，等价于 ``python -m pytest tests``。
对接 pytest 时也能直接走 ``python -m pytest scripts/tests``，因为子目录里的每个
模块本身就是合规测试文件。

子模块拆分（v1.4）：
- ``tests/fixtures.py``：共享样本生成。
- ``tests/test_data_io.py``：输入校验 / 字段映射 / 类型边界。
- ``tests/test_run_metrics.py``：run() 输出 schema、IC/分层、方向、binary_success、bootstrap、cost。
- ``tests/test_visual_report.py``：HTML 渲染、图表占位、性能拆分复用。
- ``tests/test_research_diagnostics.py``：V7 研究层 + 中性化路径。
- ``tests/test_write_production.py``：生产写入往返、append upsert、daily_runner。

为了让 IDE / pytest collector 能直接用 ``python scripts/test.py``，本入口只做
"导入 + 调用"。新增测试请优先放到 tests/ 子目录里对应模块，不要再往本文件加。
"""

from __future__ import annotations

import inspect
import sys
import tempfile
from pathlib import Path

# 让 tests/ 包能 import build / metrics / data_io 等顶层模块
_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from tests import (  # noqa: E402
    test_data_io,
    test_research_diagnostics,
    test_run_metrics,
    test_visual_report,
    test_write_production,
)


_TEST_MODULES = (
    test_data_io,
    test_run_metrics,
    test_visual_report,
    test_research_diagnostics,
    test_write_production,
)


def _iter_tests():
    for module in _TEST_MODULES:
        for name, fn in vars(module).items():
            if not name.startswith("test_") or not callable(fn):
                continue
            yield module.__name__, name, fn


def main() -> int:
    failures: list[tuple[str, str, BaseException]] = []
    count = 0
    for module_name, name, fn in _iter_tests():
        sig = inspect.signature(fn)
        count += 1
        try:
            if "tmp_path" in sig.parameters:
                with tempfile.TemporaryDirectory() as td:
                    fn(Path(td))
            else:
                fn()
        except BaseException as exc:  # 包括 AssertionError
            failures.append((module_name, name, exc))
            print(f"[FAIL] {module_name}.{name}: {type(exc).__name__}: {exc}")
        else:
            # 简洁输出：只打通过摘要在末尾给出
            pass

    if failures:
        print(f"\n{len(failures)} of {count} tests failed")
        return 1
    print(f"all {count} tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
