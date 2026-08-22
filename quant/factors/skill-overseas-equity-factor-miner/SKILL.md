---
name: overseas-equity-factor-miner
description: "Discover and validate cross-sectional alpha factors for Hong Kong and US equities - generate candidate factors, compute them, and screen by IC, decay, and turnover. Use when a user wants to mine, test, or rank overseas equity factors from Pandadata HK/US price and fundamental data rather than apply a fixed factor set."
license: GPL-3.0-only
quantSkills:
  organization: https://github.com/quantskills
  organization_url: https://github.com/quantskills
  repository: quantskills/skill-overseas-equity-factor-miner
  repository_url: https://github.com/quantskills/skill-overseas-equity-factor-miner
  project_type: skill
  collection: overseas-equity-factor-miner
  license: GPL-3.0
  category: factor            # trader-research / factor / data-api / replication / monitor / analyst / tooling
  tags: [factor,alpha,hk-us,cross-section,mining]                  # lowercase-hyphenated, 1-10 items
  platforms: [claude-code, codex, openclaw, cursor]        # claude-code / codex / openclaw / cursor / workbuddy
  language: zh-en
  status: draft                     # draft / active / stable / deprecated
  validation_level: listed          # listed / runnable / verified (community three-level scheme)
  maintainer_type: community        # official / community
  creator: abgyjaguo
  maintainer: abgyjaguo
  requires: [skill-pandadata-api]   # dependent sibling skill-* / agent-* repository names
  summary_zh: "在港美股上发现并校验横截面 alpha 因子：生成候选、计算、按 IC/衰减/换手排名。"      # 8-120 chars
  summary_en: "Discover and validate cross-sectional alpha factors for HK/US equities by IC, decay, and turnover."      # 8-200 chars
---

```json qsh-form
{
  "version": 1,
  "task": {
    "placeholder": "补充样本区间、再平衡频率、候选数量、计算预算或数据路径（可选）",
    "required": false
  },
  "fields": [
    {
      "key": "market",
      "label": "海外市场",
      "type": "select",
      "default": "HK",
      "options": [
        { "value": "HK", "label": "港股" },
        { "value": "US", "label": "美股" }
      ]
    },
    {
      "key": "universe",
      "label": "股票池",
      "type": "text",
      "required": true,
      "placeholder": "指数成分集或逗号分隔代码；港股与美股不可混合"
    },
    {
      "key": "horizon",
      "label": "预测周期",
      "type": "select",
      "default": "5,10,20",
      "options": [
        { "value": "5,10,20", "label": "5 / 10 / 20 日" },
        { "value": "5", "label": "5 日" },
        { "value": "10", "label": "10 日" },
        { "value": "20", "label": "20 日" }
      ]
    },
    {
      "key": "focus",
      "label": "候选因子族",
      "type": "text",
      "placeholder": "例如：动量、反转、价值、质量、流动性"
    },
    {
      "key": "top_k",
      "label": "保留因子数",
      "type": "number",
      "default": "10",
      "help": "按 IC IR 并惩罚换手率后保留的候选数量"
    }
  ],
  "prompt_template": "{{#task}}任务与材料：\n{{task}}\n\n{{/task}}{{#attachments}}用户上传的材料（已放入工作区）：\n{{attachments}}\n\n{{/attachments}}在 {{market}} 市场的 {{universe}} 股票池开展海外股票截面因子挖掘{{#focus}}，候选因子族聚焦 {{focus}}{{/focus}}；严格执行时点一致、存续样本和同业标准化规则，在 {{horizon}} 日预测周期上计算 Rank IC、IC IR、IC 衰减与换手率，按说明的规则排名并保留前 {{top_k}} 个候选，披露数据来源、样本、币种及局限，输出中文报告。"
}
```

# Overseas Equity Factor Miner

Use this skill to run a **cross-sectional alpha-factor discovery loop** on Hong Kong
or US equities: define a universe and rebalance calendar, generate candidate factors
from Pandadata overseas price and fundamental data, compute point-in-time cross-sections,
and validate each candidate by rank IC, IC decay, and turnover before ranking the
top-K survivors. This is a **discovery / mining loop**, not a packaged factor set.

This skill does not call data APIs directly. It routes every Pandadata call through the
**`skill-pandadata-api`** skill (see `requires`), which owns the exact method signatures,
parameters, and field names. Use only the real overseas method names listed in
`references/pandadata-overseas-map.md`; never invent a signature.

Read `references/methodology.md` and `references/pandadata-overseas-map.md` before the
first run in a session, plus `references/source_boundary.md`.

## When to use vs. when not to

- Use this skill to **mine, test, or rank** candidate factors from raw HK/US data and
  keep only those with acceptable IC / decay / turnover.
- Do **not** use it to apply a fixed, already-standardized fundamental factor set —
  that is `skill-hk-us-fundamental-factor` (it applies; this one discovers).
- Do **not** use it for A-share OHLCV factor libraries — those are the
  `quant-factor-*` collections. This skill is overseas (HK/US), cross-section, and
  discovery-oriented.

## Core Workflow

1. **Scope the run.** Resolve the market (**HK or US — never mixed**, never cross-currency),
   the universe (an explicit symbol list or an index-constituent set), the factor families
   requested, the forward-return horizons (e.g. 5 / 10 / 20 trading days), and the compute
   budget (how many candidates × rebalance dates). Read the source boundary.
2. **Build the rebalance calendar.** Via `skill-pandadata-api`, call
   `get_trade_cal(exchange=HK|US)` and derive point-in-time rebalance dates and the matching
   forward-return windows. All dates are `YYYYMMDD` strings.
3. **Assemble point-in-time panels.** Pull price/volume with `get_hk_daily` / `get_us_daily`
   and identity with `get_hk_detail` / `get_us_detail`; pull fundamentals with
   `get_stock_operating_indicator` / `get_stock_operating_metric` (long) and
   `get_stock_mktfin_indicator` / `get_stock_mktfin_metric` (wide), and peer medians with
   `get_stock_industry_median` / `get_stock_sector_median`. Route HK vs US by market
   (`references/pandadata-overseas-map.md`). Enforce point-in-time: only use data whose
   report/period-end date is on or before the rebalance date (no look-ahead), and only
   symbols alive at that date (no survivorship backfill).
4. **Generate candidate factors.** Propose a small, named batch across families:
   momentum / reversal (from price), value / quality (from operating + market-financial
   indicators), and liquidity / turnover (from volume and market cap). Write each candidate
   as an explicit formula plus its inputs and expected sign.
5. **Compute cross-sections.** For each rebalance date, compute each candidate for every
   universe member. **Standardize fundamental/quality factors WITHIN the peer group** using
   `*_median` (ROE, margins, valuation multiples are not comparable across sectors), and for
   the long operating table **dedup to one report caliber** (pivot `item_name`; pick one
   `report_type` / `data_type` restatement basis) before computing.
6. **Validate each candidate.** Compute:
   - **Rank IC** = Spearman correlation between the factor cross-section and forward return,
     averaged across rebalance dates (report mean IC, IC std, IC IR = mean/std, and hit rate).
   - **IC decay** across the requested horizons (does signal survive to 10/20 days or vanish?).
   - **Turnover** = average fraction of the top/bottom bucket that changes between rebalances
     (a high-IC factor that fully churns each period is not tradable).
7. **Rank and report top-K.** Rank surviving candidates (default by IC IR, penalized by
   turnover), and report the top-K with formula, inputs, mean IC / IC IR / decay profile /
   turnover, peer-normalization basis, and explicit caveats. Discard or flag candidates that
   fail (near-zero IC, sign flip, fast decay, or extreme turnover).

## Output Contract

Produce a **factor-mining report** (Markdown) whose sections match
`scripts/validate_report.py`:

- Title marking overseas / HK-US factor mining.
- `## 摘要` — market, universe, rebalance window, horizons, compute budget, and 3–5 findings.
- `## 候选因子` — each candidate's name, family, formula, inputs, expected sign.
- `## 计算口径` — point-in-time rule, peer-median normalization, and report-caliber dedup.
- `## 有效性检验` — per-candidate rank IC, IC IR, IC decay, and turnover (a table).
- `## 排名` — top-K ranking with the ranking rule stated.
- `## 风险与口径提示` — sample window, lag, survivorship, currency, small-universe caveats.
- `## 数据说明` — source-interface table (which Pandadata method fed which step).
- The exact disclaimer line: 本报告基于公开数据与规则化分析生成，仅供研究参考，不构成任何投资建议。

Optionally validate a draft: `python scripts/validate_report.py <report.md>`.

## Data Sources

- **Pandadata overseas** via `skill-pandadata-api` — HK: `get_hk_daily`, `get_hk_detail`,
  `get_stock_operating_indicator`, `get_stock_mktfin_indicator`, `get_stock_industry_median`;
  US: `get_us_daily`, `get_us_detail`, `get_stock_operating_metric`, `get_stock_mktfin_metric`,
  `get_stock_sector_median`; calendar: `get_trade_cal(exchange=HK|US)`.
- **Optional public fallback**: Yahoo Finance daily bars, only for price/volume when a
  Pandadata pull is empty, clearly labeled as a third-party fallback source in the report.

## References

- `references/methodology.md` — candidate generation, point-in-time panels, IC / decay /
  turnover math, ranking rule, pitfalls, and graceful degradation.
- `references/pandadata-overseas-map.md` — HK↔US method routing and field notes; exact
  call contract still comes from `skill-pandadata-api`.
- `references/source_boundary.md` — what data this skill may and may not read.

## Boundaries

- Research and workflow tooling only; a community project, not official, certified, or verified.
- Discovery is **in-sample and descriptive**: IC / decay / turnover measure historical
  cross-sectional association, not future performance; no transaction cost, borrow, or
  capacity model is applied unless stated.
- State data source, universe, sample window, horizons, lag, survivorship handling, and
  currency for every run; HK and US are never mixed and currencies are never combined.
- External writes (saving reports, any publishing) require an explicit user trigger.
- 不构成任何投资建议 / does not constitute investment advice.
