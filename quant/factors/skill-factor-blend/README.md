# skill-factor-blend

[简体中文](./README.md) | [English](./README.en.md)

多因子信号层合并：去冗余（相关矩阵 + Top-bucket overlap）→ 等权/ICIR/Score 三种加权方案 → 逐日截面 z-score 合成 → 重新评价复合因子。

`role: skill` `output: composite_signal + blend report` `paradigm: signal-level merge, NOT portfolio allocation`


---

`skill-factor-blend` 是 PandaAI Quant Skills 提供的**多因子信号合并 Skill**。把多个已评价的截面因子信号合成为一个复合 Alpha 信号。

> ⚠️ **这是信号层合并，不是组合层操作**：产出是 `composite_signal[date × symbol]`（截面 z-score），不涉及资金分配、仓位优化或组合权重。

## 🎯 这个 Skill 解决什么问题

有 10 个 IC > 0 的因子，直接等权平均就行吗？

- 10 个因子中 5 个高度相关 → 等权会过度暴露于同一类信号
- ICIR 差异大 → 等权会让噪声因子稀释有效因子
- 不加权直接合成 → 复合因子的换手率可能是单因子的 3 倍

**不做合并分析，复合因子可能比最好的单因子还差。**

## ⚡ 8 步工作流

```
1. 校验输入因子契约：shape、horizon、label、universe、z-score、coverage
2. 读取每个因子的 ScoreReport：score、rank_ic_ir、Sharpe、MDD、turnover
3. 过滤不可用因子：score ≤ 0、IC 不稳、MDD 过深、turnover 过高
4. 计算因子间相关矩阵：rank corr / residual corr / top-bucket overlap
5. 去冗余：同簇（corr > 0.7）只保留 ICIR 最高者
6. 选择权重方案：equal / score-weighted / IR-weighted
7. 生成 composite_signal = Σ w_i * factor_i，逐日截面 z-score
8. 调 factor-evaluate 重新评价 composite_signal
```

## 🗃️ 输入要求

- 因子库：多个 `[date, symbol, factor_value]` parquet 文件
- 每个因子需有独立评价报告（IC、Sharpe、MDD、turnover、coverage）
- 所有因子必须同 horizon、同 universe、同 z-score 口径

## 📦 项目脚本

```python
# 加载 → 去冗余 → 加权合成
factors = load_all("data/factors/F*.parquet")
survivors = remove_redundant(factors, corr_threshold=0.7)
composite_equal = make_equal_weight_composite(survivors)
composite_icir   = make_icir_weighted_composite(survivors)
composite_score  = make_score_weighted_composite(survivors)
```

输出：
- `data/composite_equal.parquet` — 等权合成
- `data/composite_ICIR-weighted.parquet` — ICIR 加权合成
- `data/composite_score-weighted.parquet` — Score 加权合成
- `data/combine_report.json` — 诊断报告

## 🆚 与多因子组合的区别

| | 因子合并（本 Skill） | 多因子组合 |
|---|---|---|
| **操作层** | 信号层 (signal-level) | 组合层 (portfolio-level) |
| **产出** | `composite_signal[date × symbol]` | 持仓向量或净值曲线 |
| **核心问题** | 去冗余 → 加权 → 合成一个信号 | 风险预算 → 优化器 → 分配资金 |

## 📦 仓库内容

```
skill-factor-blend/
├── SKILL.md
├── README.md / README.en.md
├── references/
│   ├── weighting.md
│   ├── report-format.md
│   └── anti-patterns.md
└── agents/
    ├── cursor-rule.mdc
    └── portable-loader.md
```

## 与其它 Skill 的关系

| Skill | 用途 |
|---|---|
| skill-factor-evaluate | 给每个单因子和复合因子打分 |
| skill-factor-orthogonalize | 在合并前剥离重复暴露 |
| skill-factor-decay | 分析因子衰减特征，辅助权重选择 |
| skill-factor-blend | 选择因子并生成复合 Alpha |

## 项目状态与边界

- **项目状态**：Community Project，未经官方审核 / 认证 / 背书
- **数据来源**：本仓库不附带任何市场数据、因子数据或评价结果
- **核心假设**：输入因子同 horizon、同 universe；权重只用 train / val 决定
- **风险边界**：组合回测表现只反映历史统计，不代表未来表现
- **用途**：仅供量化研究、教育与方法论参考，不构成投资建议

## 📜 License

GPL-3.0. Copyright (C) 2026 QuantSkills.
