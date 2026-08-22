# skill-risk-return-metrics

**简体中文** | [English](README.en.md)

单标的风险收益画像。给一个股票代码和时间窗口，一次算出年化收益、年化波动率、夏普、索提诺、最大回撤、卡玛比率、胜率等配置端常用指标，自动按代码后缀路由 A股 / 港股 / 美股。分母为 0 的比率（平序列、零回撤）返回 `null` 而非 `NaN` 或崩溃。仅输出统计事实，不提供买卖指令。

<p align="center">
  <img alt="role" src="https://img.shields.io/badge/role-风险收益画像-brightgreen">
  <img alt="output" src="https://img.shields.io/badge/output-年化·夏普·回撤·卡玛-blue">
  <img alt="market" src="https://img.shields.io/badge/market-A股·港股·美股-9cf">
  <img alt="data" src="https://img.shields.io/badge/data-panda__data·tqx__data-yellow">
  <img alt="license" src="https://img.shields.io/badge/license-GPLv3-blue">
</p>

`skill-risk-return-metrics` 是 QuantSkills 社区的单标的风险收益 Skill。它回答“这只票风险多大、这个收益值不值”，与做单标的信号的 `skill-ma-crossover-signal`、做两标的关系的 `skill-pair-correlation` 互补不重叠。

## 这个 Skill 解决什么问题

“X 风险大不大？这点收益配得上它的波动吗？”——这是配置端反复出现的问题，否则每次都要手写 pandas 重新推导夏普 / 最大回撤 / 卡玛。

本 skill 把它变成可核对的一次调用：

- 一条收盘序列 → 一整套配置端比率（**年化收益、波动率、夏普、索提诺、最大回撤 / 当前回撤、卡玛、胜率**）；
- 未定义的比率（平序列、零回撤、无下跌日）显式返回 `null`，而不是悄悄给出 `NaN`；
- 跨市场统一口径（252 交易日/年），A股与港美股同一套指标可直接横向比较。

## 计算口径

| 字段 | 公式 |
|---|---|
| `total_return` | `last_close / first_close − 1` |
| `annualized_return_cagr` | `(last_close / first_close) ** (252 / observations) − 1` |
| `annualized_return_mean` | `mean(daily_return) × 252` |
| `annualized_volatility` | `std(daily_return, ddof=1) × sqrt(252)` |
| `sharpe` | `(annualized_return_mean − risk_free_rate) / annualized_volatility` |
| `sortino` | `(annualized_return_mean − risk_free_rate) / (downside_std × sqrt(252))` |
| `max_drawdown` | `min(cum / cummax(cum) − 1)`，`cum = cumprod(1 + daily_return)` |
| `current_drawdown` | 回撤序列最后一个值 |
| `calmar` | `annualized_return_cagr / abs(max_drawdown)` |
| `win_rate` | `mean(daily_return > 0)` |

分母为 0 的比率（平序列、无回撤、无下跌日）返回 `null`。为时点结果，仅按上游数据提供的复权口径计算。

## 快速开始

```bash
# 依赖：pandas / numpy + panda_data(A股) / tqx_data(港美股)
python scripts/risk_return_metrics.py 600519.SH --lookback-days 250 --risk-free-rate 0.02
python scripts/risk_return_metrics.py 0700.HK --start-date 20260101 --end-date 20260601
```

作为平台 Skill 使用时，入口为 `scripts/risk_return_metrics.py` 中的 `async def run(...) -> str`（Panda QuantFlow skill 契约，形状同已上线的 `analysis_technical` / `fx_rates`）。缺少取数库时返回结构化 `Error: …` 字符串，而非抛异常。

## 示例输出

`0700.HK` 示例（完整文件见 [`examples/output/`](./examples/output/)）：

```
区间总收益 +8.29%    年化(CAGR) +24.31%    年化波动 28.74%
夏普 0.874    索提诺 1.201    卡玛 1.587    胜率 54.1%
最大回撤 -15.32%    当前回撤 -2.10%
```

> 区间年化约 24%、波动约 29%，夏普 0.87 中等偏上；卡玛 1.59 表示单位最大回撤约换 1.6 倍年化。
> 结构化 JSON 见 [`examples/output/risk_return_metrics.json`](./examples/output/risk_return_metrics.json)。
> 示例数值取自 SKILL.md 输出 schema，非实时行情。

## 数据从哪来

代码后缀决定市场路由（`market=auto` 时）：

- **A股** `.SH` / `.SZ` / `.BJ` 或裸 6 位数字 → `panda_data` 日线收盘；
- **港股** `.HK` → `tqx_data`；
- **美股** `.NB` / `.US` / `.NY` → `tqx_data`。

也可显式传 `--market cn|hk|us` 强制。取数由平台运行时注入，输出质量取决于上游数据可得性与正确性。

## 目录结构

```
skill-risk-return-metrics/
├── SKILL.md                        # Agent 使用说明（核心）：用途、参数、输出 schema、公式、when-NOT-to-use
├── README.md                       # 本文件（简体中文，首段=平台简介）
├── README.en.md                    # 英文说明
├── LICENSE                         # GPLv3 许可证全文
├── quantskills.yaml                # QuantSkills 上游清单：provenance / 依赖 / license: GPL-3.0-only
├── agents/                         # 各 Agent 平台运行时入口（都回到同一份 SKILL.md）
│   ├── cursor-rule.mdc             #   Cursor 规则入口
│   ├── openai.yaml                 #   OpenAI-style / OpenClaw 运行时清单（display_name / default_prompt）
│   └── portable-loader.md          #   Hermes / OpenClaw 便携加载器
├── scripts/
│   └── risk_return_metrics.py      # 可执行：async def run(...) -> str + 独立 CLI；收益/风险/比率计算
└── references/
    └── example_output.md           # 输出字段逐项说明
└── examples/
    └── output/                     # 示例输出（数值取自 SKILL.md schema）
        ├── risk_return_metrics.json    #   结构化 JSON 示例
        └── risk_return_metrics.txt     #   人类可读摘要 + 解读 + 免责
```

## 运行时入口

本 Skill 支持 Claude Code、Codex、Cursor、Hermes 和 OpenClaw。Claude Code、Codex 与原生 Skill 运行时直接加载 `SKILL.md`；Cursor 使用 `agents/cursor-rule.mdc`；Hermes / OpenClaw 在无法原生发现 Skill 时使用 `agents/portable-loader.md`（`agents/openai.yaml` 提供 OpenClaw 展示信息）。所有入口最终都回到同一份 `SKILL.md` 与同一个脚本，不维护平行业务逻辑。

## 与社区其他 skill 的分工

- **本 skill**：单标的夏普 / 回撤 / 卡玛等风险收益画像 —— **看一只票的风险收益**；
- `skill-ma-crossover-signal`：单标的趋势 / 金叉死叉 —— **看一只票的择时信号**；
- `skill-pair-correlation`：两标的相关性 / 对冲 beta / 价差 —— **看两只票的关系**；
- 多标的排序 / 筛选 → 交给因子类 skill；只要原始 OHLCV / 分钟线 → 交给行情类 skill。

## 免责声明

- **仅供研究与教育用途。** 输出为信息性研究，**不构成投资建议，不承诺任何收益**。
- **数据来源：** A股经 `panda_data`、港美股经 `tqx_data`（平台提供），输出质量取决于上游数据可得性与正确性。
- **假设与局限：** 指标基于日线收盘、按 252 交易日/年年化；分母为 0 的比率（平序列、无回撤 / 下跌日）返回 `null`；为时点结果，未做上游之外的额外复权。
- **风险边界：** 请勿作为实盘决策唯一依据，独立验证并注意市场风险。

## License

GPL-3.0-only。本 skill 为 QuantSkills 社区原创，风险收益指标为量化通用做法。许可证全文见 [`LICENSE`](./LICENSE)。
