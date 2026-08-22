# skill-risk-model

简体中文 | English

Barra 式结构化多因子风险模型与风险归因。用截面回归估风格/行业因子收益，构建结构化协方差 `Σ = XFXᵀ + Δ`，并把组合风险拆成因子风险 vs 特异风险、逐因子贡献。填补站内"回测无风险模型、优化缺协方差"的空白。

> A Barra-style structural multi-factor risk model. Estimates style and industry
> factor returns via cross-sectional WLS regression, builds a structural,
> positive-definite covariance `Σ = XFXᵀ + Δ`, and decomposes portfolio risk
> into factor vs specific and factor-by-factor contributions.

## 为什么需要它

`skill-backtest` 明说"无风险模型"，`skill-portfolio-optimize` 又需要协方差。本 Skill 提供结构化、正定、可解释的 Σ，并能回答"我的组合风险到底来自哪个因子"。

仓库自带 demo 的真实输出（`python examples/run_demo.py`，全合成、无需凭证）：

```
构建 Barra 式结构化风险模型 ...
  回归期数: 649  因子数: 9
  因子: SIZE, MOMENTUM, SHORT_REV, VOLATILITY, BETA, IND_CONS, IND_FIN, IND_HLTH, IND_TECH

等权组合的风险归因:
  total volatility (annual) : 4.63%
  factor risk share         : 56.5%      ← 因子风险
  specific risk share       : 43.5%      ← 特异风险
  IND_FIN   exposure 0.250   %var 15.2%
  IND_HLTH  exposure 0.250   %var 14.9%
  ...                                     （各因子 %var 之和 = 因子风险占比）
```

## 快速开始

```bash
pip install -r requirements.txt

python examples/run_demo.py             # 推荐先跑

# 对你自己的数据：
python scripts/risk_model.py \
  --returns returns.csv \               # [date x symbol] 收益面板（标的数 ≫ 因子数）
  --weights weights.csv \               # symbol,weight 两列
  --out model.json
```

## 模型与文献

| 部件 | 方法 | 文献 |
|------|------|------|
| 因子收益 | 逐日截面 WLS（权重 ∝ √市值）| Barra USE4；Fama-MacBeth (1973) |
| 因子协方差 F | EWMA + PSD 修正 | RiskMetrics (1996) |
| 收缩（可选） | Ledoit-Wolf | Ledoit & Wolf (2004) |
| 风险归因 | Euler / 成分风险贡献 (CCTR) | Menchero & Davis (2011) |

详见 [`references/methodology.md`](references/methodology.md)。

## 与组合优化器配套

`build_risk_model(...)` 返回的 **`asset_cov`**（`symbol×symbol` 的 Σ=XFXᵀ+Δ）可直接作为 `skill-portfolio-optimize` 的 `cov` 输入，形成"风险模型 → 组合优化 → 回测 → 过拟合检测"的完整链路。

> 注意：用于优化器的是 `asset_cov`（资产协方差，N×N），**不是** `factor_cov`（因子协方差，K×K）。后者只用于风险归因。

```python
from risk_model import build_risk_model
m = build_risk_model(returns, market_cap, industry)
cov = m["asset_cov"]            # 喂给 skill-portfolio-optimize 的 build_portfolio(cov=cov, ...)
```

## 数据接入

`scripts/data_source.py` 封装 panda_data（`get_stock_daily`+`get_adj_factor` 收益、`get_market_cap`、`get_industry`），**无凭证时自动回退合成数据**。配置真实凭证：

```bash
export DEFAULT_USERNAME=...  DEFAULT_PASSWORD=...  JAVA_SERVICE_BASE_URL=...
```

## 许可证

GPL-3.0 · Copyright (C) 2026.
