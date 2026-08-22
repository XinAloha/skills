# Layer 3：研究建议

复盘的第三层 —— **核心产出**。基于 Layer 2 的发现，给 3 ~ 5 个具体的下一步假设。

## 每个假设必含三要素

```
[H1] op_type: <add_factor / combine_method / horizon / label_kind / preprocess / ...>
  理由：基于 Layer 2 的具体发现（不是凭直觉）
  实施：具体改动一句话
  预期 score：从 X.XX → Y.YY ~ Z.ZZ
```

## 完整模板

```
=== Next Hypotheses ===

[H1] add_factor: 反转族空缺
  当前 FACTORS 中反转/动量族 = 0 个，是覆盖盲区。
  建议：加 f_reversal_5（5 日短期反转，A 股小盘股反转效应显著）。
  与现有因子相关性预期：与 size_inv ρ ≈ 0.3，与 max_120 ρ ≈ 0.4，可加。
  预期 score : +0.63 → +0.66 ~ +0.70

[H2] combine_method: Ridge 替换 IC_IR 加权
  当前 IC_IR 加权（lambda=0.3）权重已较均衡，但 Ridge 可在 train 段
  自动处理因子共线性。
  实施：sklearn.linear_model.Ridge(alpha=10) on train fwd_ret.
  预期 score : +0.63 → +0.65 ~ +0.72（也可能 -0.05 ~ +0.00）

[H3] horizon: 试 H=10
  当前 best 在 H=20，但 IC decay 曲线显示 H=10 IC_IR 几乎与 H=20 持平
  且换手降低 50%。
  预期 score : +0.63 → +0.66 ~ +0.69（提升来自换手压低）

[H4] phase transition 候选: market_neutral → vol_adjusted
  整体 lottery 类因子在小票上极强，可能让 MDD 偏深。
  vol_adjusted 标签会惩罚高波股，可能改善 MDD 同时小幅压低 IC。
  预期 score : +0.63 → +0.60 ~ +0.66 (高方差实验，仅在 H1-H3 全跑完后试)
```

## 优先级排序原则

按以下顺序排：

1. **填空缺**（add_factor 进缺失的族）—— 高确定性提分
2. **小调参**（horizon、preprocess）—— 中确定性
3. **结构改动**（combine_method）—— 中等方差
4. **高方差实验**（label_kind 切换）—— 留到最后

例：H1 > H3 > H2 > H4

## 风险预警（必有）

每份报告必须含一个"风险预警"区块：

```
=== 风险预警 ===
- 因子库偏 "lottery + 流动性"，市场风格切换时可能整体崩
- 67 轮已经接近"无脑挖"的边际，建议进入 Phase 2 或换更复杂模型
- 平均相关性 0.43 已偏中等，再加同族因子可能触发门控
```

## 何时建议 phase transition

如果 Layer 1 / Layer 2 满足以下任一：

| 信号 | 建议 |
|---|---|
| 提分动力学持续 < +0.005/轮 超过 30 轮 | 换组合方法 / 换标签 |
| 平均 \|ρ\| > 0.50 | 删同质，不要继续加 |
| CRASH 率 > 15% | 看哪个禁区触得多，可能要重读 program.md |
| 因子族覆盖 ≤ 2 | 必须换族 |
| 当前 score 接近主分公式上限（如 +1.5+） | 进 Phase 2（基本面）/ 换更复杂模型 |

## 反模式

| 反模式 | 修复 |
|---|---|
| "再加 5 个新因子" | 给 op_type + 具体函数名 |
| "继续微调" | Layer 1 显示已平台期 → 该换族 / phase transition |
| "试试 LSTM" | 违反 pooled cross-section 范式，列入禁区 |
| 优先级倒置（先做高方差实验） | 先做高确定性的填空缺，再做高方差 |
| 没说预期 score 区间 | 必须给具体数字 |
| 建议和 Layer 2 数据脱钩 | 每个建议必须引用 Layer 2 的发现 |
