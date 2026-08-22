---
name: skill-portfolio-optimize
description: >
  Turn an alpha signal into optimal portfolio weights under real constraints.
  Use when a user has factor scores / expected returns and wants portfolio
  weights, or asks about mean-variance / risk-parity / minimum-variance /
  maximum-diversification optimisation, sector-neutral or turnover-limited
  construction. Bridges factor signals and backtesting.
license: GPL-3.0
category: 工具
metadata:
  organization: QuantSkills
  organization_url: https://github.com/quantskills
  repository: skill-portfolio-optimize
  repository_url: https://github.com/quantskills/skill-portfolio-optimize
  project_type: skill
  collection: portfolio-risk-validation
---

```json qsh-form
{
  "version": 1,
  "task": {
    "placeholder": "说明或上传 alpha 信号、收益面板/协方差矩阵、现有权重、行业与暴露约束",
    "required": true
  },
  "fields": [
    {
      "key": "objective",
      "label": "优化目标",
      "type": "select",
      "default": "mean_variance",
      "options": [
        { "value": "mean_variance", "label": "均值-方差" },
        { "value": "min_variance", "label": "最小方差" },
        { "value": "max_sharpe", "label": "最大夏普" },
        { "value": "risk_parity", "label": "风险平价" },
        { "value": "max_diversification", "label": "最大分散化" }
      ]
    },
    {
      "key": "weight_cap",
      "label": "单资产权重上限",
      "type": "number",
      "placeholder": "例如 0.05",
      "help": "以小数表示，0.05 即 5%"
    },
    {
      "key": "turnover_limit",
      "label": "换手率上限",
      "type": "number",
      "placeholder": "例如 0.30",
      "help": "仅在提供上一期权重时生效"
    }
  ],
  "prompt_template": "{{#task}}任务与材料：\n{{task}}\n\n{{/task}}{{#attachments}}用户上传的材料（已放入工作区）：\n{{attachments}}\n\n{{/attachments}}把 alpha 信号转化为受约束的目标组合权重，优化目标采用 {{objective}}。{{#weight_cap}}单资产权重上限为 {{weight_cap}}。{{/weight_cap}}{{#turnover_limit}}换手率上限为 {{turnover_limit}}。{{/turnover_limit}}使用正定且稳健的协方差估计，检查行业/因子中性、暴露、换手等约束的可行性与绑定情况，输出权重、风险贡献和求解诊断，不将历史优化结果表述为投资建议，输出中文报告。"
}
```

# skill-portfolio-optimize

role: skill · output: target weights + optimisation diagnostics · paradigm: convex portfolio construction

把"多因子信号 + 风险约束"变成**最优权重**。这是站内因子流水线里缺失的一环：因子合成之后、回测之前。

## 🎯 这个 Skill 解决什么问题

生态把多个因子 `blend` 成一个信号后，回测只会"Top 10% 等权"。等权忽略了：风险集中、行业押注、换手成本、个股上限。本 Skill 用凸优化把 alpha 信号转成**可交易、受约束、风险可控**的权重。

支持五种目标函数 + 一组工程级约束：

| 目标 | 做什么 | 文献 |
|------|--------|------|
| `min_variance` | 最小化组合方差 | Markowitz 1952 |
| `mean_variance` | `max wᵀμ − λ/2·wᵀΣw` | Markowitz 1952 |
| `max_sharpe` | 最大化夏普 | — |
| `risk_parity` | 等风险贡献(ERC) | Maillard et al. 2010 |
| `max_diversification` | 最大分散化比率 | Choueifaty & Coignard 2008 |

**约束**：全额投资 / 多空、个股权重上限、**行业中性**、**因子暴露中性** `Xᵀw=0`、**换手率约束** `‖w−w_prev‖₁≤τ`。

## ⚡ 工作流（Agent 按此执行）

1. **拿信号与收益**：alpha 信号 `μ`（来自 `skill-factor-blend` 等）+ 收益面板（算协方差）。
2. **估协方差 Σ**：`scripts/covariance.py`，默认 **Ledoit-Wolf 收缩** + 特征值修正保证正定。（也可直接用 `skill-risk-model` 的结构化 Σ。）
3. **配约束**：`scripts/constraints.py`，按需开启个股上限 / 行业中性 / 暴露中性 / 换手约束。
4. **求解**：`scripts/optimizers.py`，scipy SLSQP（无需 cvxpy）。
5. **出报告**：`scripts/optimize_report.py` → 目标权重 + 诊断（实现暴露、风险贡献、换手、约束是否绑定）。
6. **画前沿（可选）**：`scripts/frontier.py` 扫风险厌恶画有效前沿。

```bash
python scripts/optimize_report.py --signal alpha.csv --returns returns.csv \
    --objective mean_variance --weight-cap 0.05 --out weights.csv
python examples/run_demo.py        # 离线 demo，五目标对比 + 行业中性
```

## 🗃️ 输入契约

| 输入 | 形态 | 必需 | 说明 |
|------|------|------|------|
| `cov` | `DataFrame [symbol×symbol]` | 是 | 协方差（由收益估或来自风险模型）|
| `mu` | `Series [symbol]` | mean_variance/max_sharpe 需要 | 预期收益 / alpha 信号 |
| `sectors` | `Series [symbol]` | 行业中性时 | 行业标签 |
| `exposures` | `DataFrame [symbol×factor]` | 暴露中性时 | 因子暴露矩阵 |
| `w_prev` / `turnover_limit` | `Series` / float | 换手约束时 | 上期权重与上限 |

输出：目标权重 `Series` + `diagnostics`（vol、holdings、sector/factor exposure、turnover、风险贡献…）。

## 🔗 管线定位

```
因子挖掘 → 评估 → 合成(skill-factor-blend) → [本 Skill：组合优化] → 回测(skill-backtest) → 过拟合检测(skill-backtest-overfit)
```

协方差可消费 `skill-risk-model` 的结构化 Σ；权重交给 `skill-backtest` 跑净值。

## 📦 仓库结构

```
skill-portfolio-optimize/
├── SKILL.md / README.md / requirements.txt / LICENSE
├── scripts/
│   ├── covariance.py        # Ledoit-Wolf 收缩 + PSD 修正
│   ├── optimizers.py        # 5 种目标(SLSQP) + 风险贡献
│   ├── constraints.py       # 约束构造(上限/行业/暴露/换手)
│   ├── frontier.py          # 有效前沿
│   ├── optimize_report.py   # 编排 → 权重 + 诊断 + CLI
│   └── data_source.py       # panda_data 适配层(离线自动回退)
├── references/methodology.md
└── examples/run_demo.py
```

## ⚠️ 使用规则

- **Σ 必须正定**：用 Ledoit-Wolf 而非裸样本协方差，尤其当标的数接近样本天数。
- 行业/暴露中性是等式约束；若与个股上限冲突会无解，需放宽。**不要叠加冗余等式**（如行业中性已隐含净敞口=0，再传 `net_exposure=0` 会使约束雅可比降秩、SLSQP 求解失败）。
- SLSQP 是局部解法：凸目标（min_var/mean_var）保证全局最优；max_sharpe/risk_parity/max_div 为非凸，用多起点更稳。
- **多空组合锚定**：`full_investment=False` 时，带收益项的目标（mean_var/max_sharpe）用 `net_exposure=0` 做美元中性；纯方差目标（min_var/risk_parity）请用 `full_investment=True` 的多头组合（net=0 不足以锚定方差最小化，会塌缩成 0）。
- 换手约束 `‖w−w_prev‖₁≤τ` 非光滑，SLSQP 按近似处理；约束紧绑时可能略有偏差。
- 只做研究/方法论参考，不构成投资建议。
