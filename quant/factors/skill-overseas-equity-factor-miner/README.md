# 🧩 Overseas Equity Factor Miner · 港美股横截面因子挖掘

**简体中文** | [English](README.en.md)

> 一句话定位：在**港股或美股**上跑一个**横截面 alpha 因子发现循环**——生成候选因子、点位计算、按 **IC / 衰减 / 换手** 校验并排名 top-K，而不是套用一套固定因子。

![type](https://img.shields.io/badge/type-skill-blue)
![category](https://img.shields.io/badge/category-factor-green)
![license](https://img.shields.io/badge/license-GPLv3-blue)

## 📖 这是什么

这是一个「**因子挖掘 / 发现循环**」技能，不是打包好的固定因子库。它引导 agent 完成一整套横截面因子研究流程：

- **输入**：市场（港股 **或** 美股，不混用）、股票池（显式清单或指数成分）、因子族（动量/反转、价值/质量、流动性/换手）、前瞻收益 horizon（如 5/10/20 交易日）、算力预算。
- **处理**：用 `get_trade_cal(exchange=HK|US)` 定调仓日 → 生成候选因子 → **点位（point-in-time）**拼装行情与基本面面板 → 横截面计算（基本面因子在**同业组内以 `*_median` 中位归一**、长表按报告口径去重）→ 逐个用**秩 IC（Spearman）/ IC 衰减 / 换手**校验 → 排名 → 输出 top-K。
- **产出**：一份中文因子挖掘报告（Markdown），含候选公式、IC/衰减/换手表、排名、口径与风险提示、数据来源表。

它**不直接调用数据接口**，所有 Pandadata 调用都委托给姊妹技能 **`skill-pandadata-api`**（由它掌握准确的方法签名与字段名）。

### 与姊妹仓库的区别

| 需求 | 用哪个 |
|---|---|
| **发现/挖掘/筛选**港美股因子（本仓库） | `skill-overseas-equity-factor-miner` |
| **套用**已标准化的港美股基本面因子 | `skill-hk-us-fundamental-factor` |
| A 股 OHLCV 因子库 | `quant-factor-*` 系列 |

## 🚀 快速开始

```bash
cp -r skill-overseas-equity-factor-miner ~/.claude/skills/overseas-equity-factor-miner
```

触发示例 prompt：

```text
在港股这 30 只里挖几个横截面因子，按 5/10/20 日的 IC、衰减和换手筛一下，给我 top-5
帮我在这批美股上生成动量/价值/流动性候选因子并做 rank IC 检验，排个名
对这组港股股票池做一次因子发现，标清点位口径和同业中位归一，输出挖掘报告
```

需要同时安装并可用 `skill-pandadata-api`（本技能通过它取数）。

## 📦 目录结构

```text
skill-overseas-equity-factor-miner/
├── SKILL.md                              # 运行时入口：发现循环 + 输出契约
├── README.md                             # 中文优先说明（本文件）
├── README.en.md                          # English
├── LICENSE                               # GPLv3
├── agents/
│   └── openai.yaml                       # OpenAI / Codex 适配（cursor-rule.mdc、portable-loader.md 由同步生成）
├── references/
│   ├── methodology.md                    # 候选生成、点位面板、IC/衰减/换手数学、排名、坑与降级
│   ├── pandadata-overseas-map.md         # 港股↔美股方法路由与字段说明
│   └── source_boundary.md                # 可读/不可读的数据边界
└── scripts/
    └── validate_report.py                # 报告结构/来源/日期/免责声明校验器（stdlib）
```

## 🖥️ 产出示例

本仓库**默认不提交生成的报告**，运行结果保存在本地。报告的结构由 `scripts/validate_report.py` 约束，最小骨架如下：

```text
# 港股 (HK) 横截面 alpha 因子挖掘报告
## 摘要        （市场 / 股票池 / 调仓窗口 / horizon / 预算 / 3-5 条发现）
## 候选因子    （名称·因子族·公式·输入·预期符号）
## 计算口径    （点位规则、同业中位归一、报告口径去重）
## 有效性检验  （逐因子 秩 IC / IC IR / IC 衰减 / 换手，表格）
## 排名        （top-K，注明排名规则）
## 风险与口径提示（样本期、滞后、存续偏差、币种、小样本）
## 数据说明    （各步骤对应的 Pandadata 接口）
→ 免责声明：……不构成任何投资建议。
```

校验一份草稿报告：

```bash
python scripts/validate_report.py 你的报告.md
# OK → 结构完整；FAIL 会逐条列出缺失项并以非零退出
```

## 🔌 运行时兼容

以 `SKILL.md` 为统一入口，可在 **Claude Code、Codex、Cursor、Hermes、OpenClaw** 等运行时加载；`agents/` 下提供各运行时适配文件（`cursor-rule.mdc`、`portable-loader.md` 由工作区技能同步生成）。

## 🔗 数据来源与依赖

- **Pandadata 港美股接口**（经 `skill-pandadata-api` 调用）：
  - 港股：`get_hk_daily`、`get_hk_detail`、`get_stock_operating_indicator`、`get_stock_mktfin_indicator`、`get_stock_industry_median`
  - 美股：`get_us_daily`、`get_us_detail`、`get_stock_operating_metric`、`get_stock_mktfin_metric`、`get_stock_sector_median`
  - 交易日历：`get_trade_cal(exchange=HK|US)`
- **可选公开兜底**：Yahoo Finance 日线，仅在 Pandadata 行情为空时补价量，报告中明确标注为第三方兜底来源。
- **依赖技能**：`skill-pandadata-api`（提供准确方法签名与字段，本技能不直接调接口，也不臆造签名）。

## 📐 限制与风险边界

| 边界 | 说明 |
|---|---|
| 🔬 样本内、描述性 | IC / 衰减 / 换手衡量历史横截面关联，**不代表未来表现**；除非声明，不含交易成本/融券/容量模型 |
| 🌐 单一市场、单一币种 | 港股与美股**不混用**，HKD/USD 不跨币种加总或比较 |
| ⏱️ 点位口径 | 强制 point-in-time（防前视）与按存续处理股票池（防存活偏差） |
| 🧮 同业归一 | 基本面因子须在同业组内以 `*_median` 归一，不跨行业/跨市场比较分位 |
| 🔢 小样本 | 股票池过小时 IC 不稳定，报告须标注股票池规模 |
| ✋ 外部写入需显式触发 | 保存报告、任何发布均需用户明确指令 |
| 📛 非官方 | 社区项目，非官方/认证/验证；不承诺收益 |

## ⚠️ 免责声明

本仓库仅提供研究方法与流程工具，基于公开数据与规则化分析生成结果，非官方、不隶属任何被研究对象，不验证任何收益声明，**不构成任何投资建议 / does not constitute investment advice**。请自行承担研究、风控与执行的责任。

## 🧑‍🔧 维护者

Created or maintained by `abgyjaguo`.

## 📜 License

This project is licensed under the GNU General Public License v3.0. See [LICENSE](LICENSE).

## 🐼 PandaAI / QUANTSKILLS 社群

<div align="center">
  <img src="https://raw.githubusercontent.com/quantskills/.github/main/profile/assets/pandaai-community-qr.jpg" alt="PandaAI 社群二维码" width="220">
  <br>
  <sub>扫码加入 PandaAI 社群，交流 QUANTSKILLS 技能、Agent 工作流与量化研究实践。</sub>
</div>
