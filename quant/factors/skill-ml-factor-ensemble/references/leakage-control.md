# Leakage Control

本 skill 的全部价值在于「防泄漏」。本文档定义滚动 walk-forward、purge、embargo 的口径，
供 Agent 在生成/修改 `scripts/ml_ensemble.py` 时严格对齐。参考 López de Prado,
*Advances in Financial Machine Learning*, 第 7 章。

## 为什么会泄漏

标签是「未来 H 日收益」。同一个训练样本的标签窗口 `[d, d+H]` 若与测试块时间重叠，
模型就「见过」测试期的未来信息 —— 朴素 K-fold / 随机划分在金融面板上会严重高估表现。

## 三道防线

1. **Rolling walk-forward（滚动前推）**
   - 只用 `[t−train_window, t]` 训练，只预测 `(t, t+step]`，然后整体右移。
   - 永远「过去训练、未来预测」，杜绝时间倒流。

2. **Purging（净化）**
   - 训练集中删除「标签窗口会触达测试块」的样本。
   - 实现近似：丢弃测试块前最后 `H` 个交易日的训练样本（`train_end = start − H`）。
   - **H 必须等于真实标签前瞻期**，否则净化不彻底，泄漏复现。

3. **Embargo（禁运缓冲）**
   - 在每个测试块之后再隔离 `embargo` 个交易日，避免序列自相关把测试信息渗回下一轮训练尾部。

## Fold 布局示意

```
udates: ......[----- train_window -----]  (purge H)  [-- test step --] (embargo) ......
                                         ^drop last H        ^OOS only
```

## 评估口径

- 只用 **OOS 预测** 计算横截面 Rank IC → ICIR（年化 = mean/std·√252）。
- 必须对比 **等权基线**：逐日对各因子 zscore 后取均值，不做任何学习。
  ML 合成若打不过等权基线，说明没有学到额外信息，应回退线性模型或减少因子。

## 常见泄漏陷阱（务必自查）

- 用 `close.pct_change(H)` 当标签（向后看，方向反）。正确：T+1 开盘 → T+1+H 开盘。
- 全样本做特征标准化 / 缺失填充（用到了未来统计量）。应在每个训练窗内 fit、对测试窗 transform。
- 因子选择 / 超参在全样本上调（多重检验泄漏）。选择也要纳入 walk-forward。
- 复权因子、ST 状态、停牌用了「最新」快照而非当时点快照（point-in-time 问题）。

> OOS ≠ 实盘。即使无泄漏，幸存者偏差、样本空间漂移、因子多重检验仍会高估实盘表现，
> ICIR 应视为上界，不构成投资建议。
