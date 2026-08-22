# skill-factor-debug

[简体中文](./README.md) | [English](./README.en.md)

不是 IDE 调试器，而是**因子崩溃 / 失效 / 数值异常的诊断手册**：按"症状 → 候选病因 → 验证手段"组织的 9 类速查表，专治"因子跑挂"和"看似太好怀疑有 bug"。

`role: skill` `output: diagnostic playbook` `paradigm: cross-section research`


---

`skill-factor-debug` 是 PandaAI Quant Skills 提供的**因子排错 Skill**。因子跑挂 / 跑出来不对劲 / 怀疑有未来函数时，本 Skill 帮 AI Agent 按症状速查表对症下药，而不是盲改。

## 🎯 这个 Skill 解决什么问题

因子崩溃的原因 90% 是这五大类：

- 黑名单禁词命中（试图读未来数据）
- 信号校验失败（截面 mean / std / 全 NaN 占比）
- 未来函数潜入（IC 看似 0.20，实盘必崩）
- 数据 checksum mismatch（parquet 被改）
- 相关性 ≥ 0.85（新因子换皮）

每一类病因都有典型修复路径。本 Skill 提供 **9 类症状速查表** + **6 类经典未来函数模式** + **二分定位法**，让排错从"猜 → 改 → 再猜"变成"症状 → 病因 → 验证"。

## ⚡ 排错工作流

```
1. 看错误日志：cat journal/last_failed/run_XXXX_error.txt
2. 用症状速查表定位病因类型
3. 读对应 references 修复
4. 隔离最小复现：python -c "import alpha; alpha.run(...)"
5. 跑 smoke test → py runner.py once
```

报错不明确时，**二分定位**：把 FACTORS 减半反复跑，定位单个因子的问题。

## 🩺 9 类症状速查表

| 症状 | 病因 | references |
|---|---|---|
| `PermissionError: 黑名单` | alpha.py 含禁词 | `forbidden-tokens.md` |
| `ValueError: HORIZON not in (1,3,5,10,20)` | HORIZON 不在白名单 | `horizon-mismatch.md` |
| `ValueError: 截面 mean/std 不在阈值` | 信号未 z-score | `signal-validation.md` |
| `RuntimeError: checksum mismatch` | parquet 数据被改 | `data-integrity.md` |
| 信号通过校验但 IC > 0.20 | **未来函数** | `look-ahead-bias.md` |
| 回测全空仓 / Sharpe NaN | universe 错 / 涨跌停剔过狠 | `backtest-anomaly.md` |
| 因子相关性 > 0.85 | 新因子换皮 | `correlation-violation.md` |
| Sharpe 远 > IC_IR | close 当成交价 / 没扣手续费 / T+0 | `look-ahead-bias.md` |
| 同代码两次结果不同 | dict 顺序 / 浮点 reduction | `nondeterminism.md` |

## 🚨 危险信号清单

看到以下任一情况，**先怀疑未来函数**，不要相信结果：

- rank IC > 0.15
- 年化 > 50% 且 MDD < 5%
- Sharpe > 5
- Sharpe / IC_IR > 1.0
- val/train IC 比例 > 95%

真实因子的 val IC 应该比 train IC 低 30~70%。

## 📦 仓库内容

```
skill-factor-debug/
├── SKILL.md
├── README.md / README.en.md
├── references/
│   ├── forbidden-tokens.md             # 黑名单禁词清单 + 修复
│   ├── signal-validation.md            # 信号校验失败诊断
│   ├── horizon-mismatch.md             # HORIZON / LABEL_KIND 错配
│   ├── look-ahead-bias.md              # 6 类经典未来函数模式
│   ├── backtest-anomaly.md             # 回测异常 + 5 项体检
│   ├── correlation-violation.md        # 相关性过高 + 改设计 3 方向
│   ├── data-integrity.md               # checksum mismatch 处理
│   └── nondeterminism.md               # 不可复现 + 固定种子标准做法
└── agents/
    ├── openai.yaml
    ├── cursor-rule.mdc
    └── portable-loader.md
```

## 🚀 快速开始

把 `skill-factor-debug/` 放到 Agent 的 skill 目录下。触发词命中（"因子崩了 / CRASH / IC 突然超高怀疑 bug / debug factor"）时自动加载。

## 🔬 6 类经典未来函数模式（最危险）

1. 用 `close[T]` 当 T 日成交价（实际只能 T+1 开盘）
2. `fwd_ret = close.pct_change(h)`（backward，方向反了）
3. `fillna(method='bfill')`（用未来值填过去）
4. 在全段（train+val+test）拟合参数再 reapply
5. rolling 窗口包含当前（要 `.shift(1)`）
6. 用未来字段切子样本（如用 2026 市值切 2021）

详见 `references/look-ahead-bias.md`。

## 🧭 与 PandaAI Quant Skills 其它 Skill 的关系

| 仓库 | 用途 |
|---|---|
| skill-factor-mine | 正常迭代 |
| skill-factor-evaluate | 跑分（崩了进入 debug）|
| skill-backtest | 回测异常时进入 debug |
| skill-ic-analysis | IC 异常高时进入 debug |
| **skill-factor-debug**（本仓库）| 9 类症状速查表 |
| skill-factor-review | 整体复盘 |

## 📜 项目状态与边界

- **项目状态**：Community Project，未经官方审核 / 认证 / 背书
- **数据来源**：本仓库不附带任何市场数据。使用者需自行准备行情面板，数据合法性与许可由使用者负责
- **核心假设**：症状速查表针对的是"截面研究范式 + T+1 开盘成交 + 三段切分（train/val/test）+ 评估宪法锁定"的项目结构；其它范式需要自行映射
- **已知限制**：本 Skill 是诊断手册，不自动修复 —— 修复仍需人脑（或 Agent）按 references 改代码
- **风险边界**：诊断结论基于经验法则（如 "Sharpe / IC_IR > 1.0 几乎一定是 bug"），偶有合理因子超出阈值，最终判断仍需人类审阅
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
