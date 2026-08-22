# 因子砌墙师

**简体中文** | [English](README.en.md)

> 单因子权益研究的质量控制技能：从股票池、时点对齐、IC/IR、换手、成本和中性化出发，判断一个因子到底是 alpha、行业暴露、数据泄漏，还是样本幻觉。

![type](https://img.shields.io/badge/type-alpha--research-blue)
![domain](https://img.shields.io/badge/domain-equity--factor-teal)
![license](https://img.shields.io/badge/license-GPLv3-blue)

---

## 这是什么

因子砌墙师不是“帮你找一个神奇因子”的技能，而是一个**把因子研究从灵感拉回工程纪律**的工作流。它适用于 A 股、港股、美股等权益市场中的横截面选股研究，尤其适合处理那些看起来很漂亮、但可能被未来函数、停牌样本、行业偏置或交易成本撑起来的因子。

这个技能默认把单因子研究拆成三层：

1. **信号层**：因子定义是否有经济含义，是否可在交易时点获得
2. **样本层**：股票池、停牌、退市、ST、流动性和行业结构是否扭曲结果
3. **交易层**：换手、成本、延迟和暴露控制后，因子是否仍然可用

## 项目状态与研究边界

| 项目项 | 说明 |
| --- | --- |
| 项目状态 | Community Project；尚未获得 QUANTSKILLS 的审核、认证或背书 |
| 维护者 | 本仓库维护者及贡献者 |
| 数据来源 | 使用者提供或指定的行情、财务披露、公司行为、指数成分和行业分类数据 |
| 核心假设 | 信息可得时点、股票池历史口径、交易滞后和成本模型与真实研究环境一致 |
| 已知限制 | 数据修订、停牌、退市、成分调整、借券可得性和成本估计会改变结果 |
| 风险边界 | 仅用于研究与教育示例；不自动获取数据、不执行交易，结论需结合原始数据独立复核 |

## 核心逻辑

```text
raw_factor        = 用户定义的原始信号
tradable_factor   = lag(raw_factor, 可交易滞后)
clean_factor      = winsorize/standardize/filter(tradable_factor)
ic_series         = corr(rank(clean_factor_t), future_return_t+h)
long_short_return = top_quantile_return - bottom_quantile_return
net_return        = gross_return - turnover_cost - slippage - spread_cost
usable_alpha      = 样本外稳定 + 成本后可用 + 暴露可解释
```

## 适用场景

- 单因子回测设计
- IC、Rank IC、ICIR 分析
- 因子中性化和暴露归因
- 行业、市值、beta、波动率等风险控制
- A 股停牌、ST、涨跌停和退市样本处理
- 回测结果过好、突然失效或成本后崩塌的排查

## 快速开始

```bash
# 校验测试用例
python3 scripts/check_test_cases.py

# 查看研究手册
sed -n '1,220p' references/playbook.md

# 查看测试用例
sed -n '1,220p' references/test-cases.md
```

### 推荐调用方式

```text
使用 $factor-mason 分析一个 20 日反转因子。股票池是沪深 300，月度调仓，要求检查未来函数、停牌样本、换手成本和行业中性化后的表现。
```

## 参数说明

| 参数 | 必填 | 说明 | 建议 |
| --- | --- | --- | --- |
| 股票池 | 是 | 市场、指数、行业、流动性范围 | 不要用事后成分股 |
| 因子定义 | 是 | 原始信号公式、字段来源、更新时间 | 先写成可审计表达式 |
| 标签周期 | 是 | 未来收益的计算窗口 | 与交易假设一致 |
| 调仓频率 | 是 | 日频、周频、月频等 | 与因子半衰期匹配 |
| 滞后规则 | 是 | 信号何时变成可交易信息 | 至少滞后一根可执行 bar |
| 成本模型 | 是 | 费率、滑点、买卖价差、借券成本 | 优先保守 |
| 中性化维度 | 否 | 行业、市值、beta、风格 | 只在符合因子逻辑时使用 |
| 样本切分 | 否 | 样本内、样本外、滚动窗口 | 避免只看全样本平均 |

## 输出结果

| 输出 | 说明 |
| --- | --- |
| 信号逻辑 | 因子为什么可能有效，以及它最可能捕捉什么行为 |
| 回测设计 | 股票池、时点对齐、调仓、成本和组合构建 |
| 诊断指标 | IC、Rank IC、ICIR、多空收益、换手、回撤和衰减 |
| 风险归因 | 行业、市值、beta、波动率和流动性暴露 |
| 失效判断 | 泄漏、拥挤、成本、状态依赖或定义错误 |
| 下一步实验 | 更稳的验证路径，而不是空泛建议 |

## 目录结构

```text
skill-factor-mason/
├── SKILL.md
├── README.md
├── README.en.md
├── scripts/
│   └── check_test_cases.py
├── references/
│   ├── playbook.md
│   └── test-cases.md
├── assets/
│   └── factor-mason.svg
├── agents/
│   ├── openai.yaml
│   ├── claude-code.md
│   ├── cursor-rule.mdc
│   ├── portable-loader.md
│   └── openclaw.md
├── metadata.yaml
└── LICENSE
```

## 运行时入口

| 运行时 | 入口 | 用法 |
| --- | --- | --- |
| Codex | `agents/openai.yaml` + `SKILL.md` | 通过技能名称触发 |
| Claude Code | `agents/claude-code.md` | 读取入口后加载 `SKILL.md` |
| Cursor | `agents/cursor-rule.mdc` | 将规则复制到项目 `.cursor/rules/` |
| Hermes | `agents/portable-loader.md` | 按便携入口加载核心说明 |
| OpenClaw | `agents/openclaw.md` | 按入口加载核心说明 |

许可元数据见 `metadata.yaml`，SPDX 标识为 `GPL-3.0-only`。

## 核心约束

| 约束 | 说明 |
| --- | --- |
| 不接受未来函数 | 信息披露、交易可得性和成交时点必须对齐 |
| 不迷信毛收益 | 高换手策略必须看成本后结果 |
| 不把暴露当 alpha | 行业、市值或 beta 暴露需要拆开 |
| 不用全样本自嗨 | 必须看样本外、滚动窗口或状态切片 |
| 不输出执行指令 | 输出研究结构、风险假设与可复核证据 |

## 测试用例

测试用例位于 [references/test-cases.md](references/test-cases.md)，覆盖：

- 泄漏陷阱
- 停牌样本
- 成本吃掉优势
- 中性化选择
- 状态破裂
- 空头现实性

运行：

```bash
python3 scripts/check_test_cases.py
```

## 免责声明

本项目用于量化研究流程整理与技能封装。研究结论应结合真实行情、财务数据和交易约束独立复核。
