---
name: corporate-action-adjustment-auditor
description: Use when raw close, adjusted close, cash-dividend, and split-factor data must be checked for invalid event inputs, unexplained price jumps, or adjusted-return mismatches before equity research or backtesting.
license: GPL-3.0-only
metadata:
  organization: QuantSkills
  organization_url: https://github.com/quantskills
  repository: skill-corporate-action-adjustment-auditor
  repository_url: https://github.com/quantskills/skill-corporate-action-adjustment-auditor
  project_type: skill
  collection: corporate-action-adjustment
  creator: adennng
  creator_url: https://github.com/adennng
  maintainer: adennng
  maintainer_url: https://github.com/adennng
quantSkills:
  project_type: skill
  category: tooling
  tags: [corporate-action, adjusted-price, dividend, split, pandadata]
  platforms: [claude-code, codex, openclaw, cursor]
  language: zh-en
  status: draft
  validation_level: runnable
  maintainer_type: community
  requires: [skill-pandadata-api]
  summary_zh: 核对现金分红与拆并股场景下原始价格、复权价格和总收益的一致性。
  summary_en: Check raw and adjusted prices for cash-dividend and split consistency before research or backtesting.
  license: GPL-3.0-only
---

# 公司行动复权审计

把输入研究制品当作需要验证的证据，而不是默认可信的结果。先冻结口径，再运行确定性检查，最后把“已证实的问题”和“缺失证据”分开报告。

## 核心工作流

1. 按证券和日期排序原始/复权序列
2. 将现金分红和拆并股映射为价格调整
3. 核对原始总收益与复权收益
4. 定位复权收益冲突和未解释跳点
5. 运行 `python scripts/audit_adjustments.py --demo` 做离线烟雾测试；处理真实数据时用 `--input <csv> --out <report.json>`。
6. 按 `references/output-contract.md` 输出机器可读 JSON 和简洁中文结论。

## 输入契约

至少包含 symbol、date、close、adj_close、split_factor、cash_dividend 的 CSV。

- `symbol` 必须为非空且不含首尾空白的证券标识符；`date` 必须使用 ISO-8601 `YYYY-MM-DD` 格式。
- 每个待审计 `symbol` 至少需要两个日期不同的观测值，否则只能返回证据不足。
- `split_factor` 表示当前行事件中“每一旧股对应的新股数”，无拆并股时填 `1`，且必须大于 0。
- `cash_dividend` 表示当前行除息事件按每一旧股计的现金分红，无分红时填 `0`，且不得为负。
- `close` 与 `adj_close` 必须使用相同币种和价格单位并且大于 0。

字段名不一致时先显式建立映射，不要猜测。缺少关键字段时停止定量结论，并列出补数清单。

## 运行参数

- `--demo`：使用内置样例；与 `--input` 互斥且二者必须提供一个。
- `--input <csv>`：读取 UTF-8 CSV；与 `--demo` 互斥且二者必须提供一个。
- `--return-tolerance <float>`：原始总收益与复权收益允许的绝对偏差，默认 `0.02`，必须是有限非负数。
- `--jump-threshold <float>`：无事件原始价格跳点阈值，默认 `0.40`，必须是有限正数。
- `--out <json>`：可选输出路径；省略时把 JSON 写到标准输出。
- 同时提供两种数据源或两者均未提供时，命令以参数错误码 2 退出。

## 输出契约

JSON 异常清单，包含原始总收益、复权收益和冲突原因。

读取 `references/output-contract.md` 获取统一的证据等级、结论状态和报告字段。输出至少包含：输入规模、参数/假设、逐项发现、限制和下一步修复。

## 方法与证据

在修改阈值、公式或解释前读取 `references/methodology.md`。保留数据版本、时区、样本窗、随机种子和所有降级项，使另一位研究员可以复现结果。

## 数据源策略

- 用户已提供规范 CSV 时直接使用，不重复调用外部数据源。
- 缺少市场数据且任务落在 PandaData 覆盖范围时，先读取 `references/pandadata-integration.md`，再使用兄弟 Skill `pandadata-api` 查询：`get_stock_daily`、`get_stock_daily_pre`、`get_stock_daily_post`、`get_adj_factor`、`get_stock_dividend`、`get_stock_split`、`get_stock_cash_dividend`、`get_stock_allotment`。
- 本 Skill 的分析脚本保持离线、确定性；PandaData 负责取数，字段标准化后再交给脚本，避免把认证、供应商响应和分析逻辑耦合。
- 分拆、并购换股、代码迁移等复杂事件若不在返回结果中，必须保留为未覆盖事件，不能据此宣布完整通过。

## 与 QuantSkills 现有能力的边界

它验证数据处理，不预测公司行动，也不提供事件交易信号。

## 使用边界

- 只用于量化研究、数据质量和风险分析，不构成投资建议。
- 不把缺失证据写成“通过”，不把启发式异常写成已证实违规。
- 不自动下单，不修改原始数据；把修复结果写到新文件。
