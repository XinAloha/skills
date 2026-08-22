---
name: factor-mine
description: Use when an agent needs a disciplined quantitative factor mining workflow
  for forming one hypothesis at a time, implementing a factor, running validation,
  recording iteration notes, accepting improvements, or rolling back weak experiments.
quantSkills:
  project_type: skill
  category: tooling
  tags:
  - factor-mining
  - alpha-research
  - workflow
  - iteration
  - validation
  platforms:
  - claude-code
  - codex
  - openclaw
  - cursor
  status: stable
  validation_level: listed
  maintainer_type: community
  summary_zh: 不是因子库，而是因子挖掘的工作流 SOP：把"加一个新因子"这件事拆成可重复、可归因、可回滚的标准动作。
  summary_en: Disciplined factor-mining workflow for hypothesis design, implementation,
    validation, iteration notes, acceptance, and rollback decisions.
  license: GPL-3.0
---

```json qsh-form
{
  "version": 1,
  "task": {
    "placeholder": "补充经济假设、现有因子库、评分规则或项目命令（可选）"
  },
  "fields": [
    {
      "key": "factor",
      "label": "起始因子",
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
      "placeholder": "可填已有表达式，作为单点改进的起点"
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
      "label": "预测周期",
      "type": "select",
      "default": "5",
      "options": [
        { "value": "1", "label": "未来1日" },
        { "value": "5", "label": "未来5日" },
        { "value": "10", "label": "未来10日" }
      ]
    }
  ],
  "prompt_template": "{{#task}}任务与材料：\n{{task}}\n\n{{/task}}{{#attachments}}用户上传的材料（已放入工作区）：\n{{attachments}}\n\n{{/attachments}}围绕 {{universe}}、{{horizon}} 日预测周期，从因子 {{factor}}{{#expr}}（自定义起点：{{expr}}）{{/expr}} 开展一次只改变一个 op_type 的因子挖掘迭代；先读取项目评分与研究规范，写完整 ITER_NOTE，校验信号契约和相关性门槛，根据验证结果接受或回滚，输出中文报告。"
}
```

# Factor Mine

> 量化因子挖掘工作流。截面 / 时序皆可，本 skill 默认 **pooled cross-section** 范式。

## 核心规则

1. **单点假设原则**：每轮只改一件事（见 `references/op-types.md`）
2. **必先读宪法**：项目内 `evaluation.md` / `program.md` 是"评分公式"和"研究方向"的唯一真理来源 —— 没读就不许提假设
3. **ITER_NOTE 强制**：`op_type / hypothesis / change / expected` 四字段必填，缺一不跑（模板：`references/iter-note.md`）
4. **信号契约**：返回信号必须截面 winsorize + z-score（细则：`references/signal-contract.md`）
5. **相关性门控**：新因子与任一已有因子 |ρ| ≥ 0.85 → 直接拒（细则：`references/correlation-gate.md`）

## 工作流（每轮 5 步）

```
1. 读宪法 + 当前 alpha 全文
2. 形成单点假设 → 写 ITER_NOTE
3. 改代码（≤ 一个 op_type）
4. 跑 runner.once → 看 score 升降
5. ACCEPTED 自动归档；REJECTED / CRASH 自动回滚
```

## 接口映射（跨项目适配）

把本 skill 用到非 `auto_research_alpha` 的项目时，先确认 5 个映射：

| 本 skill 概念 | 你的项目对应（请用户确认） |
|---|---|
| 主分公式 | `evaluation.md` / `score()` / 评估函数 |
| 单点假设记录 | `ITER_NOTE` / commit message / changelog |
| 信号契约 | 你的 `validate_signal()` / 信号 schema |
| 实验循环命令 | `py runner.py once` / `python train.py` / 自定义 |
| 因子库目录 | `factor_library/` / `models/` / `experiments/` |

**确认不了 → 先问用户，再开始挖。**

## 按需加载（references/）

| 何时读 | 文件 |
|---|---|
| 准备改代码、不确定单点假设范围 | `references/op-types.md` |
| 写 ITER_NOTE 不知道字段含义 | `references/iter-note.md` |
| 信号校验失败 / 算 IC 前 | `references/signal-contract.md` |
| 想知道挖什么因子族 / 已有族分布 | `references/factor-families.md` |
| 看反模式清单（避免常见坑） | `references/anti-patterns.md` |
| 项目级实战示例 | `references/example-auto-alpha.md` |

## QA 检查清单（提交前）

- [ ] 只改了一件事（一个 op_type）？
- [ ] ITER_NOTE 四个必填字段都有内容？
- [ ] hypothesis 有具体经济/统计含义，不是"试试看"？
- [ ] 新因子与已有因子相关性 < 0.6？
- [ ] expected 给了具体分数区间（不是"提升"）？

## 跨工具适配

- OpenAI Codex / Assistants → `agents/openai.yaml`
- Cursor → `agents/cursor-rule.mdc`
- 无原生 skill 机制的 Agent → `agents/portable-loader.md`

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
