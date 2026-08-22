---
name: skill-risk-model
description: >
  Build a Barra-style structural multi-factor risk model and attribute portfolio
  risk. Use when a user wants a covariance matrix for optimisation, asks how
  risky a portfolio is, where its risk comes from (which factors / styles /
  industries), or wants factor vs specific risk decomposition. Estimates style
  & industry factor returns via cross-sectional regression, factor covariance
  and specific risk.
license: GPL-3.0
category: 分析
metadata:
  organization: QuantSkills
  organization_url: https://github.com/quantskills
  repository: skill-risk-model
  repository_url: https://github.com/quantskills/skill-risk-model
  project_type: skill
  collection: portfolio-risk-validation
---

```json qsh-form
{
  "version": 1,
  "task": {
    "placeholder": "请说明风险模型或归因目标，并上传收益率、市值、行业及需要归因时的组合权重数据",
    "required": true
  },
  "fields": [
    {
      "key": "mode",
      "label": "分析模式",
      "type": "select",
      "default": "full",
      "options": [
        { "value": "full", "label": "建模与风险归因" },
        { "value": "covariance", "label": "构建协方差矩阵" },
        { "value": "attribution", "label": "组合风险归因" }
      ]
    },
    {
      "key": "universe",
      "label": "股票池",
      "type": "text",
      "placeholder": "如：沪深300、自定义持仓池；需保证标的数显著多于因子数"
    },
    {
      "key": "focus",
      "label": "重点关注",
      "type": "text",
      "placeholder": "如：风格因子贡献、行业风险、特异风险、优化器输入"
    }
  ],
  "prompt_template": "{{#task}}任务与材料：\n{{task}}\n\n{{/task}}{{#attachments}}用户上传的材料（已放入工作区）：\n{{attachments}}\n\n{{/attachments}}请执行 Barra 风格结构化多因子风险模型 {{mode}}。{{#universe}}股票池为 {{universe}}。{{/universe}}{{#focus}}重点关注：{{focus}}。{{/focus}}校验收益率、市值、行业及组合权重输入，以逐日 WLS 估计因子收益，用 EWMA 估计因子协方差与特异风险并做 PSD 修正，明确区分 factor_cov 与供优化器使用的 asset_cov，给出组合年化波动、因子/特异风险拆分和逐因子贡献，输出中文报告。"
}
```

# skill-risk-model

role: skill · output: factor covariance + specific risk + risk attribution · paradigm: structural multi-factor (Barra-style)

把一篮子标的的协方差，从"裸样本估计"升级为**结构化风险模型**：风格 + 行业因子驱动的协方差，加上可解释的风险归因。

## 🎯 这个 Skill 解决什么问题

`skill-backtest` 自述"无风险模型"，`skill-portfolio-optimize` 又需要一个可信的协方差 Σ。本 Skill 填这个洞——用 Barra 式结构化模型：

```
r_{i,t+1} = Σ_k X_{i,k,t} · f_{k,t} + u_{i,t}
            └─ 暴露 × 因子收益 ─┘   └ 特异收益 ┘
```

它回答三个问题：
1. **协方差从哪来**？`Σ = X F Xᵀ + Δ`（结构化、正定、可给优化器用）。
2. **组合有多大风险**？年化波动率 + 因子风险 vs 特异风险拆分。
3. **风险来自哪**？逐因子的暴露与方差贡献（CCTR）。

## ⚡ 工作流（Agent 按此执行）

1. **算暴露 X**：`scripts/exposures.py`，风格因子 = SIZE / MOMENTUM / SHORT_REV / VOLATILITY / BETA（截面去极值 + 标准化）+ 行业哑变量。（VALUE/LIQUIDITY 需财务/换手字段，作为可选传入。）
2. **截面回归估因子收益 f**：`scripts/cross_section_reg.py`，逐日 **WLS（权重 ∝ √市值）**，残差即特异收益 u。
3. **估协方差**：`scripts/factor_cov.py`，因子协方差 F 用 **EWMA**（近期加权）、特异方差 Δ 用 EWMA，均做 PSD 修正与年化。
4. **风险归因**：`scripts/risk_attribution.py`，给定权重 → 因子/特异拆分 + 逐因子贡献。
5. **出报告**：`scripts/risk_model.py` 编排 → RiskReport（JSON + 文本）。

```bash
python scripts/risk_model.py --demo                                  # 离线演示
python scripts/risk_model.py --returns returns.csv --weights w.csv --out model.json
python examples/run_demo.py
```

## 🗃️ 输入契约

| 输入 | 形态 | 必需 | 说明 |
|------|------|------|------|
| `returns` | `DataFrame [date×symbol]` | 是 | 日收益面板（标的数应 ≫ 因子数）|
| `market_cap` | `DataFrame [date×symbol]` | 是 | 算 SIZE 暴露与回归权重 |
| `industry` | `Series [symbol]` | 是 | 行业分类（行业因子）|
| `weights` | `Series [symbol]` | 风险归因时 | 待归因的组合权重 |

输出：`factor_cov`（K×K 因子协方差）、`asset_cov`（**N×N 资产协方差 Σ=XFXᵀ+Δ**）、`specific_var`（symbol）、`exposures`（最新）、风险归因表。

## ⚠️ 重要约束

- **标的数必须远大于因子数**：5 风格 + N 行业，至少需要 ~30+ 只标的，否则截面回归无法识别（标的太少会跳过所有期）。
- 暴露每日截面标准化，因子收益才可跨期比较。
- 喂给 `skill-portfolio-optimize` 的是 **`asset_cov`（N×N，经 EWMA+特征值修正保证正定）**，不是 K×K 的 `factor_cov`。后者仅用于风险归因。

## 🔗 管线定位

```
[本 Skill：风险模型 Σ + 归因] ──供 Σ──> skill-portfolio-optimize ──权重──> skill-backtest
                              └──归因──> 任意组合的风险体检
```

## 📦 仓库结构

```
skill-risk-model/
├── SKILL.md / README.md / requirements.txt / LICENSE
├── scripts/
│   ├── exposures.py          # 风格暴露 + 行业哑变量(截面标准化)
│   ├── cross_section_reg.py  # 逐日 WLS 截面回归 -> 因子收益/特异收益
│   ├── factor_cov.py         # 因子协方差(EWMA) + 特异风险(EWMA)
│   ├── risk_attribution.py   # 因子vs特异 + 逐因子 CCTR
│   ├── risk_model.py         # 编排 -> RiskReport + CLI
│   └── data_source.py        # panda_data 适配层(离线自动回退)
├── references/methodology.md
└── examples/run_demo.py
```

仅供研究/方法论参考，不构成投资建议。
