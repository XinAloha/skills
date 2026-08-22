# Output Schema

如果用户希望结果可以继续加工、筛选或转成代码，输出为 `idea_candidates.json` 风格的结构化对象。这个文件保留完整想法，不代表候选已经通过实证评估。

## 推荐字段

推荐顶层结构：

```json
{
  "generation_context": {
    "available_fields": ["open", "high", "low", "close", "volume"],
    "field_scope_source": "default",
    "idea_count": 5,
    "shortlist_count": 2,
    "research_sources": [],
    "custom_lens_pack_ids": []
  },
  "idea_candidates": []
}
```

每个候选至少包含：

```json
{
  "name": "seed_cycle_phase_energy_shift",
  "layer": "market_structure_cycle",
  "agent_tags": ["market_cycle"],
  "selected_lenses": [
    {
      "lens_id": "market_cycle.phase_divergence",
      "role": "primary",
      "origin": "builtin",
      "source_ids": []
    },
    {
      "lens_id": "market_cycle.cycle_energy_balance",
      "role": "modifier",
      "origin": "builtin",
      "source_ids": []
    }
  ],
  "prompt_lens_ids": [
    "market_cycle.phase_divergence",
    "market_cycle.cycle_energy_balance"
  ],
  "combination_type": "single_tag_multi_lens",
  "composition_operator": "modifier",
  "hypothesis": "短长周期相位开始错位且短周期能量上升时，可能表明市场主导节奏正在转移。",
  "economic_rationale": "价格轨迹的相位偏离提供结构变化线索，短长周期能量比用于判断偏离是否伴随主导节奏变化。",
  "inputs": ["close"],
  "operators": ["pct_change", "rolling_mean", "rolling_sum", "ratio"],
  "formula_sketch": "短长周期平滑收益的归一化相位偏离，再用短长收益能量比调节强度。",
  "factor_shape": {
    "formula_family": "multiscale_interaction",
    "shape_type": "interaction",
    "primary_signal": "short_long_phase_distance",
    "auxiliary_signal": "short_long_return_energy_ratio",
    "composition": "primary * (1 + bounded_modifier)",
    "pseudo_formula": "robust_zscore(short_smooth_return - long_smooth_return) * (1 + tanh(short_energy / long_energy - 1))",
    "windows": {
      "short": 5,
      "long": 20,
      "normalization": 60
    },
    "normalization": "rolling_median_mad with epsilon-protected energy ratio",
    "direction": "绝对值越高表示短长周期错位越强；正负表示短周期相对长周期的主导方向。",
    "implementation_steps": [
      "计算仅使用历史 close 的日收益",
      "计算短长窗口平滑收益轨迹",
      "构造短长轨迹的稳健归一化距离",
      "构造短长收益能量比并做有界变换",
      "按 modifier 语法组合两个分量"
    ]
  },
  "implementation_hint": "按标的排序后计算历史收益，分别构造短长平滑轨迹和收益平方和，对分母做除零保护。",
  "expected_behavior": "更值得在中短期节奏切换和趋势衰减阶段验证。",
  "failure_mode": "在长期单边趋势中，短周期能量增强可能只是噪声而非周期转换。",
  "suggested_horizon_days": 10,
  "implementation_priority": 1,
  "shortlisted": true,
  "similarity_tags": ["short_long_phase", "return_energy", "multiscale_interaction"],
  "anti_homogeneity_check": {
    "mechanism_signature": "phase_divergence|energy_shift|cycle_transition",
    "only_parameter_variant": false,
    "same_formula_new_labels": false,
    "nearest_candidate": null,
    "distinction": "以相位偏离和能量转移的交互刻画节奏切换，不是普通短长动量差。"
  },
  "self_check": {
    "uses_allowed_fields_only": true,
    "no_future_information": true,
    "logic_formula_aligned": true,
    "duplicate_of": null
  }
}
```

## 字段含义

- `generation_context.available_fields`: 本轮允许候选使用的实际字段。
- `generation_context.field_scope_source`: `default` 表示用户未说明字段，本轮默认使用日频 OHLCV；`user_provided` 表示由用户明确给出。
- `name`: 候选名称，适合作为后续代码因子名起点。
- `generation_context.research_sources`: 本轮使用的论文、研报或研究笔记来源摘要；未使用外部材料时为空。
- `generation_context.custom_lens_pack_ids`: 本轮加载的 Custom Lens Pack ID。
- `layer`: 七层之一。
- `agent_tags`: 本候选使用的一个或两个 Agent tag。
- `selected_lenses`: 实际选中的 Lens、组合角色、来源类型和 `source_ids`。`origin` 使用 `builtin`、`user_context` 或 `custom_pack`。
- `prompt_lens_ids`: 实际参与生成的 Prompt Lens，用于追踪和后续评估。
- `combination_type`: 生成类型，例如 `single_tag_single_lens`、`single_tag_multi_lens`、`same_layer_cross_tag` 或 `cross_layer`。
- `composition_operator`: Lens 之间的组合方式，例如 `none`、`modifier`、`confirmation`、`gate`、`stabilizer` 或 `contrast`。
- `hypothesis`: 一句话假设。
- `economic_rationale`: 行为或市场机制解释。
- `inputs`: 使用的原始字段。
- `operators`: 计划用到的核心算子或变换。
- `formula_sketch`: 人可读公式草图，不要求是最终可执行代码。
- `factor_shape`: 介于假设和代码之间的具体因子形态；字段细节见 `factor_shape_guidance.md`。
- `implementation_hint`: 落地实现建议。
- `expected_behavior`: 预期在哪类阶段更有效。
- `failure_mode`: 典型失效条件。
- `suggested_horizon_days`: 推荐先验证的收益 horizon。
- `implementation_priority`: 建议优先实现和验证的顺序，不代表预测有效性排名。
- `shortlisted`: 是否进入可执行 seed 生成阶段。
- `similarity_tags`: 用于批内查找机制和计算路径近邻的标签。
- `anti_homogeneity_check`: 判断候选是否只是换窗口、换名称或公式换皮，并说明与最近候选的实质差异。
- `self_check`: 字段合法性、未来信息、逻辑一致性和重复性检查。

## 输出建议

- 如果是面向对话，可先给简短总结，再附结构化列表。
- 如果要交给下游 skill，再按 `handoff_schema.md` 为 shortlist 生成 `custom_seed_factors.json`。
- 保持字段名稳定，不要频繁换 schema。
- 反同质化用于去重，不强制 Layer、Agent 或公式家族平均分布。
- 使用外部研究信息时，必须保留 Lens 来源；不得把模型推断伪装成来源原文结论。
