# 因子挖掘反模式

| 反模式 | 为什么错 | 修复 |
|---|---|---|
| 同时改 N 个东西 | 即使提分也无法归因，后续不可复用 | 拆成 N 次实验，每次一个 op_type |
| 在 train+val 全段拟合权重 | val 段已被训练污染，过拟合 | 仅在 train 段拟合，参数应用到 val |
| 单股序列建模（LSTM / RNN / 按 symbol 分组拟合） | 违反 pooled cross-section 范式 | 全样本混合训练，特征做截面 |
| "我先看一下 test 段表现" | 看一眼就污染了未见性 | 三段切分**严格不可见**，看了就废 |
| 给已有因子换皮再加（5 / 3 / 1 日反转都保留） | 同质化共线性，无新信息 | 见 `correlation-gate.md` |
| 50 行复杂特征工程换 0.005 IC | 复杂度成本高 / 可解释性差 / 易过拟合 | 简单可解释优先（5~20 行） |
| 没写 ITER_NOTE 就跑 | 没有假设就没有研究 | 见 `iter-note.md` |
| `hypothesis: "试试看"` | 不是假设，是赌博 | 写出经济 / 统计因果 |
| `expected: "提升"` | 无法事后判断"对了"还是"蒙对了" | 给具体分数区间 |
| 把整个 cache / journal / factor_library 读进来"参考" | 偷看历史 = 偷看未来 | 在 `metrics.py` 用 in-process 数据算 |
| 改了 `prepare.py` 的私有函数 | 评估宪法被绕过 | 申请新功能在 journal 留言，等人类评审 |
| 用 `close[T]` 当 T 日成交价 | 未来函数 —— T+1 才能成交 | 见 factor-debug skill 的 §6 |

## 危险信号清单（看到立刻警觉）

如果你的实验出现以下任一情况，**先停下来检查未来函数**：

- 信号校验通过但 IC > 0.15
- 回测年化 > 50%，最大回撤 < 5%
- Sharpe / IC_IR > 1.0
- train / val / test 三段 IC 量级一致且都 > 0.10

真实因子的 val IC 应该比 train IC 低 30~70%。

> 参考实现：`auto_research_alpha/program.md §2 (禁止清单)`，runner 的黑名单静态扫描会拦截一部分。
