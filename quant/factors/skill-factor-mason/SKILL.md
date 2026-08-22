---
name: factor-mason
description: 当需要开发、审查、验证或排错单因子股票 alpha 时，使用此 skill。适用于 A 股/港股/美股等权益市场的横截面选股、单因子回测、IC/IR 分析、行业/市值/beta 中性化、股票池过滤、未来函数检测、换手成本诊断和因子失效归因。
metadata:
  organization: QuantSkills
  organization_url: https://github.com/quantskills
  repository: skill-factor-mason
  repository_url: https://github.com/quantskills/skill-factor-mason
  project_type: skill
  collection: quantitative-research
  project_status: community-project
  review_status: unreviewed
  license: GPL-3.0-only
  category: quantitative-finance
---

# 因子砌墙师

## 项目声明

- 项目类型：Community Project / Skill；当前未声明为官方、认证或生产项目
- 维护者：本仓库维护者及贡献者
- 数据来源：由使用者提供或指定的行情、财务披露、公司行为、指数成分和行业分类数据
- 研究边界：仅用于量化研究与教育示例，不自动获取数据、不执行交易
- 已知限制：结果依赖数据质量、时点可得性、股票池构造、成本模型和样本外验证；本技能不能替代交易所规则或数据供应商文档

## 适用场景

1. 用户需要把一个单因子想法转成可审计的回测设计
2. 用户需要判断因子是否存在未来函数、样本污染或停牌价格问题
3. 用户需要解释 IC、Rank IC、ICIR、多空收益、换手和成本后的表现
4. 用户需要区分真正选股 alpha 与行业、市值、beta、流动性暴露
5. 用户提到单因子、选股、IC、因子中性化、A 股停牌、换手过高、回测失真或因子失效

## 研究立场

因子研究最常见的失败不是“没有公式”，而是研究者太早相信公式。此 skill 的默认立场是：**任何因子先按嫌疑人处理，只有通过时点、样本、成本和样本外四道检查，才允许被称作 alpha。**

## 核心逻辑

```text
raw_factor        = 用户定义的原始信号
tradable_factor   = lag(raw_factor, 可交易滞后)
clean_factor      = winsorize/standardize/filter(tradable_factor)
ic_series         = corr(rank(clean_factor_t), future_return_t+h)
long_short_return = top_quantile_return - bottom_quantile_return
net_return        = gross_return - turnover_cost - slippage - spread_cost
usable_alpha      = 样本外稳定 + 成本后可用 + 暴露可解释
```

## 输入参数

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| universe | str/list | 是 | 市场、指数、行业、股票池规则，例如“沪深 300”“全 A 非 ST” |
| factor_definition | str | 是 | 原始因子公式、字段来源、更新时间和经济含义 |
| as_of_date | str | 否 | 研究基准日，格式 YYYYMMDD；未给出时要求用户说明 |
| start_date/end_date | str | 否 | 回测区间 |
| label_horizon | int/str | 是 | 未来收益窗口，如 5D、20D、1M |
| rebalance_frequency | str | 是 | 调仓频率，如 daily、weekly、monthly |
| lag_rule | str | 是 | 信号可交易滞后规则，如 T+1 open、next close |
| cost_model | dict/str | 是 | 手续费、滑点、价差、借券成本 |
| neutralization | list | 否 | 行业、市值、beta、波动率、流动性等 |
| portfolio_rule | str | 否 | 分层、多空、多头、等权、市值加权等 |

## 工作流

### 1. 时点审计

- 明确每个字段何时发布、何时可获得、何时可交易
- 将会计数据、指数成分、行业分类和价格数据分别对齐
- 一旦发现未来信息，先重写因子，不继续回测

### 2. 样本清洗

- 处理停牌、ST、退市、上市未满期、涨跌停、低流动性和陈旧价格
- 不使用事后成分股构造历史股票池
- 明确缺失值是剔除、填充还是分组处理

### 3. 因子变换

- 对异常值做 winsorize 或 robust clipping
- 对横截面做 z-score、rank 或分位数变换
- 只在有研究动机时做行业、市值、beta 或风格中性化

### 4. 验证指标

| 指标 | 用途 |
| --- | --- |
| IC / Rank IC | 信号方向是否稳定 |
| ICIR | 信号稳定性 |
| 分层收益 | 单调性和尾部贡献 |
| 多空收益 | 理论 alpha 强度 |
| 换手率 | 交易成本压力 |
| 成本后收益 | 实盘可用性 |
| 衰减曲线 | 信号半衰期 |
| 状态切片 | 牛熊、震荡、流动性变化下是否失效 |

## 输出格式

返回结果必须包含：

1. **因子定义复述**：用可审计语言重写用户的因子
2. **时点与样本假设**：明确哪些数据可用、哪些样本被剔除
3. **回测方案**：标签、调仓、组合构建和成本模型
4. **诊断结论**：IC、收益、换手、成本和中性化后的解释
5. **失效风险**：未来函数、拥挤、成本、状态依赖或行业暴露
6. **下一步实验**：最多 3 个最值得做的验证，不泛泛罗列

## 验收要求

1. 未来函数检查必须通过
2. 样本池必须说明构造方法
3. 成本后结果必须单独讨论
4. 若使用中性化，必须解释为什么需要中性化
5. 若因子失效，必须说明更像数据问题、逻辑问题、成本问题还是市场状态问题

## 资源

- 研究手册：[references/playbook.md](references/playbook.md)
- 测试用例：[references/test-cases.md](references/test-cases.md)
- 用例校验：[scripts/check_test_cases.py](scripts/check_test_cases.py)
