# Evolution Rules

当前 skill 的核心不是脚本内调 API，而是：

1. 脚本先分析输入因子
2. 当前使用 skill 的模型读取 prompt pack
3. 模型自己完成 mutation / crossover
4. 脚本再评估这些生成因子并输出推荐

所以这里真正的“进化”是 **LLM reasoning step + deterministic evaluation step** 的组合。

## 总体原则

1. 当前只跑 **一轮**，不自动 loop。
2. 所有输入因子先统一算 `RankIC`、`RankICIR`、`IC`、`ICIR` 和 `MI`。
3. `mutation` 默认对所有输入因子都做一次建议。
4. `crossover` 主要从 strong pool 出发，并给每个强因子配一个低相关伙伴。
5. 对所有生成因子按表现排序，最终推荐 top-k 给用户。
6. 用户若要继续迭代，直接把 `next_round_custom_seed_factors.json` 作为下一轮 custom seed 输入。

## 输入因子评估

先对所有输入因子统一计算：

- `IC`
- `RankIC`
- `ICIR`
- `RankICIR`
- `MI`

默认可以按绝对值看 `RankIC` / `RankICIR`，因为反向有效因子仍然有研究价值。

## Strong Pool

所有输入因子按表现排序后，取前 50% 左右作为 strong pool。

作用：

- strong pool 因子更适合作为 crossover 的主因子
- 剩余因子更多用于提供低相关多样性

## Mutation 规则

对每个输入因子生成 **一个** mutation 建议。

当前模型在读 prompt 时，应该遵守这些原则：

- 先读懂 parent factor 在经济学上想抓什么
- 保留 parent factor 的经济含义
- 保留 parent factor 的基本逻辑而不是完全换题
- 只改变一到两个结构性部件，例如窗口、标准化、非线性、平滑或 interaction
- 不允许使用 `target_return`
- 不允许引入未来信息

## Crossover 规则

### 配对方式

从 strong pool 中取主因子，再从全体输入因子中寻找**绝对相关性较低**的伙伴因子。

这样做的目标是：

- 保留强因子的核心逻辑
- 让模型分析 partner 在哪里能形成互补
- 用低相关结构增加多样性

### 生成数量

当前默认每对 crossover pair 生成 **两个**建议因子。

### 当前模型应遵守的原则

- 以表现更好的主因子为核心
- 显式分析 partner 在哪些逻辑上与主因子互补
- 借用互补部分，而不是创造完全无关的新因子
- 保持经济直觉
- 避免未来函数

## 排序与相关性输出

当前实现是：

1. **排序**
   - 先按 `RankIC`
   - 再按 `RankICIR`
   - 默认可以按绝对值看这两个指标

2. **相关性输出**
   - 输出每个候选与输入因子池的 `maxCorr`
   - 输出每个推荐因子与其余推荐因子的 `maxCorr`
   - 这些相关性只作为诊断信息，不参与推荐过滤

因此，推荐结果只由 `RankIC` 和 `RankICIR` 决定，`corr` 只作为可选参考输出。

## 推荐方向

如果某个生成因子：

- `RankICIR > 0`

则：

```text
recommended_sign = 1
```

如果：

- `RankICIR < 0`

则：

```text
recommended_sign = -1
```

表示它可能是反向有效因子，下一轮继续使用时应考虑符号翻转。

## 你真正要看的文件

脚本准备阶段最重要的是：

- `input/input_factor_metrics.csv`
- `input/input_factor_correlations.csv`
- `input/strong_pool.json`
- `input/crossover_pairs.json`
- `generation/prompts/*.prompt.txt`
- `generation/generated_candidates_template.json`

评估阶段最重要的是：

- `generation/generated_factor_metrics.csv`
- `generation/ranked_recommendations.csv`
- `final/recommended_factors.json`
- `final/next_round_custom_seed_factors.json`

## 当前实现没有做的事

下面这些仍然不在这个 MVP 里：

- 完整多轮 loop
- adaptive feedback
- fresh alpha injection
- quality checker graph
- prompt-based repair / self-critique 链
- 负样本池单独评分

如果后面要继续贴近 CogAlpha 论文，可以优先把：

- richer mutation prompt
- stronger crossover partner selection
- feedback summary
- multi-round orchestration

接回去。
