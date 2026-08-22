# 复盘报告标准模板

```markdown
# Factor Library Review — YYYY-MM-DD

## Layer 1: 量化盘点

- 总实验 N（ACCEPTED N_acc / REJECTED N_rej / CRASHED N_crash）
- 接受率 X%；CRASH 率 Y%
- 分数 +A.AA → +B.BB（K 次大跳跃 + M 次微调）
- 提分动力学：早期 +X.XXX/轮 → 当前 +Y.YYY/轮
- 关键事件（5 次大跳跃）：
  - Iter 04  +amihud (流动性切入)         +0.18 → +0.13
  - Iter 17  HORIZON 5→20 (周期适配)     +0.42 → +0.11
  - ...

## Layer 2: 结构分析

### 2.1 当前 FACTORS（K 个）

| 因子 | 族 |
|---|---|
| size_inv | 流动性 |
| neg_max_ret_120 | lottery |
| neg_vol_cv_120 | 量能分布 |

族覆盖：3 / 8（缺反转、波动、量价相关、估值、盈利、行业）

### 2.2 相关性矩阵

|              | size  | max120 | vol_cv |
|---|---|---|---|
| size         | 1.00  | 0.42   | 0.31   |
| max120       | 0.42  | 1.00   | 0.55   ← 警告 |
| vol_cv       | 0.31  | 0.55   | 1.00   |

平均 \|ρ\| = 0.43（中等同质化，仍可接受）

### 2.3 最优路径

突破基本来自换族 / 换 horizon，不来自微调：
- Iter 04, 17, 28, 44 = 4 次大跳跃（占总提升 92%）
- Iter 05-08, 18-21 等 30+ 轮微调仅占 8%

## Layer 3: 研究建议

### [H1] add_factor: 填反转族（最高优先级）
- 理由：Layer 2.1 显示反转/动量族 = 0
- 实施：加 f_reversal_5
- 预期：+0.03 ~ +0.07

### [H2] horizon: 试 H=10
- 理由：当前 H=20，换手 33；IC decay 显示 H=10 IC_IR 几乎不降
- 实施：HORIZON 20 → 10
- 预期：+0.03 ~ +0.06（提升来自换手压低）

### [H3] combine_method: Ridge 替换 IC_IR
- 理由：Layer 2.2 显示因子间 |ρ| > 0.4，Ridge 处理共线性
- 实施：sklearn.linear_model.Ridge(alpha=10)
- 预期：±0.05（高方差）

### [H4] label_kind: market_neutral → vol_adjusted（最后试）
- 理由：lottery 因子在小票上强，可能让 MDD 偏深
- 实施：LABEL_KIND = "vol_adjusted"
- 预期：-0.03 ~ +0.03（高方差，仅在 H1~H3 跑完后试）

优先级：H1 > H2 > H3 > H4

## 风险预警

- 因子库偏 "lottery + 流动性"，市场风格切换时可能整体崩
- 接受率仍健康（~30%），但提分动力学已减缓到 +0.002/轮
- 平均 |ρ| = 0.43 中等，再加同族因子可能触发门控
- 当前 score +0.63，距离主分公式上限（~+1.5）还有空间，无需立即 phase transition
```

## 输出长度

- 完整报告 ~50 ~ 80 行
- Layer 1 ~10 行（含数据 + 关键事件）
- Layer 2 ~20 行（三个子章节）
- Layer 3 ~20 行（4 个假设 + 风险预警）
- 不超过 100 行 —— 太长就把细节移到附图（score_trajectory.png / corr_heatmap.png）

## 必含元素 checklist

- [ ] 元信息（日期、项目）
- [ ] Layer 1：接受率、CRASH 率、分数轨迹、提分动力学
- [ ] Layer 2.1：因子族分布
- [ ] Layer 2.2：相关性矩阵 + 平均 |ρ|
- [ ] Layer 2.3：最优路径关键事件
- [ ] Layer 3：3~5 个假设，每个含 op_type + 理由 + 实施 + 预期
- [ ] Layer 3 优先级排序
- [ ] 风险预警 ≥ 3 条
