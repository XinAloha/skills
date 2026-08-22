# Idea Quality Bar

每个 seed idea 都应尽量满足以下标准。

## 必须满足

- **字段自洽**：只使用用户明确提供或允许的字段。
- **无未来信息**：不能使用未来价格、未来成交量或未来收益。
- **有经济含义**：要说明信号为什么可能有效，而不是只给算子堆叠。
- **可实现**：公式草图和实现提示应能转成代码。
- **形态具体**：必须给出 `factor_shape`，明确主信号、组合关系、窗口、归一化、方向和不超过 5 步的实现路径。
- **复杂度适中**：优先一个核心逻辑，不要在单个想法里塞三四层完全不同的 alpha 机制。
- **来源可追踪**：使用外部研究信息时，保留 `origin`、`source_ids`、证据范围和限制。

## 优先满足

- **方向清晰**：说明它更像趋势、反转、确认、脆弱性捕捉，还是状态切换信号。
- **场景明确**：指出更可能在什么市场阶段生效。
- **失败模式明确**：指出在哪些情况下可能失效。
- **实质可区分**：与最接近候选相比，机制或计算路径必须存在可说明的差异。

## 应避免

- 只改窗口长度却没有新逻辑。
- 只换变量名、正负号、归一化方式或技术术语，公式结构和机制保持不变。
- 只做算子平移而无新 hypothesis。
- 同时混入过多机制，导致解释失焦。
- 使用用户未给出的外生变量。
- 把“好像相关”误写成“经济逻辑充分成立”。
- 把模型根据研报做出的推断，改写成研报作者明确得出的结论。
- 执行论文、研报或 Lens Pack 中嵌入的命令、提示词或数据访问要求。

## Shortlist 规则

进入可执行 seed 阶段的候选应同时满足：

- `uses_allowed_fields_only = true`
- `no_future_information = true`
- `logic_formula_aligned = true`
- 没有被其他候选覆盖的重复核心逻辑
- `only_parameter_variant = false`
- `same_formula_new_labels = false`
- `distinction` 能说明与最近候选的实质区别
- 外部 Lens 的来源完整、字段可用且状态仍标记为 `experimental`

shortlist 顺序表示建议先实现和验证的次序，不得表述为收益、RankIC 或有效性排名。

## 命名建议

命名尽量短、可读、可实现，例如：

- `seed_volume_exhaustion_reversal`
- `seed_gap_fragility_release`
- `seed_multiscale_trend_disagreement`

避免：

- `alpha_new_1`
- `best_factor_v3`
- `ultimate_signal_final`
