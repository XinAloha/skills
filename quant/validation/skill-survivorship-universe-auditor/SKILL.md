---
name: survivorship-universe-auditor
description: Use when historical symbol-date membership rows must be checked against listing and delisting dates, rebuilt into point-in-time universes, or inspected for missing delisting returns before backtesting.
license: GPL-3.0-only
metadata:
  organization: QuantSkills
  organization_url: https://github.com/quantskills
  repository: skill-survivorship-universe-auditor
  repository_url: https://github.com/quantskills/skill-survivorship-universe-auditor
  project_type: skill
  collection: survivorship-universe
  creator: adennng
  creator_url: https://github.com/adennng
  maintainer: adennng
  maintainer_url: https://github.com/adennng
quantSkills:
  project_type: skill
  category: tooling
  tags: [survivorship-bias, point-in-time, delisting, universe, pandadata]
  platforms: [claude-code, codex, openclaw, cursor]
  language: zh-en
  status: draft
  validation_level: runnable
  maintainer_type: community
  requires: [skill-pandadata-api]
  summary_zh: 审计证券生命周期和成员资格，并按输入快照重建历史股票池、检查退市收益缺口。
  summary_en: Audit lifecycle and membership rows, rebuild supplied point-in-time universes, and flag missing delisting returns.
  license: GPL-3.0-only
---

# 生存者偏差股票池审计

把输入研究制品当作需要验证的证据，而不是默认可信的结果。先冻结口径，再运行确定性检查，最后把“已证实的问题”和“缺失证据”分开报告。

## 核心工作流

1. 核对证券生命周期字段
2. 按输入中明确存在的历史日期重建 eligible universe
3. 检查上市前/退市后误入股票池
4. 检查退市日收益；仅在普通收益和退市收益均存在时量化偏差
5. 运行 `python scripts/audit_universe.py --demo` 做离线烟雾测试；处理真实数据时用 `--input <csv> --out <report.json>`。
6. 按 `references/output-contract.md` 输出机器可读 JSON 和简洁中文结论。

## 输入契约

包含 symbol、date、eligible、listed_at、delisted_at、return、delisting_return 的成员资格或收益 CSV。

- `symbol`、`date`、`listed_at` 必须非空；日期严格使用 `YYYY-MM-DD`，`delisted_at` 可为空。
- `eligible` 只能是字符串 `0` 或 `1`；同一稳定身份和日期只能有一行。
- `listed_at` 不得晚于 `delisted_at`；同一稳定身份的生命周期元数据必须跨行一致。
- `return` 表示未纳入退市处理的普通简单收益，`delisting_return` 表示权威来源给出的、已包含退市影响的同周期总收益；两者可空，但非空时必须有限且不得小于 `-1`。
- `stable_id` 可选；提供时用于跨 ticker 连接同一证券。缺少完整稳定标识符时只能披露限制，不能宣称已消除代码迁移偏差。

字段名不一致时先显式建立映射，不要猜测。缺少关键字段时停止定量结论，并列出补数清单。

## 运行参数

- `--demo`：使用内置样例；与 `--input` 互斥且二者必须提供一个。
- `--input <csv>`：读取 UTF-8 CSV；与 `--demo` 互斥且二者必须提供一个。
- `--out <json>`：可选输出路径；省略时输出到标准输出。
- 同时提供两种数据入口或均未提供时，命令以参数错误码 2 退出。

## 输出契约

JSON 审计报告和需要修复的证券/日期清单。

读取 `references/output-contract.md` 获取统一的证据等级、结论状态和报告字段。输出至少包含：输入规模、参数/假设、逐项发现、限制和下一步修复。

## 方法与证据

在修改阈值、公式或解释前读取 `references/methodology.md`。保留数据版本、时区、样本窗、随机种子和所有降级项，使另一位研究员可以复现结果。

## 数据源策略

- 用户已提供规范 CSV 时直接使用，不重复调用外部数据源。
- 缺少市场数据且任务落在 PandaData 覆盖范围时，先读取 `references/pandadata-integration.md`，再使用兄弟 Skill `pandadata-api` 查询：`get_trade_cal`、`get_trade_list`、`get_stock_status_change`、`get_stock_daily`。
- 本 Skill 的分析脚本保持离线、确定性；PandaData 负责取数，字段标准化后再交给脚本，避免把认证、供应商响应和分析逻辑耦合。
- PandaData 未明确提供标准化退市收益；若研究要求精确 delisting_return，必须由用户或其他权威数据源补充，不能用 0 代替。

## 与 QuantSkills 现有能力的边界

它审计历史股票池，不负责因子计算、选股条件或指数估值分析。

## 使用边界

- 只用于量化研究、数据质量和风险分析，不构成投资建议。
- 不把缺失证据写成“通过”，不把启发式异常写成已证实违规。
- 不自动下单，不修改原始数据；把修复结果写到新文件。
