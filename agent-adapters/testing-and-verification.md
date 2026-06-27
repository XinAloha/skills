---
description: 测试与验证规范（跨平台版） - pytest 分层、网络隔离、数据质量和导入检查
type: sub-document
applies-to: [claude-code, codex]
auto_execution_mode: 2
---

# 测试与验证

## 分层测试策略

所有层级都按同一套命令语义执行；差异只在工具调用方式：Claude Code 用 `Bash` 执行命令，Codex 用 `run_terminal_cmd` 执行同一命令（Windows 项目可选择 PowerShell 作为 shell）。长时任务在 Claude Code 中用 `Bash` 的 `run_in_background=true`；Codex 中用 `run_terminal_cmd` 启动并持续观察输出，必要时用 PowerShell 作业管理。

| 层级 | 目标 | 命令 | Claude Code 调用 | Codex 调用 |
|-----|------|------|------------------|------------|
| 语法/导入 | 快速发现语法、循环导入、缺依赖 | `python -m compileall data_collection test` | `Bash: python -m compileall data_collection test` | `run_terminal_cmd: python -m compileall data_collection test` |
| 单元测试 | 验证函数、类、异常分支，默认 mock 外部依赖 | `pytest test/unit -v --tb=short` | `Bash: pytest test/unit -v --tb=short` | `run_terminal_cmd: pytest test/unit -v --tb=short` |
| 集成测试 | 验证 CLI、调度、数据库协同 | `pytest test/integration -v --tb=short` | `Bash: pytest test/integration -v --tb=short` | `run_terminal_cmd: pytest test/integration -v --tb=short` |
| 数据质量 | 验证字段、schema、数据完整性规则 | `pytest test/data_quality -v --tb=short` | `Bash: pytest test/data_quality -v --tb=short` | `run_terminal_cmd: pytest test/data_quality -v --tb=short` |
| 诊断脚本 | 手动排查网络和真实数据源 | `python test/diagnostics/test_network.py` | `Bash: python test/diagnostics/test_network.py` | `run_terminal_cmd: python test/diagnostics/test_network.py` |

## 选择最小验证集

变更后先选最小但足够的验证集，避免把真实网络、全量数据或长耗时测试当作默认门槛。定位测试文件时：Claude Code 用 `Glob`/`Grep` 查找、`Read` 查看；Codex 用 `rg` 查找、`Get-Content`/编辑器查看。需要修正代码或测试时：Claude Code 用 `Edit`/`Write`；Codex 用 `apply_patch`。

| 变更范围 | 至少运行 | Claude Code 调用 | Codex 调用 |
|---------|---------|------------------|------------|
| 单个工具函数 | 对应 `test/unit/test_xxx.py` | `Bash: pytest test/unit/test_xxx.py -v --tb=short` | `run_terminal_cmd: pytest test/unit/test_xxx.py -v --tb=short` |
| 采集器字段映射 | 对应采集器单测 + `test/data_quality/test_api_column_schema.py` | `Bash: pytest <对应采集器单测> test/data_quality/test_api_column_schema.py -v --tb=short` | `run_terminal_cmd: pytest <对应采集器单测> test/data_quality/test_api_column_schema.py -v --tb=short` |
| 调度流程 | `test/integration/test_daily_job.py` 或相关用例 | `Bash: pytest test/integration/test_daily_job.py -v --tb=short` | `run_terminal_cmd: pytest test/integration/test_daily_job.py -v --tb=short` |
| 数据库后端/schema | `test/unit/test_database_backend.py` + 数据质量测试 | `Bash: pytest test/unit/test_database_backend.py test/data_quality -v --tb=short` | `run_terminal_cmd: pytest test/unit/test_database_backend.py test/data_quality -v --tb=short` |
| 配置加载 | `test/unit/test_config.py` | `Bash: pytest test/unit/test_config.py -v --tb=short` | `run_terminal_cmd: pytest test/unit/test_config.py -v --tb=short` |
| 全局重构 | compileall + unit + integration + data_quality | `Bash: python -m compileall data_collection test` 后分别跑 unit/integration/data_quality | `run_terminal_cmd: python -m compileall data_collection test` 后分别跑 unit/integration/data_quality |

## 网络测试规则

- 默认不把真实 API 请求作为必要验证；本地快速回归优先用 mock、fixture 和离线样本。
- 真实 API 诊断放在 `test/diagnostics/`，结果只作为排障线索。运行方式：Claude Code 用 `Bash: python test/diagnostics/test_network.py`；Codex 用 `run_terminal_cmd: python test/diagnostics/test_network.py`。
- 单元测试用 mock 固定输入输出，避免依赖交易日、行情可用性或账号额度。
- 需要网络的集成测试必须标记，CI 或本地快速回归可跳过。
- 不在测试代码里写真实 token、账号密码、内部 IP；需要检查敏感信息时，Claude Code 用 `Grep` 搜索可疑键名，Codex 用 `rg` 搜索可疑键名。

## 数据质量检查

涉及行情、复权、概念、龙虎榜、资金流向时检查：

- [ ] 必需字段存在。
- [ ] 日期、股票代码格式统一。
- [ ] OHLC 关系正确，价格和成交量不为负。
- [ ] 唯一键不会产生重复记录。
- [ ] 空数据路径可解释，不误判为采集成功。
- [ ] 多源字段语义一致。

数据质量用例的运行方式：Claude Code 用 `Bash: pytest test/data_quality -v --tb=short`；Codex 用 `run_terminal_cmd: pytest test/data_quality -v --tb=short`。若只验证某个 schema 或字段规则，先用 Claude Code `Grep`/Codex `rg` 定位测试名，再只跑对应测试文件或 `-k` 表达式。

## 跑测试时的工具调用

示例：验证股票采集器单测。

| 动作 | Claude Code | Codex |
|------|-------------|-------|
| 跑单个测试文件 | `Bash: pytest test/unit/test_stock_collector.py -v --tb=short` | `run_terminal_cmd: pytest test/unit/test_stock_collector.py -v --tb=short` |
| 失败输出过长 | `Bash: pytest test/unit/test_stock_collector.py -v --tb=line -x` | `run_terminal_cmd: pytest test/unit/test_stock_collector.py -v --tb=line -x` |
| 搜索测试或断言 | `Grep: "test_stock_collector|assert"`，必要时 `Glob: test/**/*.py` | `rg "test_stock_collector|assert" test` |
| 查看相关文件 | `Read: test/unit/test_stock_collector.py` | `Get-Content test/unit/test_stock_collector.py` |
| 修改相关文件 | `Edit` 精确替换，必要时 `Write` 覆盖已读文件 | `apply_patch` 精确补丁 |

- 失败输出过长时再加 `--tb=line` 或 `-x`（fail fast）：Claude Code 用 `Bash: pytest ... --tb=line -x`；Codex 用 `run_terminal_cmd: pytest ... --tb=line -x`。
- 长任务不要阻塞主流程：Claude Code 用 `Bash` 且设置 `run_in_background=true`，过会儿用 `BashOutput` 或对应后台任务输出读取结果；Codex 用 `run_terminal_cmd` 启动并观察输出，必要时用 PowerShell `Start-Job`/`Receive-Job` 管理。
- 不要在单条命令调用里链很多无关命令，便于用户审查：Claude Code 避免单条 `Bash` 串联大量命令；Codex 避免单条 `run_terminal_cmd` 串联大量命令。
- 多个独立且耗时的验证需要并行分派时，Claude Code 可用 `Agent`/`TaskCreate` 类能力拆分任务（仅 Claude Code 适用）；Codex 没有等价 agent 工具时，按最小验证集顺序执行并记录每条命令。

## 验证结果记录

交付时记录命令和结果，必须写清命令、平台工具和结论：

```markdown
验证：
- Claude Code `Bash: python -m compileall data_collection test` 通过；Codex `run_terminal_cmd: python -m compileall data_collection test` 等价
- Claude Code `Bash: pytest test/unit/test_xxx.py -v --tb=short` 通过 (12 passed)；Codex `run_terminal_cmd: pytest test/unit/test_xxx.py -v --tb=short` 等价
- Claude Code `Bash: pytest test/integration -v --tb=short` 跳过（需要 PostgreSQL，本地不可用）；Codex `run_terminal_cmd: pytest test/integration -v --tb=short` 同样应说明跳过原因
```

如果未运行完整测试，说明原因，例如依赖真实网络、耗时过长、缺少本地密钥或任务只改文档。

## 不要做的事

- 不要用 `Bash: cat` 看测试输出（Claude Code 直接看 `Bash` 工具返回结果即可）；Codex 不要额外用 `run_terminal_cmd: cat ...`、`type ...` 或 `Get-Content` 重读同一份测试输出，直接使用 `run_terminal_cmd` 返回结果。
- 不要用 `Bash: grep -i pass` 过滤测试输出（容易漏失败行）；Codex 不要用 `run_terminal_cmd: rg -i pass <输出文件>` 或 PowerShell `Select-String pass` 只筛通过行。
- 不要在测试里 `print(os.environ['TUSHARE_TOKEN'])`，也不要在 Codex/PowerShell 中把真实 token 回显到终端。
- 不要改测试让它通过（除非测试本身就错了，且修改原因被明确写入提交说明）；Claude Code 修改用 `Edit`/`Write` 并说明原因，Codex 修改用 `apply_patch` 并说明原因。
