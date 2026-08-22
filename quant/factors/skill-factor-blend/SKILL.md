---
name: factor-blend
description: Use when an agent needs to blend multiple evaluated quantitative factor
  signals into a single composite alpha signal (signal-level merge, not portfolio-level
  combination). Covers factor selection, redundancy removal, weighting, and composite
  evaluation.
quantSkills:
  project_type: skill
  category: factor
  tags:
  - factor-blending
  - signal-merge
  - composite-alpha
  - factor-weighting
  - correlation-control
  - equal-weight
  - icir-weight
  - score-weight
  - z-score-synthesis
  - pandadata
  platforms:
  - claude-code
  - codex
  - openclaw
  - cursor
  status: stable
  validation_level: production
  maintainer_type: community
  summary_zh: 多因子信号层合并：去冗余（相关矩阵 + Top-bucket overlap）→ 等权/ICIR/Score 三种加权方案 → 逐日截面 z-score 合成 → 重新评价复合因子。信号层操作（产出 composite_signal），非组合层资金分配。
  summary_en: "Multi-factor signal-level blending: redundancy removal via correlation matrix and top-bucket overlap, three weighting schemes (equal/ICIR/score), daily cross-sectional z-score synthesis, and composite re-evaluation. Signal-level only — outputs composite_signal, not portfolio weights."
  license: GPL-3.0
  repository: https://github.com/quantskills/skill-factor-blend
---

```json qsh-form
{
  "version": 1,
  "task": {
    "placeholder": "说明待合并的因子及其评估报告，或上传因子矩阵和 ScoreReport",
    "required": true
  },
  "fields": [
    {
      "key": "universe",
      "label": "股票池",
      "type": "select",
      "default": "000300.SH",
      "options": [
        { "value": "000300.SH", "label": "沪深300" },
        { "value": "000905.SH", "label": "中证500" },
        { "value": "399006.SZ", "label": "创业板指" },
        { "value": "000852.SH", "label": "中证1000" }
      ]
    },
    {
      "key": "horizon",
      "label": "预测周期",
      "type": "select",
      "default": "5",
      "options": [
        { "value": "1", "label": "未来 1 日" },
        { "value": "5", "label": "未来 5 日" },
        { "value": "10", "label": "未来 10 日" }
      ]
    },
    {
      "key": "weighting",
      "label": "加权方式",
      "type": "select",
      "default": "equal",
      "options": [
        { "value": "equal", "label": "等权" },
        { "value": "icir", "label": "ICIR 加权" },
        { "value": "score", "label": "综合评分加权" }
      ]
    }
  ],
  "prompt_template": "{{#task}}任务与材料：\n{{task}}\n\n{{/task}}{{#attachments}}用户上传的材料（已放入工作区）：\n{{attachments}}\n\n{{/attachments}}在 {{universe}}、未来 {{horizon}} 日的统一口径下合并多个已评估因子，先按相关性和 Top-bucket overlap 去冗余，再采用 {{weighting}} 生成逐日截面 z-score 复合信号；不得把信号合并误作组合资金配置，并重新评估复合因子的贡献、稳定性、换手与风险，输出中文报告。"
}
```

# 多因子合并 (Factor Signal Blending)

> 给定多个候选因子 `[date × symbol × factor]` 和各自评价报告，将多个因子信号**合并**为一个**可评价、可解释、可复现**的复合 Alpha 信号。
>
> ⚠️ **这是信号层合并，不是组合层操作**：产出是 `composite_signal[date × symbol]`（截面 z-score），不涉及资金分配、仓位优化或组合权重。如需从信号生成持仓，请另行处理。

## 核心规则

1. **只合并已评价因子**：每个输入因子必须有 `factor-evaluate` 报告或项目内等价 `ScoreReport`。
2. **先去冗余，再给权重**：相关性过高的因子不能靠优化器”自动解决”。
3. **权重来自 train / val，不看 test**：test 段严格不可见，不能用来挑因子或调权重。
4. **同口径才可合并**：horizon、label kind、universe、mask、截面标准化口径必须一致。
5. **复合因子必须重新评价**：合并完成后把 composite signal 当作新因子跑完整评价。
6. **合并不是刷分器**：报告必须展示单因子贡献、相关性、换手变化和合并稳定性。

## 工作流（标准 8 步）

```
1. 校验输入因子契约：shape、horizon、label、universe、z-score、coverage
2. 读取每个因子的 ScoreReport：score、rank_ic_ir、Sharpe、MDD、turnover、monotonicity
3. 过滤不可用因子：score <= 0、IC 不稳、MDD 过深、turnover 过高、coverage 过低
4. 计算因子间相关矩阵：rank corr / residual corr / top-bucket overlap
5. 去冗余：同簇只保留质量最高或先做 factor-orthogonalize
6. 选择权重方案：equal / score-weighted / IR-weighted / constrained optimizer
7. 生成 composite_signal = Σ weight_i * factor_i，并逐日 z-score
8. 调 factor-evaluate 重新评价 composite_signal，输出合并报告
```

## 权重方案选择

> ⚠️ **Agent 执行时必须反问用户选择权重方案**，不能自行决定。若用户未明确指定，默认用 equal 作为基准并告知用户。

| 场景 | 推荐方案 |
|---|---|
| 因子数量少，质量接近 | Equal weight |
| 评价报告质量差异明显 | Score-weighted |
| IC 稳定性是主目标 | IR-weighted |
| 因子多且相关性复杂 | Constrained optimizer |
| 样本短、噪声大 | Equal 或 shrinked score-weighted |

默认推荐：**先做去冗余，再用 score-weighted；如果样本少于 2 年，用 equal weight 作为基准**。

**交互式询问流程**：
```
1. Agent 展示可用权重方案及适用场景
2. Agent 列出各因子的 ICIR/Score 速览
3. Agent 反问："请选择权重方案: equal / icir / score？"
4. 用户确认后，Agent 按选定方案执行合成
```

CLI 调用时可通过 `--weight` 跳过交互：
```bash
python scripts/blend.py --weight icir    # 直接指定
python scripts/blend.py                   # 交互式询问
```

## 与多因子组合的区别

| | 多因子合并（本 skill） | 多因子组合 (Portfolio Combination) |
|---|---|---|
| **操作层** | 信号层 (signal-level) | 组合层 (portfolio-level) |
| **输入** | 多个因子 z-score | 多个策略的收益或权重 |
| **产出** | `composite_signal[date × symbol]` | 持仓向量或净值曲线 |
| **核心问题** | 去冗余 → 加权 → 合成一个信号 | 风险预算 → 优化器 → 分配资金 |
| **后续步骤** | 信号 → 选股 → 组合构建 | 已是最终持仓 |

## 接口映射

| 本 skill 概念 | 你的项目对应 |
|---|---|
| 输入因子库 | `[date × symbol × factor]` 或多个 `[date × symbol]` DataFrame |
| 单因子评价 | `factor-evaluate` 的 `ScoreReport` |
| 权重 | `factor_name → weight` |
| 复合因子 | `composite_signal[date × symbol]` |
| 最终评价 | 调 `factor-evaluate` 或项目内 `primary_score()` |

## 按需加载

| 何时读 | 文件 |
|---|---|
| 想看权重算法 | `references/weighting.md` |
| 输出报告格式 | `references/report-format.md` |
| 常见误区与危险信号 | `references/anti-patterns.md` |

## 项目实现

- **`scripts/blend.py`**：独立可运行的合并脚本
  ```bash
  # 交互式选择权重（推荐）
  python scripts/blend.py --factor-dir data/factors_orthogonalized

  # 直接指定权重方案
  python scripts/blend.py --factor-dir data/factors --weight icir
  python scripts/blend.py --factor-dir data/factors --weight equal
  python scripts/blend.py --factor-dir data/factors --weight score

  # 调整去冗余阈值
  python scripts/blend.py --corr-threshold 0.6
  ```
  输入：`data/factors/F*.parquet`（或正交化后）
  输出：
  - `data/composite_{scheme}-weighted.parquet` — 合成因子
  - `data/combine_state.pkl` — 完整中间态（权重/ICIR/去冗余记录）
  - `data/combine_report.json` — 诊断报告

**权重计算逻辑**：
- **equal**：所有去冗余后因子权重 = 1/n
- **icir**：权重 ∝ max(0.01, ICIR)，确保负 ICIR 因子不被完全排除但有惩罚
- **score**：权重 ∝ ICIR × √coverage / (1 + turnover)，综合平衡预测力、覆盖率、交易成本

## 管线连接

```
data/factors/F*.parquet（或 factors_orthogonalized/）
  → skill-factor-evaluate（单因子评价）
  → 去冗余（corr > 0.7 同簇去重）
  → skill-factor-blend（等权/ICIR/Score 加权合成）
  → data/composite_*.parquet
  → skill-factor-evaluate（复合因子重新评价）
  → skill-factor-decay（复合因子衰减分析）
```

## QA 检查清单

- [ ] 所有输入因子的 horizon / label / universe 一致？
- [ ] 每个输入因子都有独立评价报告？
- [ ] 已计算因子间相关性和 top-bucket overlap？
- [ ] 高相关因子已经去冗余或正交化？
- [ ] 权重没有使用 test 段信息？
- [ ] 复合因子已重新 z-score 并重新评价？
- [ ] 报告展示了单因子贡献，不只是 composite score？
- [ ] 确认本 skill 做的是信号层合并（产出 signal），而非组合层资金分配？

## 跨工具适配

- Cursor → `agents/cursor-rule.mdc`
- 无原生 skill 机制 → `agents/portable-loader.md`

---

## 项目边界（量化研究合规声明）

> 按 QUANTSKILLS 社区规则 §8 声明。

- **数据来源**：本 skill 不附带任何市场数据、因子数据或评价结果；使用者需自行准备合法数据和 ScoreReport。
- **假设与参数**：默认合并对象是同 horizon、同 universe 的截面因子信号；默认权重在 train / val 上确定，test 严格不可见。
- **已知限制**：复合信号容易过拟合；合并表现依赖样本期、交易成本、股票池和单因子质量，不能保证未来有效。
- **风险边界**：合并权重、回测净值和综合评分仅反映历史数据 + 假设条件下的统计表现，不代表未来表现。合并结果仅为信号（截面 z-score），不构成持仓建议。
- **用途定位**：仅供量化研究、教育与方法论参考。不构成任何形式的投资建议、交易信号或获利保证。
