# skill-factor-review

[简体中文](./README.md) | [English](./README.en.md)

不是单因子评价，而是**因子库整体复盘 Skill**：扫描实验日志 + 因子卡，输出三层报告（量化盘点 + 结构分析 + 研究建议），回答"已经做了什么、最优在哪、下一步该挖什么"。

`role: skill` `output: 3-layer review report` `paradigm: library-level review`


---

`skill-factor-review` 是 PandaAI Quant Skills 提供的**因子库复盘 Skill**。跑了 N 轮迭代之后到了"停下来想想"的时候，本 Skill 把因子库 + 实验日志做一次系统性复盘，给出可执行的下一步研究建议。

## 🎯 这个 Skill 解决什么问题

跑了 50+ 轮、20+ 因子之后常见的状况：

- 不知道从哪里继续挖（盲目加新因子）
- 因子库已经有 30% 同质化但没人察觉
- 边际收益已递减到 +0.002/轮 但还在硬挖
- 想做阶段验收但没有可比数据
- 想写研究报告但没有结构化输出

本 Skill 强制三层结构：

1. **量化盘点** — 接受率 / CRASH 率 / 分数轨迹 / 提分动力学
2. **结构分析** — 因子族分布 / 相关性矩阵 / 最优路径回溯
3. **研究建议** — 3~5 个具体假设（含 op_type + 理由 + 预期 score）+ 风险预警

## ⚡ 复盘流程

```
1. 扫描 runs.jsonl / INDEX.md / 因子卡 → 原始数据
2. Layer 1：算接受率、CRASH 率、分数轨迹、提分动力学曲线
3. Layer 2：因子族归类、相关性矩阵、回溯最优路径关键决策
4. Layer 3：基于 Layer 2 的发现给 3~5 个具体下一步假设
5. 输出标准报告 + 配图
```

## 🗃️ 输入要求

- 实验日志：`runs.jsonl` / `experiments.jsonl` / git log（哪种都行）
- 因子库索引：`INDEX.md` / `models/registry.json`
- 因子卡：每个因子有 `card.json` 含 score、metrics
- best 标记：`best.json` 或当前 alpha.py

**最低要求**：≥ 30 轮实验、≥ 10 因子才有复盘价值。少于此量级直接看 `runner status`，不要复盘。

## 📦 仓库内容

```
skill-factor-review/
├── SKILL.md
├── README.md / README.en.md
├── references/
│   ├── quantitative-stats.md           # Layer 1 怎么算
│   ├── structural-analysis.md          # Layer 2 三个子分析
│   ├── research-recommendations.md     # Layer 3 假设格式
│   ├── report-template.md              # 标准报告模板
│   └── anti-patterns.md                # 12 种反模式
└── agents/
    ├── openai.yaml
    ├── cursor-rule.mdc
    └── portable-loader.md
```

## 🚀 快速开始

把 `skill-factor-review/` 放到 Agent 的 skill 目录下。触发词命中（"复盘因子库 / 看看跑过哪些 / 下一步挖什么 / 阶段验收"）时自动加载。

## 📄 报告样板

```markdown
# Factor Library Review — 2026-06-12

## Layer 1: 量化盘点
- 总实验 67, 接受率 34%, CRASHED 6
- 分数 +0.05 → +0.63（5 次大跳跃 + 30+ 次微调）
- 提分动力学：边际收益已递减到 +0.002/轮

## Layer 2: 结构分析
- 当前 FACTORS: [size_inv, max_ret_120, vol_cv_120]
- 因子族覆盖：流动性 1 / lottery 1 / 量能 1，反转/动量/波动率全空
- 相关性矩阵：mean |ρ| = 0.43 (中等)
- 最优路径：4 次大跳跃来自换族 / 换 horizon

## Layer 3: 下一步建议（含优先级）
1. [add_factor] f_reversal_5         预期 +0.03 ~ +0.07
2. [horizon]    试 H=10              预期 +0.03 ~ +0.06（来自换手降低）
3. [combine_method] Ridge α=10       预期 ±0.05
4. [label_kind] vol_adjusted         高方差实验，最后做

## 风险预警
- 因子库偏 "lottery + 流动性"，市场风格切换时可能整体崩
- 67 轮已接近"无脑挖"边际，建议进入 Phase 2 或换更复杂模型
```

## 🧭 与 PandaAI Quant Skills 其它 Skill 的关系

| 仓库 | 用途 |
|---|---|
| skill-factor-mine | 单轮迭代 |
| skill-factor-evaluate | 单因子评分 |
| skill-backtest | 单因子回测 |
| skill-ic-analysis | 单因子深度诊断 |
| skill-factor-debug | 单次崩溃排错 |
| **skill-factor-review**（本仓库）| 库级别复盘 |

复盘的产出会反哺 skill-factor-mine 的下一轮假设设计。

## 📜 项目状态与边界

- **项目状态**：Community Project，未经官方审核 / 认证 / 背书
- **数据来源**：本仓库不附带任何市场数据。使用者需自行准备行情面板和实验日志，数据合法性与许可由使用者负责
- **核心假设**：项目使用三段冻结切分（train / val / test），test 段严格不可见；评估宪法已锁定（`primary_score()` 不可改）
- **已知限制**：复盘建议基于历史实验数据，对"行情风格切换"等结构性变化的预测能力有限；Layer 3 给出的假设仍需人脑评估而非自动执行
- **风险边界**：复盘结论仅反映在历史数据 + 假设条件下的统计趋势，不代表未来表现
- **用途**：仅供量化研究、教育与方法论参考。**不构成任何形式的投资建议、交易信号或获利保证**

## 📜 License

This repository is licensed under the GNU General Public License v3.0. See LICENSE.

Copyright (C) 2026 QuantSkills.

## 🐼 PandaAI / QUANTSKILLS 社群

<div align="center">
  <img src="https://raw.githubusercontent.com/quantskills/.github/main/profile/assets/pandaai-community-qr.jpg" alt="PandaAI 社群二维码" width="220">
  <br>
  <sub>扫码加入 PandaAI 社群，交流 QUANTSKILLS 技能、Agent 工作流与量化研究实践。</sub>
</div>
