# Composition Operators

当一个候选使用两个 Prompt Lens 时，先选择一个 `primary` Lens 作为主机制，再选择一个辅助 Lens。辅助 Lens 只能改变强度、可信度、适用状态或对照关系，不应吞掉主机制。

组合语法用于研究设计和公式草图，不是固定公式模板。生成想法时可以写出近似形式，但应允许模型在同一机制下探索不同实现。

## Operator Types

### modifier

用途：辅助机制连续调节主信号强度，但不改变主信号方向。

草图：

```text
F = P * (1 + lambda * M)
F = P * sigmoid(M)
```

适合：能量强弱、流动性强弱、路径噪声、波动尺度等作为主信号的强度权重。

### confirmation

用途：辅助机制确认主信号是否更可信，一致时增强，不一致时削弱。

草图：

```text
F = P * C
where C is a continuous confidence score in [0, 1]
```

适合：相位偏离由能量变化确认、轨迹弯折由压缩释放确认、形态信号由成交量确认。

### gate

用途：只在某类连续状态下激活或弱化主信号。优先使用软门控，避免二值开关过硬。

草图：

```text
F = P * g(S)
```

适合：趋势因子只在低噪声状态启用，反转因子只在极端冲击后启用。

### stabilizer

用途：用稳定性或不稳定性调整主信号可靠性。

草图：

```text
F = P / (1 + Instability)
F = P * Reliability
```

适合：信号持久性、跨窗口一致性、近期失效率等。

### contrast

用途：表达两个机制之间的张力或分歧。

草图：

```text
F = P1 - P2
F = normalized(P1) - normalized(P2)
```

适合：趋势压力与反转压力冲突、短周期与长周期节奏分歧、价格方向与成交行为背离。

## Selection Rules

- 一个候选最多使用两个 Lens，除非用户明确要求复杂融合。
- 必须记录 `selected_lenses`，包括每个 Lens 的 `lens_id` 和 `role`。
- 必须记录 `composition_operator`。
- 如果只有一个 Lens，`composition_operator` 使用 `none`。
- 不要为了组合而组合；如果第二个 Lens 不能改变解释、适用状态或可靠性，就保持单 Lens。
- 不要把 operator 写成唯一公式。它只规定组合关系，不规定最终表达式。

## Two-Stage Workflow

### Stage 1: Lens Selection

只负责研究设计，不写代码。输出：

```yaml
selected_lenses:
  - lens_id: market_cycle.phase_divergence
    role: primary
  - lens_id: market_cycle.compression_expansion_turn
    role: confirmation
combination_type: single_tag_multi_lens
composition_operator: confirmation
hypothesis: >
  相位错位若同时发生于压缩向扩张转换阶段，更可能代表真实周期转折，
  而不是普通短期噪声。
```

### Stage 2: Factor Implementation

基于 Stage 1 的结构化研究方案，再选择公式、实现代码、处理数值稳定性、检查未来信息。不要让一个 prompt 同时承担 Lens 选择、研究假设、公式设计、代码实现和测试的全部压力。
