# skill-portfolio-optimize

简体中文 | English

把多因子 alpha 信号转成最优组合权重。支持均值方差 / 最小方差 / 最大夏普 / 风险平价 / 最大分散化五种目标，外加个股上限、行业中性、因子暴露中性、换手率约束。补上站内"因子合成 → 回测"之间最大的断层。

> Convert an alpha signal into optimal portfolio weights under realistic
> constraints. Five objectives (mean-variance, min-variance, max-Sharpe, risk
> parity, max diversification) plus weight caps, sector / factor neutrality and
> turnover limits. Solved with scipy SLSQP — no heavyweight solver required.

## 为什么需要它

回测只会"Top 10% 等权"，等权忽略风险集中、行业押注和换手成本。本 Skill 用凸优化得到真正可交易的权重。

仓库自带 demo 的真实输出（`python examples/run_demo.py`，全合成、无需凭证）：

```
### 五种目标函数对比（同一组 10 只标的）###
min_variance         vol=0.070 holdings=10 maxw=0.120
max_sharpe           vol=0.080 holdings=10 maxw=0.187
risk_parity          vol=0.070 holdings=10 maxw=0.100   ← 风险最分散
mean_variance        vol=0.115 holdings= 5 maxw=0.300   ← 集中下注

### 行业中性 + 个股上限5% + 换手约束（多空）###
 sum / gross       : 0.0000 / 0.4000        ← 美元中性(来自行业中性约束)
 sector exposure   : 金融0.0 家电0.0 白酒0.0 科技0.0 医药0.0   ← 行业完全中性
 turnover          : 1.0  (≤ 1.5 约束)
```

约束真的在生效：行业暴露精确归零、个股不超 5%、换手不破上限。这里的**美元中性来自行业中性约束本身**（每个行业净敞口=0 ⇒ 组合总净敞口=0），不是 `long_only=False` 自动产生的。

> 做**没有行业约束**的纯多空组合时，务必显式传 `net_exposure=0.0` 锚定美元中性（仅对带收益项的 `mean_variance`/`max_sharpe` 有效）；否则构造器会发警告。纯方差目标（`min_variance`/`risk_parity`）的多空组合请改用 `full_investment=True` 的多头组合。

## 快速开始

```bash
pip install -r requirements.txt

python examples/run_demo.py          # 推荐先跑

# 对你自己的数据：
python scripts/optimize_report.py \
  --returns returns.csv \            # [date x symbol] 收益面板
  --signal  alpha.csv \              # symbol,alpha 两列
  --objective mean_variance \
  --weight-cap 0.05 \
  --out weights.csv
```

## 方法与文献

| 目标 / 方法 | 文献 |
|------------|------|
| 均值方差 / 最小方差 | Markowitz (1952) |
| 风险平价（ERC） | Maillard, Roncalli & Teïletche (2010) |
| 最大分散化 | Choueifaty & Coignard (2008) |
| Ledoit-Wolf 收缩协方差 | Ledoit & Wolf (2004) |

详见 [`references/methodology.md`](references/methodology.md)。

## 数据接入

`scripts/data_source.py` 封装 panda_data（`get_stock_daily` + `get_adj_factor` → 收益面板；`get_market_cap`、`get_industry` 供约束用），**无凭证时自动回退合成数据**。配置真实凭证：

```bash
export DEFAULT_USERNAME=...  DEFAULT_PASSWORD=...  JAVA_SERVICE_BASE_URL=...
```

## 许可证

GPL-3.0 · Copyright (C) 2026.
