---
name: portfolio-liquidity-stress-test
description: Use when holdings, value-based ADV, spread, and volatility data must be stress-tested for days-to-liquidate, horizon cash raised, redemption shortfall, and spread plus square-root impact costs.
license: GPL-3.0-only
metadata:
  organization: QuantSkills
  organization_url: https://github.com/quantskills
  repository: skill-portfolio-liquidity-stress-test
  repository_url: https://github.com/quantskills/skill-portfolio-liquidity-stress-test
  project_type: skill
  collection: portfolio-liquidity
  creator: adennng
  creator_url: https://github.com/adennng
  maintainer: adennng
  maintainer_url: https://github.com/adennng
quantSkills:
  project_type: skill
  category: analyst
  tags: [portfolio, liquidity, stress-test, redemption, pandadata]
  platforms: [claude-code, codex, openclaw, cursor]
  language: zh-en
  status: draft
  validation_level: runnable
  maintainer_type: community
  requires: [skill-pandadata-api]
  summary_zh: 估算组合在成交量冲击下的清算天数、期限内变现、赎回缺口和冲击成本。
  summary_en: Estimate portfolio liquidation days, horizon cash, redemption shortfall, and impact costs under volume stress.
  license: GPL-3.0-only
---

# 组合流动性压力测试

把输入研究制品当作需要验证的证据，而不是默认可信的结果。先冻结口径，再运行确定性检查，最后把“已证实的问题”和“缺失证据”分开报告。

## 核心工作流

1. 定义正常/压力 ADV 与参与率
2. 计算逐标的清算天数
3. 叠加点差和平方根冲击
4. 聚合指定期限内可变现比例与现金缺口
5. 运行 `python scripts/stress_liquidity.py --demo` 做离线烟雾测试；处理真实数据时用 `--input <csv> --out <report.json>`。
6. 按 `references/output-contract.md` 输出机器可读 JSON 和简洁中文结论。

## 输入契约

包含 symbol、position_value、adv、spread_bps、volatility 的持仓 CSV。`position_value` 与 `adv` 必须是同币种的金额口径；期货和期权需先按合约乘数归一化。

- `symbol` 必须非空且唯一；同一标的多个持仓批次应先合并，避免拆单低估非线性冲击。
- `position_value` 为待变现的非负总持仓金额，`adv` 为同币种的正数日均成交金额。
- `spread_bps` 为非负的完整买卖价差，`volatility` 为非负的小数波动率；所有数值必须有限。
- 指定赎回目标时，脚本按持仓市值比例分配出售目标，再受逐标的压力期限容量约束；不得把最大变现容量成本冒充小额赎回成本。

字段名不一致时先显式建立映射，不要猜测。缺少关键字段时停止定量结论，并列出补数清单。

## 运行参数

- `--demo`：使用内置样例；与 `--input` 互斥且二者必须提供一个。
- `--input <csv>`：读取 UTF-8 CSV；与 `--demo` 互斥且二者必须提供一个。
- `--participation <float>`：最大日参与率，默认 `0.1`，必须是有限的 `(0,1]` 数。
- `--volume-shock <float>`：ADV 压力乘数，默认 `0.5`，必须是有限正数。
- `--horizon-days <int>`：变现期限，默认 5 个交易日，必须为模型有限数值范围内的正整数。
- `--eta <float>`：平方根冲击系数，默认 `0.5`，必须是有限非负数。
- `--redemption-value <float>`：可选赎回现金目标，必须是有限非负数；省略时以整个组合为目标。
- `--out <json>`：可选输出路径；省略时输出到标准输出。

## 输出契约

JSON 组合可变现比例、成本和逐标的压力结果。

读取 `references/output-contract.md` 获取统一的证据等级、结论状态和报告字段。输出至少包含：输入规模、参数/假设、逐项发现、限制和下一步修复。

## 方法与证据

在修改阈值、公式或解释前读取 `references/methodology.md`。保留数据版本、时区、样本窗、随机种子和所有降级项，使另一位研究员可以复现结果。

## 数据源策略

- 用户已提供规范 CSV 时直接使用，不重复调用外部数据源。
- 缺少市场数据且任务落在 PandaData 覆盖范围时，先读取 `references/pandadata-integration.md`，再使用兄弟 Skill `pandadata-api` 查询：`get_stock_daily`、`get_stock_min`、`get_future_daily`、`get_future_min`、`get_option_daily`。
- 本 Skill 的分析脚本保持离线、确定性；PandaData 负责取数，字段标准化后再交给脚本，避免把认证、供应商响应和分析逻辑耦合。
- 持仓市值、赎回情景和真实 bid-ask spread 属于用户/经纪商数据；若用高低价差等代理，必须标记为 proxy 并做敏感性分析。

## 与 QuantSkills 现有能力的边界

它做流动性情景分析，不等同于监管分类，也不保证真实成交。

## 使用边界

- 只用于量化研究、数据质量和风险分析，不构成投资建议。
- 不把缺失证据写成“通过”，不把启发式异常写成已证实违规。
- 不自动下单，不修改原始数据；把修复结果写到新文件。
