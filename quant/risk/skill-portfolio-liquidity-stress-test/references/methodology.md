# 方法论

## 核心原则

1. 压力期同时降低成交量并提高波动率/点差
2. 大仓位使用非线性冲击
3. 报告结果对参与率和 horizon 的敏感性

## 情景公式

- 压力 ADV：`adv × volume_shock`
- 日容量：`压力 ADV × participation`
- 期限最大容量：`min(position_value, 日容量 × horizon_days)`
- 赎回分配：`min(redemption_target, portfolio_value) × position_value / portfolio_value`
- 实际赎回出售：`min(赎回分配, 期限最大容量)`
- 冲击：`eta × volatility × sqrt(实际赎回出售 / (压力 ADV × horizon_days))`，日参与比例上限为 participation；成本另加半个完整买卖价差

最大期限容量与赎回出售是两个不同概念。成本只按实际赎回出售金额计算，不能用整个组合的最大变现容量成本代替小额赎回成本。

## 推荐执行顺序

1. 冻结输入快照、时间窗、时区、单位和标识符。
2. 运行脚本并保存 JSON，不在原始文件上就地修改。
3. 人工复核所有高严重度发现，区分确定性错误与启发式风险。
4. 改变参数时保留前后版本并解释原因。
5. 在独立样本或压力场景复算，不用单一历史窗口证明稳健。

## 主要参考

- [SEC Liquidity Risk Management Program Rules](https://www.sec.gov/resources-small-businesses/small-business-compliance-guides/investment-company-liquidity-risk-management-program-rules)
- [SEC Liquidity Risk FAQ](https://www.sec.gov/rules-regulations/staff-guidance/division-investment-management-frequently-asked-questions/investment-company-liquidity-risk-management-programs-frequently-asked-questions)

## 解释规则

- `pass` 只表示已执行的检查未发现问题，不代表策略有效或未来盈利。
- `fail` 必须附具体记录、字段或计算证据。
- `insufficient-evidence` 用于关键字段、历史版本或真实执行信息缺失。
