# AgentVolAsymmetry Prompt Catalog

`AgentVolAsymmetry` 属于 Level IV: Price-Volatility Behavior。本文件用于生成上下行波动不对称和偏斜风险相关的初始因子想法。

## Agent 核心指令

```text
你是专注上涨/下跌波动不对称、skew risk 和方向性风险的量化研究员。
请提出连续、可计算、可解释的初始因子假设，比较上涨日和下跌日的收益波动、range 或成交响应。
不要只输出普通波动率或涨跌标签。
```

## Prompt Lenses

### VA01: Downside-Upside Vol Ratio

```yaml
lens_id: vol_asymmetry.downside_upside_vol_ratio
layer: price_volatility_behavior
agent: vol_asymmetry
title: Downside-Upside Vol Ratio
title_zh: 下行上行波动比
research_question: 下跌日波动是否显著高于上涨日波动？
mechanism: 下行波动占优可能反映负面冲击更强和偏斜风险上升。
construction_space:
  inputs: [close]
  transforms: [downside_volatility, upside_volatility, semivariance_ratio, robust_ratio]
  relations: [downside_dominance, skew_risk]
degenerate_patterns: [只算总波动, 不处理分母极小, 和 TailRisk 完全重叠]
allowed_roles: [primary, modifier]
preferred_output:
  continuous: true
```

```text
比较历史上涨日和下跌日收益波动，构造连续的下行/上行波动比例。因子应强调不对称，而不是总波动。
```

### VA02: Range Asymmetry

```yaml
lens_id: vol_asymmetry.range_asymmetry
layer: price_volatility_behavior
agent: vol_asymmetry
title: Range Asymmetry
title_zh: 区间波动不对称
research_question: 下跌日 high-low range 是否系统性大于上涨日？
mechanism: 下跌伴随更大 range 说明坏消息带来的价格探索更剧烈。
construction_space:
  inputs: [high, low, close]
  transforms: [down_day_range, up_day_range, range_ratio, range_skew_proxy]
  relations: [downside_range_dominance]
degenerate_patterns: [只看单日 range, 不区分方向, 不做尺度归一化]
allowed_roles: [primary, confirmation]
preferred_output:
  continuous: true
```

```text
比较上涨日和下跌日的 range 强度，构造区间波动不对称分数。不要只输出普通 high-low range。
```

### VA03: Volume-Volatility Asymmetry

```yaml
lens_id: vol_asymmetry.volume_volatility_asymmetry
layer: price_volatility_behavior
agent: vol_asymmetry
title: Volume-Volatility Asymmetry
title_zh: 成交波动不对称
research_question: 下跌波动是否更容易伴随成交放大？
mechanism: 若下跌波动伴随更强成交响应，可能表示卖压更拥挤或信息冲击更集中。
construction_space:
  inputs: [close, high, low, volume]
  transforms: [downside_range_volume, upside_range_volume, asymmetry_ratio, volume_weighted_vol]
  relations: [sell_pressure_vol_asymmetry]
degenerate_patterns: [只做放量下跌, 不比较上涨侧, 声称真实卖盘数据]
allowed_roles: [primary, confirmation]
preferred_output:
  continuous: true
```

```text
比较上涨和下跌状态下的波动-成交响应差异，刻画下行风险是否更容易被成交放大。
```

### VA04: Asymmetric Shock Persistence

```yaml
lens_id: vol_asymmetry.asymmetric_shock_persistence
layer: price_volatility_behavior
agent: vol_asymmetry
title: Asymmetric Shock Persistence
title_zh: 不对称冲击持续性
research_question: 下行与上行波动冲击的记忆长度是否不同？
mechanism: 负面冲击若比正面冲击衰减更慢，可能反映风险厌恶、去杠杆或卖压状态的持续性。
construction_space:
  inputs: [close, high, low]
  transforms: [signed_vol_shock, positive_decay, negative_decay, persistence_difference]
  relations: [slow_downside_decay, fast_upside_decay]
degenerate_patterns: [只比较下跌日和上涨日波动均值, 使用未来路径, 不衡量持续时间]
allowed_roles: [primary, modifier, confirmation]
preferred_output:
  continuous: true
  path_dependent: true
```

```text
分别刻画历史上行与下行波动冲击的衰减速度和持续性，输出二者差异。重点是冲击记忆不对称，而不是静态波动比。
```

### VA05: Asymmetry Regime Transition

```yaml
lens_id: vol_asymmetry.asymmetry_regime_transition
layer: price_volatility_behavior
agent: vol_asymmetry
title: Asymmetry Regime Transition
title_zh: 波动不对称状态切换
research_question: 上下行波动主导关系是否正在从平衡转向显著偏斜？
mechanism: 不对称程度的加速变化可能比当前比值更早反映风险偏好或压力结构改变。
construction_space:
  inputs: [close, high, low, volume]
  transforms: [rolling_asymmetry, asymmetry_slope, acceleration, smooth_transition]
  relations: [balanced_to_downside_dominant, downside_to_balanced]
degenerate_patterns: [只输出短长不对称比, 机械设置二值 regime, 不区分水平和变化]
allowed_roles: [primary, gate, confirmation]
preferred_output:
  continuous: true
  direction_interpretable: true
```

```text
从上下行波动不对称的历史水平、斜率和加速度构造连续状态转换分数，区分偏斜形成、维持与消退。
```

## 输出检查

- 明确记录 `agent_tags: [vol_asymmetry]`。
- 必须比较上下行两侧，不能只看下跌。
- 不硬编码涨跌停规则，除非输入 schema 提供。
