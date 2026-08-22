# skill-pair-correlation

**简体中文** | [English](README.en.md)

两标的关系分析。给两个股票代码，一次算出收益相关系数（全窗口 + 近 20/60 日）、对冲 beta（A 对 B）、以及最新对数价差 z-score，用于配对交易 / 对冲 / 相关性判断。两条腿各自独立按后缀路由 A股 / 港股 / 美股，并在**任何统计量之前先按共同交易日 inner-join 对齐**。仅输出统计事实与推断，不提供买卖指令。

<p align="center">
  <img alt="role" src="https://img.shields.io/badge/role-相关性·对冲-brightgreen">
  <img alt="output" src="https://img.shields.io/badge/output-相关系数·对冲beta·价差z-blue">
  <img alt="market" src="https://img.shields.io/badge/market-A股·港股·美股-9cf">
  <img alt="data" src="https://img.shields.io/badge/data-panda__data·tqx__data-yellow">
  <img alt="license" src="https://img.shields.io/badge/license-GPLv3-blue">
</p>

`skill-pair-correlation` 是 QuantSkills 社区的两标的关系 Skill。它回答“这两只票走势像不像 / 对冲比例多少 / 价差偏离没有”，与做单标的信号的 `skill-ma-crossover-signal`、做单标的风险画像的 `skill-risk-return-metrics` 互补不重叠。

## 这个 Skill 解决什么问题

“腾讯和阿里走势相关吗？”“做这组配对要用多大对冲比例？”“现在价差偏离了没有？”——相关性和对冲 beta 是每一笔配对交易、每一个“我账户里这两只是不是冗余”问题的基础，但手搓极易出错：**最经典的 bug 就是拿两条从没在同一交易日对齐过的收益序列去算相关**，一个停牌日就能悄悄让结果失真。

本 skill 把它变成可核对的结构化结果：

- **先 inner-join 再统计**——两条腿按共同交易日对齐后才算任何指标，跨市场配对（如 `0700.HK` vs `BABA.NB`）也能正确处理；
- 一次返回**全窗口 + 近 20/60 日相关系数、对冲 beta / hedge_ratio、对数价差 z-score**，并附一句可读的解读提示；
- 退化腿（方差为 0）对应字段返回 `null`，不崩溃。

## 计算口径

| 字段 | 公式 |
|---|---|
| `correlation` | 全对齐窗口日简单收益的 Pearson 相关 |
| `correlation_recent_20 / _60` | 同上，取最后 20 / 60 行（样本不足为 `null`） |
| `beta_a_on_b` / `hedge_ratio` | `cov(ret_a, ret_b) / var(ret_b)` |
| `spread_zscore` | `spread = ln(Pa) − beta·ln(Pb)`；在 `zscore_window` 上 `(spread_last − mean) / std` |
| `price_ratio` | `last_close_a / last_close_b` |

任何分母为 0 的统计量（平腿、`var(ret_b)=0`、`std(spread)=0`）返回 `null`。

## 快速开始

```bash
# 依赖：pandas / numpy + panda_data(A股) / tqx_data(港美股)
python scripts/pair_correlation.py 0700.HK 9988.HK --lookback-days 250
python scripts/pair_correlation.py 600519.SH 000858.SZ --zscore-window 60
```

作为平台 Skill 使用时，入口为 `scripts/pair_correlation.py` 中的 `async def run(...) -> str`（Panda QuantFlow skill 契约）。缺少取数库时返回结构化 `Error: …` 字符串，而非抛异常。

## 示例输出

`0700.HK ↔ 9988.HK` 示例（完整文件见 [`examples/output/`](./examples/output/)）：

```
相关性：全窗口 0.712    近20日 0.664    近60日 0.731
对冲 beta（A 对 B）：0.884    价格比 5.121
对数价差 z-score：-1.83（窗口 60）
```

> 两者中高度相关，价差 z = −1.83 < 0，A 相对 B 偏“便宜”，接近但未到 ±2 的均值回复触发区。
> 结构化 JSON 见 [`examples/output/pair_correlation.json`](./examples/output/pair_correlation.json)。
> 示例数值取自 SKILL.md 输出 schema，非实时行情。

## 数据从哪来

每条腿的代码后缀独立决定市场路由（`market_a` / `market_b = auto` 时）：

- **A股** `.SH` / `.SZ` / `.BJ` 或裸 6 位数字 → `panda_data` 日线收盘；
- **港股** `.HK` → `tqx_data`；
- **美股** `.NB` / `.US` / `.NY` → `tqx_data`。

也可对每条腿显式传 `--market-a` / `--market-b`。取数由平台运行时注入，输出质量取决于上游数据可得性与正确性。

## 目录结构

```
skill-pair-correlation/
├── SKILL.md                     # Agent 使用说明（核心）：用途、参数、输出 schema、公式、when-NOT-to-use
├── README.md                    # 本文件（简体中文，首段=平台简介）
├── README.en.md                 # 英文说明
├── LICENSE                      # GPLv3 许可证全文
├── quantskills.yaml             # QuantSkills 上游清单：provenance / 依赖 / license: GPL-3.0-only
├── agents/                      # 各 Agent 平台运行时入口（都回到同一份 SKILL.md）
│   ├── cursor-rule.mdc          #   Cursor 规则入口
│   ├── openai.yaml              #   OpenAI-style / OpenClaw 运行时清单（display_name / default_prompt）
│   └── portable-loader.md       #   Hermes / OpenClaw 便携加载器
├── scripts/
│   └── pair_correlation.py      # 可执行：async def run(...) -> str + 独立 CLI；对齐 + 相关/beta/价差 z
└── references/
    └── example_output.md        # 输出字段逐项说明
└── examples/
    └── output/                  # 示例输出（数值取自 SKILL.md schema）
        ├── pair_correlation.json    #   结构化 JSON 示例
        └── pair_correlation.txt     #   人类可读摘要 + 解读 + 免责
```

## 运行时入口

本 Skill 支持 Claude Code、Codex、Cursor、Hermes 和 OpenClaw。Claude Code、Codex 与原生 Skill 运行时直接加载 `SKILL.md`；Cursor 使用 `agents/cursor-rule.mdc`；Hermes / OpenClaw 在无法原生发现 Skill 时使用 `agents/portable-loader.md`（`agents/openai.yaml` 提供 OpenClaw 展示信息）。所有入口最终都回到同一份 `SKILL.md` 与同一个脚本，不维护平行业务逻辑。

## 与社区其他 skill 的分工

- **本 skill**：两标的相关性 / 对冲 beta / 价差 —— **看两只票的关系**；
- `skill-ma-crossover-signal`：单标的趋势 / 金叉死叉 —— **看一只票的择时信号**；
- `skill-risk-return-metrics`：单标的夏普 / 回撤 / 卡玛 —— **看一只票的风险收益**；
- 多标的因子筛选 → 交给因子类 skill。

## 免责声明

- **仅供研究与教育用途。** 输出为信息性研究，**不构成投资建议，不承诺任何收益**。
- **数据来源：** A股经 `panda_data`、港美股经 `tqx_data`（平台提供），输出质量取决于上游数据可得性与正确性。
- **假设与局限：** 两条腿先按共同交易日 inner-join 对齐；相关 / beta 基于日简单收益，价差 = `ln(Pa) − beta·ln(Pb)`；相关性与 beta 为历史值、样本外不稳定，退化腿返回 `null`；跨市场配对因交易日历差异会缩小对齐样本。
- **风险边界：** 请勿作为实盘配对 / 对冲唯一依据，独立验证并注意市场风险。

## License

GPL-3.0-only。本 skill 为 QuantSkills 社区原创，相关性与对冲 beta 为量化通用做法。许可证全文见 [`LICENSE`](./LICENSE)。
