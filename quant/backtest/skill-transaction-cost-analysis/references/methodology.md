# 方法论 (methodology)

本 Skill 用 **Perold (1988) implementation shortfall（IS，执行差额）** 框架，把一笔/一批成交相对基准价的总成本拆成五个可归因分项，全部以 **bps（万分之一，相对基准价）** 计量。

## 1. 符号约定

- `side=buy → dir=+1`，`side=sell → dir=−1`。
- 所有分项统一为**"对本方不利为正"**：买入价高于基准是成本(+)；卖出价低于基准也是成本(+)。`dir` 已吸收方向符号。
- 基准价 `benchmark` 可选 `区间VWAP / 区间TWAP / 到达价arrival`，默认 VWAP。

## 2. 从分钟线重建的市场量

对每个标的用 `get_stock_min`（1/5/15/60m）取成交日的分钟线（单标的容器 `MinuteBars`）：

- **区间 VWAP** = `Σ amount / Σ volume`（成交区间 = 成交时刻 ± window/2，默认 30 分钟）。无 `amount` 时用 `close × volume` 近似。
- **区间 TWAP** = 各分钟典型价 `(H+L+C)/3` 的等权平均。
- **到达价 arrival** = 首笔成交时刻**前一根**分钟线的收盘价（决策价代理）；用户可显式提供真实决策价。
- **年化波动 σ** = 分钟对数收益样本标准差 × `sqrt(240 × 244)`（每日 240 分钟、年 244 交易日）。样本不足回退经验值 0.30。
- **ADV（日均成交量，股）** = 分钟量按自然交易日聚合取均值；区间覆盖不足半日时用 `分钟均量 × 240` 外推为整日量。

## 3. 五项分解

设成交价 `P`、数量 `Q`、基准价 `B`、到达价 `A`、区间 VWAP `V`。

| 分项 | 公式（bps） | 含义 |
|---|---|---|
| **择时 timing** | `dir · (B − A) / A · 1e4`；arrival 基准为 0 | 决策 → 所选执行基准，价格向不利方向的漂移 |
| **冲击 impact** | `k · σ_day · sqrt(Q / ADV) · 1e4` | square-root 市场冲击（自身交易推价，恒为正） |
| **点差 spread** | `0.5 · mean((H − L) / mid) · 1e4` | 分钟高低幅一半近似半点差（恒为正） |
| **费用 fees** | `佣金bps + 过户费 + (卖出A股)印花税5bps` | 显性交易费用 |
| **滑点 slippage** | `dir · (P − B) / B · 1e4` | 成交价相对所选 VWAP/TWAP/arrival 基准的残差 |

其中 `σ_day = σ_annual / sqrt(244)`，为日尺度波动——square-root 冲击模型的经验标定通常以日波动为输入，故此处不用区间尺度 σ。

**总成本** = timing + impact + spread + fees + slippage（逐笔求和），组合层面按**成交额加权**聚合。

### square-root 冲击模型

`impact_ratio = k · σ_day · sqrt(参与率)`，参与率 = `Q / ADV`。这是买方与经纪商广泛使用的市场冲击近似（Almgren et al. 2005；Kissell 2013）：冲击随交易规模的**平方根**增长而非线性，`k` 为经验系数（默认 0.1，可按品种/市场标定）。与 `skill-portfolio-liquidity-stress-test` 共用同一冲击内核——那个测"能否清掉"，本 Skill 算"清掉花了多少"。

## 4. A 股费用口径

- **佣金**：单边 `commission_bps`（默认 2.5 bps，含规费），买卖双边各计。
- **印花税**：A 股（`.SH/.SZ/.BJ`）**卖出**单边 0.05% = 5 bps（2023-08-28 起由 0.1% 下调至 0.05%）。
- **过户费**：约万分之 0.1 量级，统一小额计入。
- 港美股用日线自带的 `vwap/bid/ask` 可替代分钟近似，精度更高（本 Skill 预留 `hk_daily/us_daily` 入口）。

## 5. ⚠️ 局限与近似声明

- **无逐笔 tick / 盘口**：Pandadata 提供分钟线，不含逐笔成交与实时买卖盘口。因此：
  - **点差为分钟级近似**：用"分钟内高低幅的一半"代理半点差，通常**高估**真实有效点差（分钟高低幅包含了区间内的价格漂移，不仅是买卖价差）。
  - **冲击为模型估计**：非从实际盘口深度反演，依赖 `k` 与 ADV/σ 估计的质量。
- **到达价代理**：无真实下单时间戳时用成交前一分钟收盘价，可能低估或高估 timing。
- **区间窗口敏感性**：VWAP/TWAP 依赖 `window_minutes`（默认 30 分钟），窗口越宽越平滑。
- 结论用于**研究与执行诊断**，不用于精确清算结算。

## 参考文献

- Perold, A. (1988). *The Implementation Shortfall: Paper versus Reality.* Journal of Portfolio Management.
- Almgren, R., Thum, C., Hauptmann, E., Li, H. (2005). *Direct Estimation of Equity Market Impact.* Risk.
- Kissell, R. (2013). *The Science of Algorithmic Trading and Portfolio Management.* Academic Press.

> 仅供研究参考，不构成投资建议。
