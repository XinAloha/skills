---
name: ic-analysis
description: Use when an agent needs multidimensional IC diagnostics for a quantitative
  signal, including rank versus Pearson IC, IC decay, subsample IC, top-basket Jaccard
  stability, and cumulative IC timelines.
quantSkills:
  project_type: skill
  category: tooling
  tags:
  - ic-analysis
  - rank-ic
  - ic-decay
  - factor-diagnostics
  - quant-research
  platforms:
  - claude-code
  - codex
  - openclaw
  - cursor
  status: stable
  validation_level: listed
  maintainer_type: community
  summary_zh: 不是评分系统，而是IC 多维诊断 Skill：双 IC 对照 + IC 衰减曲线 + 子样本切片 + Top 篮 Jaccard + 时序累计图。回答"在哪类股票/什么周期上有效"。
  summary_en: Multidimensional IC diagnostics for rank versus Pearson IC, IC decay,
    subsample IC, top-basket stability, and cumulative IC timelines.
  license: GPL-3.0
---

```json qsh-form
{
  "version": 1,
  "task": {
    "placeholder": "补充信号/面板文件、样本区间或希望重点切分的维度（可选）"
  },
  "fields": [
    {
      "key": "factor",
      "label": "内置因子",
      "type": "select",
      "default": "momentum_20",
      "help": "填写自定义表达式时以表达式为准",
      "options": [
        { "value": "momentum_20", "label": "20日动量" },
        { "value": "reversal_5", "label": "5日反转" },
        { "value": "lowvol_20", "label": "20日低波动" },
        { "value": "alpha101_101", "label": "Alpha101 #101" },
        { "value": "alpha101_12", "label": "Alpha101 #12" },
        { "value": "corr_open_vol", "label": "量价背离" }
      ]
    },
    {
      "key": "expr",
      "label": "自定义因子表达式",
      "type": "textarea",
      "placeholder": "例如：-1 * correlation(rank(open), rank(volume), 10)"
    },
    {
      "key": "universe",
      "label": "股票池",
      "type": "select",
      "default": "000300.SH",
      "options": [
        { "value": "000300.SH", "label": "沪深300" },
        { "value": "000905.SH", "label": "中证500" },
        { "value": "399006.SZ", "label": "创业板指" },
        { "value": "000852.SH", "label": "中证1000" }
      ]
    },
    {
      "key": "horizon",
      "label": "主预测周期",
      "type": "select",
      "default": "5",
      "help": "报告仍应同时展示多周期 IC 衰减曲线",
      "options": [
        { "value": "1", "label": "未来1日" },
        { "value": "5", "label": "未来5日" },
        { "value": "10", "label": "未来10日" },
        { "value": "20", "label": "未来20日" }
      ]
    }
  ],
  "prompt_template": "{{#task}}任务与材料：\n{{task}}\n\n{{/task}}{{#attachments}}用户上传的材料（已放入工作区）：\n{{attachments}}\n\n{{/attachments}}诊断 {{universe}} 中因子 {{factor}}{{#expr}}（自定义表达式优先：{{expr}}）{{/expr}} 的 IC 表现，以 {{horizon}} 日为主周期，同时比较 Rank IC 与 Pearson IC、绘制 1/3/5/10/20/40/60 日衰减、按市值/波动/行业做子样本分析、计算 Top 10% Jaccard 稳定性与累计 IC 时序，输出中文报告。"
}
```

# IC Analysis

> 单个 IC_IR 数字告诉你"因子有没有效"，但不告诉你"在哪有效、能用多久、稳不稳"。本 skill 把 IC 拆成 4 个维度。

## 核心规则

1. **永远算双 IC**：rank IC 和 Pearson IC 对照（细则：`references/dual-ic.md`）
2. **算 IC decay 曲线**：H = 1/3/5/10/20/40/60，看信号衰减形态（细则：`references/ic-decay.md`）
3. **算子样本 IC**：按市值 / 波动 / 行业切，看在哪类股票上有效（细则：`references/subsample-ic.md`）
4. **算 Top 篮 Jaccard**：相邻日 Top 10% 重合度，衡量惯性 vs 噪声（细则：`references/top-basket-stability.md`）
5. **画 IC 时序图**：找崩溃点 / 平台期（细则：`references/ic-timeline.md`）

## 工作流

```
1. 双 IC 对照（基础健康检查）
2. IC decay 曲线（决定 horizon）
3. 子样本 IC（市值 / 波动 / 行业三维切）
4. Top 篮 Jaccard（看换手成本）
5. IC 时序累计图（找失效段）
6. 综合诊断报告
```

## 接口映射

| 本 skill 概念 | 你的项目对应 |
|---|---|
| `signal` | `[date × symbol]` 浮点 DataFrame |
| `panel` | 含 `open` / `close`（算 forward return）、市值代理（`close * volume` 累计也行）|
| 行业字段 | 如果有就用，没有则跳过子样本 §3 行业切片 |

## 按需加载

| 何时读 | 文件 |
|---|---|
| 双 IC 怎么对照 | `references/dual-ic.md` |
| 怎么画 decay 曲线 | `references/ic-decay.md` |
| 怎么按市值/波动/行业切 | `references/subsample-ic.md` |
| 算 Top 篮 Jaccard | `references/top-basket-stability.md` |
| 画 IC 时序图 | `references/ic-timeline.md` |
| 综合报告格式 | `references/report-format.md` |

## QA 检查清单

- [ ] 同时算了 rank IC 和 Pearson IC？
- [ ] 至少算了 5 个 horizon 的 IC（不是只一个）？
- [ ] 至少做了 1 个维度的子样本切分（市值优先）？
- [ ] 画了 IC 时序累计图？
- [ ] 报告里给了"信号在哪类股票上最有效"的结论？

## 跨工具适配

- OpenAI Codex / Assistants → `agents/openai.yaml`
- Cursor → `agents/cursor-rule.mdc`
- 无原生 skill 机制 → `agents/portable-loader.md`

---

## 项目边界（量化研究合规声明）

> 按 QUANTSKILLS 社区规则 §8 声明。

- **数据来源**：本 skill 不附带任何市场数据；使用者需自行准备行情面板（OHLCV / 涨跌停 / 停牌状态等），数据合法性与许可由使用者负责。
- **假设与参数**：默认假设见各 references（T+1 开盘成交、Top 10% 等权、双边 15bp 手续费、A 股涨跌停规则等）。这些是**研究阶段的标准化假设**，不等同于真实交易。
- **已知限制**：
  - 不模拟市场冲击、不模拟集合竞价滑点、不模拟券池融券约束
  - 不处理分红除权除息 / 配股 / 重大事件停牌的复杂情形
  - 默认 pooled cross-section 范式，对单股序列建模、时序模型不适用
- **风险边界**：本 skill 输出的因子分数 / 回测净值 / IC 诊断结果，**仅反映在历史数据 + 假设条件下的统计表现**，不代表未来表现。
- **用途定位**：**仅供量化研究、教育与方法论参考**。不构成任何形式的投资建议、交易信号或获利保证。使用者据此进行实盘交易的全部后果由使用者自负。
