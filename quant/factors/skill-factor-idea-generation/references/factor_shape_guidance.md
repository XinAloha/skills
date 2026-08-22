# Factor Shape Guidance

`factor_shape` 位于研究假设和可执行代码之间。它应让用户看懂因子的具体形态，并让后续实现者无需重新猜测公式结构；但它不是唯一公式模板，也不代表因子已经通过实证验证。

## 必填结构

```yaml
factor_shape:
  formula_family: path_interaction
  shape_type: interaction
  primary_signal: downside_shock
  auxiliary_signal: volume_decay
  composition: primary * confirmation
  pseudo_formula: zscore(downside_return_3d) * sigmoid(volume_decay_3d)
  windows:
    shock: 3
    baseline: 20
  normalization: rolling_robust_zscore
  direction: 数值越高表示卖压衰减后的修复条件越强
  implementation_steps:
    - 计算历史 3 日下行收益冲击
    - 计算成交量相对 20 日基线的异常程度
    - 计算冲击后成交量衰减
    - 对两个分量做历史滚动稳健归一化
    - 用确认算子组合主信号和衰减分量
```

## 字段约束

- `formula_family`：描述计算骨架，不描述研究主题。可使用 `level`、`difference`、`ratio`、`path_decay`、`persistence`、`concentration`、`asymmetry`、`interaction`、`gate`、`contrast`、`reliability_weighted` 或更准确的简短名称。
- `shape_type`：使用 `single_signal`、`interaction`、`gated_signal`、`contrast`、`state_score` 或 `reliability_weighted`。
- `primary_signal`：承担核心经济方向的信号。
- `auxiliary_signal`：没有辅助信号时填 `null`；有辅助信号时说明其确认、门控、调节或稳定作用。
- `composition`：用简短关系描述分量如何组合，与 `composition_operator` 保持一致。
- `pseudo_formula`：写到可以直接据此实现，但不要假装是已经验证的最终公式。
- `windows`：给出首轮建议窗口及语义。窗口只是待验证参数，不得用换窗口制造新候选。
- `normalization`：说明尺度处理、极值控制和分母保护方式。
- `direction`：说明数值增大代表什么，不承诺未来收益方向。
- `implementation_steps`：不超过 5 步；每一步都应能从允许字段和历史数据完成。

## 从 Lens 到 Factor Shape

1. 先从 `primary` Lens 提取一个核心可观察量。
2. 若存在第二个 Lens，只提取一个与其角色一致的辅助量。
3. 根据 `composition_operator` 选择计算关系，不要无解释地相加或相乘。
4. 选择最少的窗口和变换，使假设能够被实现和检验。
5. 写清方向和失效条件，再判断是否需要转成代码。

## 反同质化规则

反同质化只负责识别伪创新和重复候选，不强制本轮平均覆盖各 Layer、Agent 或公式家族。

每个候选都要记录：

```yaml
similarity_tags:
  - downside_shock
  - volume_decay
  - path_dependent
anti_homogeneity_check:
  mechanism_signature: downside_shock|volume_decay|reversal_condition
  only_parameter_variant: false
  same_formula_new_labels: false
  nearest_candidate: null
  distinction: 以冲击后的量能衰减路径为核心，不是普通负收益反转
```

按以下顺序检查：

1. **机制重复**：若研究对象、因果叙事和预期场景相同，则优先视为同一想法。
2. **公式重复**：若公式树相同，仅变量别名、正负号或表述不同，不得作为新想法。
3. **参数重复**：若只改变窗口、平滑参数、阈值或归一化方式，标记 `only_parameter_variant: true` 并合并。
4. **组合重复**：若第二个 Lens 没有改变方向、状态、可靠性或失效条件，则删除第二个 Lens。
5. **实质差异**：保留候选时，`distinction` 必须说明它与最相近候选在机制或计算路径上的真实差异。

允许同一批次出现相同 `formula_family`，前提是机制签名和计算路径确实不同。不要为了“看起来多样”强行选择不合适的 Layer。

