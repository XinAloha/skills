---
name: portfolio-attribution
description: Decompose a portfolio's active return versus its benchmark into sector allocation, stock selection, and interaction (Brinson-Fachler + Carino multi-period linking) plus factor contributions (cross-sectional regression), answering where the excess return came from. Evidence-first with built-in identity assertions. Use when the user asks 组合归因, 业绩归因, 超额收益来源, 这策略赚的是配置还是选股, or 回测跑完想知道钱赚在哪, on Claude Code, Codex, Cursor, Hermes, or OpenClaw.
license: GPL-3.0-only
metadata:
  organization: QuantSkills
  organization_url: https://github.com/quantskills
  repository: skill-portfolio-attribution
  repository_url: https://github.com/quantskills/skill-portfolio-attribution
  project_type: skill
  collection: portfolio-attribution
quantSkills:
  project_type: skill
  category: portfolio
  tags:
  - portfolio-attribution
  - brinson-fachler
  - carino-linking
  - factor-attribution
  - performance
  platforms:
  - claude-code
  - codex
  - cursor
  - hermes
  - openclaw
  language: zh-en
  status: stable
  validation_level: runnable
  maintainer_type: community
  requires: []
  summary_zh: 把组合相对基准的主动收益分解为行业配置、个股选择、交互效应与因子贡献，回答超额收益的来源；恒等式内建为运行时断言，算不平即拒绝出报告。
  summary_en: Decompose a portfolio's active return vs benchmark into allocation, selection, interaction, and factor contributions; identity checks are built-in runtime assertions.
---

# 组合绩效归因（Portfolio Attribution）

把组合跑赢/跑输基准的主动收益，精确拆解为**行业配置、个股选择、交互效应**（Brinson-Fachler + Carino 多期链接）与**因子贡献**（横截面回归）——回答量化流水线中回测之后的下一个问题：这笔超额收益到底赚在哪、亏在哪。

**它做什么**：把主动收益按来源拆开，各项加总精确等于区间主动收益（恒等式内建为运行时断言，算不平即拒绝出报告）。
**它不做什么**：不生产行情数据、不做组合优化、不给买卖指令。

## 何时使用

- 有一段时间的组合持仓，想知道超额收益的来源
- 回测跑完，想解释策略赚的是行业配置的钱还是选股的钱
- 想验证组合收益是否真的来自设计时押注的因子（动量、价值……）

## 输入：只需提供「持仓」

唯一需要提供的是**每日持仓时间序列**（来自任意回测、券商对账单或实盘账户，任何平台皆可）：

| 持仓（需提供） | 列 | 说明 |
|----|----|------|
| 每日持仓 | `date, symbol, weight` | 期初权重；或给 `market_value`，由 Agent 换算 `weight = 市值 / 账户总资产` |

- **现金记一行 `symbol=CASH`**（否则会漏掉现金拖累——实测中现金常是主动收益的最大来源之一）。
- 只需提供持仓；下面三张由 Agent 从**公开数据**补齐。

归因引擎内部消费四张长表（parquet/csv，列名固定）：

| 表 | 列 | 来源 |
|----|----|------|
| 组合权重 | `date, symbol, weight` | ← 提供的持仓 |
| 基准权重 | `date, symbol, weight` | ← 默认「持股等权」，由持仓生成 |
| 个股收益 | `date, symbol, ret` | ← 公开前复权行情 |
| 行业分类 | `symbol, sector` | ← 公开行业分类 |
| 因子暴露（可选） | `date, symbol, <因子列...>` | ← 提供则追加因子归因 |

输入校验（不符合直接报错/告警，不静默处理）：
- 权重每日加总偏离 1 超过 1e-4：**报错**，不静默归一化
- 权重/收益表出现重复 `(date, symbol)`：**报错**，避免 merge 时重复计权导致错误归因
- 持仓缺对应收益：**报错**
- `|日收益|>21%`：**告警**——A股单日涨跌幅一般 ≤20%，超过多为未复权/停牌复牌/异常数据，需核对收益是否已前复权

## 派生三张表怎么来（Agent 自动补，只用公开数据）

除持仓外的三张，Agent 从**公开数据**生成，**全程不连任何数据库、不需要私有凭证**：

- **个股收益**：公开前复权日线（akshare `stock_zh_a_daily(adjust="qfq")` / Pandadata）。前复权已处理除权除息，`close/pre_close` 即为干净日收益。
- **行业分类**：公开行业分类（akshare / Pandadata / 巨潮公司档案）。
- **基准（默认：持股等权）**：把**持有过的股票等权**作为基准——只需持仓本身，不依赖任何外部指数数据，能完全对账、无停牌/成分调整/前视偏差噪声。回答"你的主动权重 vs 等权持有同一批股，加分还是减分"。
  - 可选「vs 沪深300 / 上证指数」：需**干净的指数成分收益**。裸从成分股重建易踩两个坑——① 末期成分回套历史的**前视偏差**（会显著虚高基准）；② 停牌复牌/分红噪声。须用 point-in-time 成分并谨慎处理，否则不建议。

**安全边界（重要）**：本 skill **不含任何数据库连接/适配器**。它只吃"持仓 + 公开数据"，**绝不接入使用方的私有库**（那会泄露数据库凭证与他人数据）。把回测持仓从私有系统导出成文件，是使用方（平台）的职责，不是本 skill 的一部分。

## 运行

```bash
python scripts/attribution.py \
  --portfolio p.parquet --benchmark b.parquet \
  --returns r.parquet --sectors s.csv \
  [--exposures e.parquet] [--out report_dir]
```

输出：终端文本报告；指定 `--out` 时额外写三种格式——`attribution_report.txt`（文字）、`attribution_report.json`（结构化，含逐期明细）、`attribution_report.html`（自包含可视化报告：主动收益瀑布 + 行业贡献发散条 + 因子归因，内联 SVG、零依赖、离线可用、明暗自适应）。加 `--no-html` 可跳过 HTML。

## 工作流

1. 校验输入（权重加总、重复主键、收益覆盖、收益合理性、行业覆盖）
2. 逐期 Brinson-Fachler：配置 = (wp−wb)(rb−Rb)，选股 = wb(rp−rb)，交互 = (wp−wb)(rp−rb)
3. Carino 几何链接把逐期效应缩放到跨期可加，恒等式内建断言：各项加总 ≡ 区间主动收益
4. （可选）逐期横截面 OLS 估计因子收益，主动暴露 × 因子收益 = 因子贡献，残差为特质/选股收益；**因子贡献同样用 Carino 系数逐期缩放并在全域计算，因此因子面板合计 ≡ 行业面板合计 ≡ 区间主动收益**（两个面板对同一总账）
5. 输出报告

## 解读要点

- **配置为正**：超配了跑赢基准的行业，或低配了跑输的行业
- **选股为正**：行业内部选出的股票赢了该行业基准
- **交互项**：主动权重 × 主动选股的二阶项，通常较小；很大时说明押注集中
- 因子归因里 **特质项很大**：收益主要来自因子解释不了的部分——要么是真选股能力，要么是因子模型缺项

## 自检

```bash
python scripts/validate.py   # 13 项数学恒等式与护栏测试，必须全通过
```

包括：单期/多期恒等式、零主动组合全零、纯配置组合选股为零、纯选股组合配置为零、线性收益下特质项为零、**因子面板与行业面板对同一区间主动收益**、权重守卫、**重复主键守卫**、**零权重行业不产生 NaN**、**收益合理性告警**、csv 前导零。

## 边界与不做的事

- 假设组合每期按给定权重再平衡；期内交易、费用不在 v1 范围
- **现金**：在持仓里记 `CASH` 行即计入现金拖累/贡献；不记则漏掉
- 因子收益用 OLS 估计，未做行业中性化与加权回归（计划 v2）
- **不含数据库适配器**：只吃"持仓 + 公开数据"，不接入任何私有库
- 收益护栏只告警不改数据；数据清洗（复权、剔除脏值）是取数环节的职责，非归因引擎
