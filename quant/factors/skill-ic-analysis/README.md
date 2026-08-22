# skill-ic-analysis

[简体中文](./README.md) | [English](./README.en.md)

不是评分系统，而是**IC 多维诊断 Skill**：双 IC 对照 + IC 衰减曲线 + 子样本切片 + Top 篮 Jaccard + 时序累计图。回答"在哪类股票/什么周期上有效"。

`role: skill` `output: 5-section diagnostic report` `paradigm: pooled cross-section`


---

`skill-ic-analysis` 是 PandaAI Quant Skills 提供的 **IC 多维诊断 Skill**。单个 IC_IR 数字告诉你"因子有没有效"，但不告诉你"在哪有效、能用多久、稳不稳"。本 Skill 把 IC 拆成 5 个维度看。

## 🎯 这个 Skill 解决什么问题

整体 IC = 0.04 可能是：

- 小票 IC=0.08、大票 IC=0（容量受限）
- 高波 IC=0.07、低波 IC=0.01（吃风险溢价）
- H=1 IC=0.01、H=20 IC=0.05（低频信号）
- 2020 年 IC=0.10、2023 年 IC=-0.02（regime shift）
- Jaccard < 0.5（信号噪声主导，年化换手 100+）

这些信息**整体 IC 一个数字看不到**。本 Skill 强制 5 项分析全做，并给出综合判读。

## ⚡ 5 项分析

```
1. 双 IC 对照（rank vs Pearson） — 基础健康检查
2. IC decay 曲线（H=1/3/5/10/20/40/60） — 决定 horizon
3. 子样本 IC（市值 / 波动 / 行业三维切） — 看在哪类股票上有效
4. Top 篮 Jaccard — 信号惯性 vs 噪声
5. IC 时序累计图 — 找崩溃点 / 平台期 / regime shift
6. 综合判读 — 因子类型 / 推荐 H / 实盘风险 / 后续动作
```

## 🗃️ 输入要求

- 信号：`[date × symbol]` 浮点 DataFrame
- 行情面板：含 `open` / `close`（算 forward return）、市值代理（`close * volume` 累计也行）
- 行业字段（可选）：有则做行业切片，无则跳过

## 📦 仓库内容

```
skill-ic-analysis/
├── SKILL.md
├── README.md / README.en.md
├── references/
│   ├── dual-ic.md                      # rank vs Pearson 对照
│   ├── ic-decay.md                     # 衰减曲线 + 形态分类
│   ├── subsample-ic.md                 # 市值/波动/行业切片
│   ├── top-basket-stability.md         # Jaccard 算法 + 解读表
│   ├── ic-timeline.md                  # 时序图 + regime shift 检测
│   └── report-format.md                # 综合诊断报告模板
└── agents/
    ├── openai.yaml
    ├── cursor-rule.mdc
    └── portable-loader.md
```

## 🚀 快速开始

把 `skill-ic-analysis/` 放到 Agent 的 skill 目录下。触发词命中（"IC 衰减 / IC decay / 子样本 IC / 信号稳不稳"）时自动加载。

## 📄 综合报告样板

```
=== IC Analysis Report ===
Factor      : f_neg_max_ret_120
Period      : 2021-12-04 → 2024-12-03 (val)

[1] 双 IC 对照
    rank IC mean    : +0.038       rank_ic_ir   : 2.14
    pearson IC mean : +0.029       pearson_ic_ir: 1.87
    诊断            : 量级稍失真，rank > pearson by 30%

[2] IC Decay
    H=1   ic=0.012  ir=1.05
    H=20  ic=0.038  ir=2.14   ← 当前 horizon
    H=40  ic=0.029  ir=1.74
    诊断  : 中频信号（H=20 峰值），适合 H ∈ [10, 20]

[3] 子样本 IC（按市值）
    Q1 (smallest) : ic=0.062     ← 主导
    Q5 (largest)  : ic=0.011
    诊断  : 小票主导，实盘容量受限

[4] Top 10% Jaccard
    mean=0.91  std=0.03
    诊断  : 信号变化慢，换手低

[5] IC 时序: 一路上扬，无明显失效段

=== 综合判读 ===
- 因子类型 : 中频 lottery，主要在小盘高波股上有效
- 推荐 H   : 20
- 实盘风险 : 容量受限（小盘流动性），高波股集中（MDD 偏深）
- 后续动作 : 加低波因子做对冲（op_type=combine_method）
```

## 🧭 与 PandaAI Quant Skills 其它 Skill 的关系

| 仓库 | 用途 |
|---|---|
| skill-factor-mine | 提案改代码 |
| skill-factor-evaluate | 给一个综合分（含简化 IC 算法）|
| skill-backtest | 净值 / 分组 / benchmark |
| **skill-ic-analysis**（本仓库）| IC 多维诊断（不画净值）|
| skill-factor-debug | IC 异常高时怀疑 bug |
| skill-factor-review | 库级别复盘 |

## 📜 项目状态与边界

- **项目状态**：Community Project，未经官方审核 / 认证 / 背书
- **数据来源**：本仓库不附带任何市场数据。使用者需自行准备行情面板，数据合法性与许可由使用者负责
- **核心假设**：截面研究范式（pooled cross-section）；forward return 用 `open.shift(-1).pct_change(H).shift(-H)`
- **已知限制**：子样本切分需要使用过去信息（不可用未来市值切过去）；对超低频因子（H > 60）IC decay 量级可能噪声很大
- **风险边界**：IC 诊断仅反映在历史数据 + 假设条件下的统计表现，不代表未来表现
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
