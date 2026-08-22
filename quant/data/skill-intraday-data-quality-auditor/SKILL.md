---
name: intraday-data-quality-auditor
description: Use when normalized intraday OHLCV bars must be checked for duplicate or non-monotonic timestamps, missing intervals, invalid price relationships, non-positive prices, negative volume, or trading-date mismatches before research or backtesting.
license: GPL-3.0-only
metadata:
  organization: QuantSkills
  organization_url: https://github.com/quantskills
  repository: skill-intraday-data-quality-auditor
  repository_url: https://github.com/quantskills/skill-intraday-data-quality-auditor
  project_type: skill
  collection: intraday-data-quality
  creator: adennng
  creator_url: https://github.com/adennng
  maintainer: adennng
  maintainer_url: https://github.com/adennng
quantSkills:
  project_type: skill
  category: tooling
  tags: [intraday, data-quality, ohlcv, market-data, pandadata]
  platforms: [claude-code, codex, openclaw, cursor]
  language: zh-en
  status: draft
  validation_level: runnable
  maintainer_type: community
  requires: [skill-pandadata-api]
  summary_zh: 审计标准化日内 OHLCV 行情的时间戳、缺口、价格不变量、成交量和交易日一致性。
  summary_en: Audit normalized intraday OHLCV bars for timestamp, gap, price-invariant, volume, and trading-date defects.
  license: GPL-3.0-only
---

# 日内行情质量审计

把输入研究制品当作需要验证的证据，而不是默认可信的结果。先冻结口径，再运行确定性检查，最后把“已证实的问题”和“缺失证据”分开报告。

## 核心工作流

1. 按交易所日历和时区规范时间
2. 检测重复、缺口和乱序
3. 验证 OHLCV 不变量
4. 将缺口标记为待核查，不把计划休市、停牌或竞价边界直接判定为错误
5. 运行 `python scripts/audit_bars.py --demo` 做离线烟雾测试；处理真实数据时用 `--input <csv> --out <report.json>`。
6. 按 `references/output-contract.md` 输出机器可读 JSON 和简洁中文结论。

## 运行参数

- `--demo`：无值开关，使用内置异常样例，与 `--input` 二选一。
- `--input <csv>`：待审计 CSV 路径；未使用 `--demo` 时必填。
- `--out <json>`：可选输出路径；省略时将 JSON 写到标准输出。
- `--expected-seconds <int>`：预期 K 线间隔秒数，默认 `60`，必须大于 `0`。相邻时间戳间隔超过该值的 `1.5` 倍时标记 `missing_bar_gap`。

正常运行时生成 `references/output-contract.md` 定义的 JSON 报告。`--demo` 与 `--input` 必须且只能提供一个；两者同时提供或同时缺失属于 CLI 用法错误，程序按 `argparse` 约定输出用法并以退出码 `2` 结束。`--expected-seconds` 非正或输入证据不足时，JSON 报告状态为 `insufficient-evidence`，不输出伪“通过”。

## 输入契约

包含 symbol、trading_date、session、timestamp、open、high、low、close、volume 的分钟/秒级 OHLCV CSV。`session` 必须由交易所时段规则或期货合约 `trading_hours` 显式生成，不能只凭时间间隔猜测。同一 `symbol + trading_date + session` 组内的 ISO-8601 时间戳必须统一使用带时区偏移或不带时区偏移的格式；混用时输出 `insufficient-evidence`。本脚本不接收逐笔成交或 Level-2 队列数据。

字段名不一致时先显式建立映射，不要猜测。缺少关键字段时停止定量结论，并列出补数清单。

## 输出契约

JSON 数据质量报告和逐时间戳问题清单。

读取 `references/output-contract.md` 获取统一的证据等级、结论状态和报告字段。输出至少包含：输入规模、参数/假设、逐项发现、限制和下一步修复。

## 方法与证据

在修改阈值、公式或解释前读取 `references/methodology.md`。保留数据版本、时区、样本窗、随机种子和所有降级项，使另一位研究员可以复现结果。

## 数据源策略

- 用户已提供规范 CSV 时直接使用，不重复调用外部数据源。
- 缺少市场数据且任务落在 PandaData 覆盖范围时，先读取 `references/pandadata-integration.md`，再使用兄弟 Skill `pandadata-api` 查询：`get_trade_cal`、`get_stock_min`、`get_stock_rt_min`、`get_index_min`、`get_future_min`、`get_future_detail`。
- 本 Skill 的分析脚本保持离线、确定性；PandaData 负责取数，字段标准化后再交给脚本，避免把认证、供应商响应和分析逻辑耦合。
- 分钟接口不是逐笔成交或 Level-2 盘口；不能用它验证队列位置、撤单或逐笔撮合顺序。

## 与 QuantSkills 现有能力的边界

它识别数据异常，不自动删除成交，也不替代交易所最终裁定。

## 使用边界

- 只用于量化研究、数据质量和风险分析，不构成投资建议。
- 不把缺失证据写成“通过”，不把启发式异常写成已证实违规。
- 不自动下单，不修改原始数据；把修复结果写到新文件。
