---
name: factor-review
description: Use when an agent needs to review an existing factor library, summarize
  experiment logs, quantify acceptance rates and score dynamics, analyze factor families
  and correlations, and recommend the next research direction.
quantSkills:
  project_type: skill
  category: tooling
  tags:
  - factor-review
  - factor-library
  - research-review
  - correlation
  - workflow
  platforms:
  - claude-code
  - codex
  - openclaw
  - cursor
  status: stable
  validation_level: listed
  maintainer_type: community
  summary_zh: 不是单因子评价，而是因子库整体复盘 Skill：扫描实验日志 + 因子卡，输出三层报告（量化盘点 + 结构分析 + 研究建议），回答"已经做了什么、最优在哪、下一步该挖什么"。
  summary_en: Factor-library review skill for experiment logs, acceptance rates, score
    dynamics, factor-family structure, correlations, and research recommendations.
  license: GPL-3.0
---

```json qsh-form
{
  "version": 1,
  "task": {
    "placeholder": "请给出因子库/实验日志位置（如 runs.jsonl、因子卡目录）",
    "required": true
  },
  "fields": [],
  "prompt_template": "{{#task}}任务与材料：\n{{task}}\n\n{{/task}}{{#attachments}}用户上传的材料（已放入工作区）：\n{{attachments}}\n\n{{/attachments}}复盘任务材料中给出的因子库与实验日志，依次完成接受率与分数轨迹的量化盘点、因子族与相关性结构分析、下一步研究建议；每项建议写明 op_type、具体改动和预期分数，输出中文报告。"
}
```

# Factor Review

> 跑了 N 轮迭代之后，到了"停下来想想"的时候。本 skill 把因子库 + 实验日志做一次系统性复盘，回答三个问题：**已经做了什么、最优在哪、下一步该挖什么**。

## 核心规则

1. **复盘三层结构**：量化盘点 → 结构分析 → 研究建议（顺序不能乱）
2. **必有可执行建议**：建议必须包含 op_type + 具体改动 + 预期分数
3. **足够数据量再复盘**：少于 10 因子 / 30 迭代复盘没意义
4. **不要只夸最优因子**：要找盲区和同质化

## 三层报告结构

```
Layer 1: 量化盘点 — 跑了多少轮、接受率、分数轨迹（细则：references/quantitative-stats.md）
Layer 2: 结构分析 — 因子族分布、相关性矩阵、最优路径（细则：references/structural-analysis.md）
Layer 3: 研究建议 — 下一步该试什么、该停什么（细则：references/research-recommendations.md）
```

## 工作流

```
1. 扫描 runs.jsonl / INDEX.md / factor cards → 得到原始数据
2. Layer 1：算接受率、CRASH 率、分数轨迹、提分动力学
3. Layer 2：因子族归类、相关性矩阵、回溯最优路径的关键决策
4. Layer 3：基于 Layer 2 的发现给 3~5 个具体下一步假设
5. 输出标准报告（references/report-template.md）
```

## 接口映射

| 概念 | 你的项目对应 |
|---|---|
| 实验日志 | `journal/runs.jsonl` / `experiments.jsonl` / git log |
| 因子库索引 | `factor_library/INDEX.md` / `models/registry.json` |
| 因子卡 | `factor_library/<id>/card.json` |
| best 标记 | `journal/best.json` / 当前 alpha.py |

**最低要求**：项目里至少要有"实验日志"（哪怕是 markdown 列表）才能复盘。否则先建机制再回头。

## 按需加载

| 何时读 | 文件 |
|---|---|
| Layer 1 怎么算指标 | `references/quantitative-stats.md` |
| Layer 2 怎么做结构分析 | `references/structural-analysis.md` |
| Layer 3 建议格式 | `references/research-recommendations.md` |
| 标准报告模板 | `references/report-template.md` |
| 复盘反模式 | `references/anti-patterns.md` |

## QA 检查清单

- [ ] Layer 1 给了接受率和 CRASH 率？
- [ ] Layer 1 画了分数轨迹（best 演进）？
- [ ] Layer 2 列出了当前因子的族分布？
- [ ] Layer 2 算了相关性矩阵？
- [ ] Layer 3 至少给了 3 个具体假设（含 op_type + 预期）？
- [ ] Layer 3 假设有优先级排序？
- [ ] 提到了风险预警（同质化 / 边际收益递减 / 风格集中）？

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
