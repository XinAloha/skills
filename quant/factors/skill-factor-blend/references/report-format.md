# 因子组合报告输出格式

输出给用户时，必须展示“为什么选这些因子、为什么给这些权重、组合后是否更好”。不要只给复合因子 score。

## 标准格式

```
=== Factor Combine Report ===
Composite   : alpha_combo_v3
Horizon     : 5d
Label       : market_neutral
Period      : 2021-12-04 → 2024-12-03 (val, 3.0y)
Method      : score-weighted after redundancy filter

Selected factors:
  f_amihud_20          weight=0.28  score=+0.412  rank_ic_ir=2.10  turn=33.5
  f_momentum_60        weight=0.24  score=+0.356  rank_ic_ir=1.84  turn=18.2
  f_value_ep           weight=0.19  score=+0.281  rank_ic_ir=1.21  turn=7.4
  f_residual_quality   weight=0.17  score=+0.247  rank_ic_ir=1.06  turn=12.8
  f_low_vol_reversal   weight=0.12  score=+0.181  rank_ic_ir=0.88  turn=21.1

Rejected / merged:
  f_size_momentum      corr(f_momentum_60)=0.82, lower score
  f_amihud_10          top-bucket overlap with f_amihud_20=76%

Correlation diagnostics:
  max pairwise rank corr     : 0.54
  mean pairwise rank corr    : 0.21
  max top-bucket overlap     : 48%
  largest weight             : 0.28

Composite evaluation:
                    best single    composite     delta
  score             +0.412         +0.538        +0.126
  rank IC mean      +0.038         +0.046        +0.008
  rank IC IR        +2.10          +2.64         +0.54
  Sharpe            +0.85          +1.08         +0.23
  max drawdown      -22.3%         -18.9%        +3.4pp
  ann turnover      33.5           29.6          -3.9

Stability:
  yearly IC positive years : 3 / 3
  leave-one-out worst delta: -0.061 score
  verdict                  : ACCEPT COMPOSITE
```

## 必含元素

1. **元信息**：Composite / Horizon / Label / Period / Method
2. **入选因子表**：weight + 单因子 score + 关键指标
3. **拒绝或合并原因**：高相关、重叠、低质量、成本过高
4. **相关性诊断**：max corr、mean corr、top overlap、最大权重
5. **复合因子评价**：与最佳单因子并排对比
6. **稳定性检查**：年度表现、leave-one-out、结论

## Verdict 规则

| Verdict | 条件 |
|---|---|
| ACCEPT COMPOSITE | 相比最佳单因子提升明显，相关性可控，稳定性通过 |
| NEEDS REVIEW | 分数提升小，或依赖单个因子，或 turnover 上升明显 |
| REJECT | 组合不如最佳单因子，或高相关堆叠，或表现来自 test 污染 |

## 不要做的事

- 只输出一组权重
- 只比较 composite 与平均单因子，不比较最佳单因子
- 不说明被剔除因子
- 不展示相关性矩阵摘要
- 用复杂优化器但不说明约束和样本段
