---
name: index-rebalance-event-study
description: Use when historical index additions, deletions, or weight changes need a reproducible abnormal-return and volume event study around announcement or effective dates without using current constituents as a proxy.
license: GPL-3.0-only
metadata:
  organization: QuantSkills
  organization_url: https://github.com/quantskills
  repository: skill-index-rebalance-event-study
  repository_url: https://github.com/quantskills/skill-index-rebalance-event-study
  project_type: skill
  collection: index-rebalance
  creator: adennng
  creator_url: https://github.com/adennng
  maintainer: adennng
  maintainer_url: https://github.com/adennng
quantSkills:
  project_type: skill
  category: analyst
  tags: [index, rebalance, event-study, abnormal-return, pandadata]
  platforms: [claude-code, codex, openclaw, cursor]
  language: zh-en
  status: draft
  validation_level: runnable
  maintainer_type: community
  requires: [skill-pandadata-api]
  summary_zh: 按公告日或生效日研究指数调整事件的异常收益、成交量及可选权重变化。
  summary_en: Study index-rebalance abnormal returns, volume, and optional weight changes by announcement or effective-date anchor.
  license: GPL-3.0-only
---

# 指数调仓事件研究

把输入研究制品当作需要验证的证据，而不是默认可信的结果。先冻结口径，再运行确定性检查，最后把“已证实的问题”和“缺失证据”分开报告。

## 核心工作流

1. 收集历史公告和生效日
2. 区分 add/delete/weight change
3. 使用可选 `relative_to` 字段分别按公告日或生效日计算 AR/CAR 和成交量
4. 通过分别运行事前、实施和事后窗口比较不同阶段；不把描述性 CAR 当作因果结论
5. 运行 `python scripts/study_index_rebalance.py --demo` 做离线烟雾测试；处理真实数据时用 `--input <csv> --out <report.json>`。
6. 按 `references/output-contract.md` 输出机器可读 JSON 和简洁中文结论。

## 输入契约

包含 event_id、symbol、action、announcement_date、effective_date、relative_day、return、benchmark_return、volume_ratio 的 CSV。

- `event_id` 与 `symbol` 必须非空；`action` 只能是 `add`、`delete` 或 `weight_change`。
- 两个事件日期必须使用 `YYYY-MM-DD`，且公告日不得晚于生效日。
- `relative_day` 必须是整数；同一 `event_id`、锚点和相对日只能有一行。
- `relative_to` 可省略，或填写 `announcement`/`effective`；填写后脚本按“事件×锚点”分别计算，禁止混算。
- `return`、`benchmark_return`、`volume_ratio` 必须为有限数，且成交量比不得为负；可选权重字段也必须为有限数。
- 每个事件锚点在指定窗口内至少有一条观测，否则返回证据不足。

字段名不一致时先显式建立映射，不要猜测。缺少关键字段时停止定量结论，并列出补数清单。

## 运行参数

- `--demo`：使用内置样例；与 `--input` 互斥且二者必须提供一个。
- `--input <csv>`：读取 UTF-8 CSV；与 `--demo` 互斥且二者必须提供一个。
- `--start <int>` / `--end <int>`：事件窗口起止相对日，默认 `0` 和 `1`，且 start 不得大于 end。
- `--out <json>`：可选输出路径；省略时输出到标准输出。
- 同时提供两种数据入口或均未提供时，命令以参数错误码 2 退出。

## 输出契约

JSON 逐事件锚点 CAR、成交量比和按 action、锚点分层的聚合结果。

读取 `references/output-contract.md` 获取统一的证据等级、结论状态和报告字段。输出至少包含：输入规模、参数/假设、逐项发现、限制和下一步修复。

## 方法与证据

在修改阈值、公式或解释前读取 `references/methodology.md`。保留数据版本、时区、样本窗、随机种子和所有降级项，使另一位研究员可以复现结果。

## 数据源策略

- 用户已提供规范 CSV 时直接使用，不重复调用外部数据源。
- 缺少市场数据且任务落在 PandaData 覆盖范围时，先读取 `references/pandadata-integration.md`，再使用兄弟 Skill `pandadata-api` 查询：`get_index_weights`、`get_index_daily`、`get_stock_daily`、`get_trade_cal`。
- 本 Skill 的分析脚本保持离线、确定性；PandaData 负责取数，字段标准化后再交给脚本，避免把认证、供应商响应和分析逻辑耦合。
- 若研究要求官方公告时间而不仅是权重快照变化，仍需补充指数公司公告；不得把首次观测日期冒充 announcement_date。

## 与 QuantSkills 现有能力的边界

它是指数调仓专项事件研究，不重复一般指数估值轮动，也不假设纳入必涨。

## 使用边界

- 只用于量化研究、数据质量和风险分析，不构成投资建议。
- 不把缺失证据写成“通过”，不把启发式异常写成已证实违规。
- 不自动下单，不修改原始数据；把修复结果写到新文件。
