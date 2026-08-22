# skill-factor-mine

[简体中文](./README.md) | [English](./README.en.md)

不是因子库，而是**因子挖掘的工作流 SOP**：把"加一个新因子"这件事拆成可重复、可归因、可回滚的标准动作。

`role: skill` `output: workflow` `paradigm: pooled cross-section`


---

`skill-factor-mine` 是 PandaAI Quant Skills 提供的**量化因子挖掘工作流 Skill**。它定义了一套通用 SOP：从读"评估宪法"、形成单点假设、写实验便签（ITER_NOTE）、改代码、跑分到接受/回滚，把因子挖掘从"灵感驱动"变成"协议驱动"。

QuantSkills 社区规则：参见组织根目录 `Community Rules`。

它**不是因子库**，也**不是回测引擎**，而是用于**继续生产因子库**的研究协议。如果你想要现成的因子，请到 PandaAI Quant Skills 的姊妹仓库里找；如果你想用一套有纪律的方式自己挖，请使用本 Skill。

## 🎯 这个 Skill 解决什么问题

当你（或你的 AI Agent）在迭代 `alpha.py` / `factors.py` / 任何因子文件时，最常见的失败模式是：

- **一次改了 N 个东西**：分数提升了，不知道是哪一项起作用，下次无法复用
- **没有假设就开干**：跑 100 轮全是噪声，没有学到任何东西
- **未来函数偷偷溜进来**：IC 漂亮但实盘必崩
- **新因子和老因子换皮**：相关性 0.9，加了等于没加，反而引入共线性

本 Skill 会自动施加：

- 单点假设原则（每轮只改一个 op_type）
- ITER_NOTE 强制四字段（`op_type` / `hypothesis` / `change` / `expected`）
- 截面 winsorize + z-score 信号契约
- 因子相关性门控 |ρ| ≥ 0.85
- 8 大因子族决策树（避免单族堆叠）
- 12 种反模式清单

让因子挖掘变成"提案 → 实验 → 接受 / 回滚 → 归档"的可审计循环。

## ⚡ 工作流

```
1. 读宪法（evaluation.md / program.md / 项目评分函数）
2. 读当前 alpha 全文
3. 形成单点假设 → 写 ITER_NOTE
4. 改代码（只改一个 op_type）
5. 跑评分（py runner.py once 或等价命令）
6. ACCEPTED → 自动归档因子卡
   REJECTED / CRASH → 自动回滚到上一最优 snapshot
```

## 🗃️ 输入要求

本 Skill 不要求特定数据格式，但你的项目至少要有：

- 行情面板（OHLCV，至少 `date / symbol / open / close / volume`）
- 评分函数（项目内的 `primary_score()` 或等价物）
- 实验日志机制（`runs.jsonl` / changelog / git log 都行）
- 单文件因子接口（`alpha.run(train, val) → (signal_train, signal_val)` 或类似）

如果项目还没这套基础设施，参考 `references/example-auto-alpha.md` 里 `auto_research_alpha` 的完整搭建方式。

## 📦 仓库内容

```
skill-factor-mine/
├── SKILL.md                            # Claude Code skill 入口
├── README.md / README.en.md            # 用户向介绍（本文件）
├── references/                         # 深度参考（Agent 按需加载）
│   ├── op-types.md                     # 8 种合法单点改动
│   ├── iter-note.md                    # 实验便签强制模板
│   ├── signal-contract.md              # 信号 winsorize + z-score 契约
│   ├── correlation-gate.md             # 相关性门控规则
│   ├── factor-families.md              # 8 大因子族 + 决策树
│   ├── anti-patterns.md                # 12 种反模式
│   └── example-auto-alpha.md           # 实战参考项目
└── agents/                             # 跨工具适配
    ├── openai.yaml                     # OpenAI Codex / Assistants
    ├── cursor-rule.mdc                 # Cursor 项目规则
    └── portable-loader.md              # 普通 ChatGPT / Claude Web
```

## 🚀 快速开始

### Claude Code（原生）

把整个 `skill-factor-mine/` 文件夹放到 `.claude/skills/` 或 `~/.claude/skills/` 下。当你说"加个新因子 / 挖一个 alpha / 迭代 alpha.py"时，Claude Code 会自动加载。

### Cursor

复制 `agents/cursor-rule.mdc` 到项目 `.cursor/rules/` 下。编辑 `alpha.py` 或 `factors/*.py` 时自动激活。

### OpenAI Codex / Assistants

把 `agents/openai.yaml` 的 `instructions` 字段灌入 system prompt 或 Assistant 配置。

### 普通 ChatGPT / Claude Web

打开 `agents/portable-loader.md`，把"激活提示"区块复制到对话开头。

## 🧪 ITER_NOTE 模板

每次改因子代码必填：

```python
ITER_NOTE: dict = {
    "op_type":    "add_factor",       # 见 references/op-types.md
    "hypothesis": "新增 amihud 流动性因子，与现有低波家族相关性低，应能补充信息。",
    "change":     "在 FACTORS 末尾加 f_amihud_20；其它不动。",
    "expected":   "score +0.35 → +0.40 左右；turnover 略升。",
    "parent_iter": 7,
    "reasoning":   "F0004 单调性 0.93 但 turnover=33 偏高。",
    "new_factor":  "f_amihud_20",
}
```

## 🧭 与 PandaAI Quant Skills 其它 Skill 的关系

| 仓库 | 用途 |
|---|---|
| **skill-factor-mine**（本仓库）| 提案与实验 SOP |
| skill-factor-evaluate | 给单个因子打综合分（双 IC / Sharpe / MDD / 单调性 / 换手） |
| skill-backtest | 截面多头回测 + 四联诊断图 |
| skill-ic-analysis | IC 多维诊断（衰减 / 子样本 / Jaccard / 时序）|
| skill-factor-debug | 因子崩溃 / 数值异常 / 未来函数自检 |
| skill-factor-review | 因子库复盘三层报告 |

典型工作流：mine → evaluate（自动调用）→ debug（崩了就用）→ ic-analysis（接受后深度诊断）。

## 📜 项目状态与边界

- **项目状态**：Community Project（社区项目），未经官方审核 / 认证 / 背书
- **数据来源**：本仓库不附带任何市场数据。使用者需自行准备行情面板，数据合法性与许可由使用者负责
- **核心假设**：截面研究范式（pooled cross-section）；HORIZON ∈ (1, 3, 5, 10, 20)；T+1 开盘成交
- **已知限制**：不模拟市场冲击 / 集合竞价滑点 / 券池融券约束；不处理分红除权除息复杂情形
- **风险边界**：因子分数仅反映在历史数据 + 假设条件下的统计表现，不代表未来表现
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
