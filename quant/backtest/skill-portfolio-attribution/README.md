# skill-portfolio-attribution

**简体中文** | [English](README.en.md)

组合绩效归因 Skill：把组合相对基准的主动收益分解为行业配置、个股选择、交互效应与因子贡献，回答量化投资中回测之后的下一个问题——这笔超额收益到底赚在哪。

<p align="center">
  <img alt="role" src="https://img.shields.io/badge/role-组合绩效归因-brightgreen">
  <img alt="output" src="https://img.shields.io/badge/output-Brinson·Carino·因子·txt%2Fjson%2FHTML-blue">
  <img alt="validation" src="https://img.shields.io/badge/validation-13%2F13恒等式与护栏-orange">
  <img alt="data" src="https://img.shields.io/badge/data-框架中立-9cf">
  <img alt="license" src="https://img.shields.io/badge/license-GPLv3-blue">
</p>

`skill-portfolio-attribution` 是 QuantSkills 社区的组合绩效归因 Skill。社区因子生态已覆盖挖掘、评估、衰减、合成、回测——本 Skill 补上信号变成组合之后缺失的一环：归因。

QuantSkills GitHub 组织：https://github.com/quantskills

## 这个 Skill 解决什么问题

回测报告告诉你组合年化超额 8%，但不会告诉你这 8% 来自哪里：是超配了对的行业，还是在行业内选对了股票，或是押中了动量、价值这类因子。归因把主动收益按来源精确拆开，各项加总严格等于区间主动收益。

本 Skill 提供两层归因：

- **Brinson-Fachler 行业归因**：把主动收益拆为配置、选股、交互三项，Carino 多期几何链接使逐期效应跨期可加
- **因子归因**：逐期横截面回归估计因子收益，主动暴露 × 因子收益得因子贡献，残差为特质（选股）收益

两个面板对同一区间主动收益——因子归因与行业归因共用 Carino 缩放口径，因此因子面板合计恒等于行业面板合计，恒等于区间主动收益。

## 归因是少数能自证算对的量化工具

归因各项加总必须精确等于主动收益，这一恒等式内建为运行时断言：算不平即拒绝出报告。输入校验同样严格，不符合直接报错而非静默处理：

- **权重加总守卫**：每日权重加总偏离 1 超过 1e-4 报错，不静默归一化
- **重复主键守卫**：权重/收益表出现重复 `(date, symbol)` 报错，避免 merge 时重复计权导致错误归因
- **零权重行业防护**：某行业在组合与基准中权重均为 0 时效应恒为 0，不产生 NaN 混入报告
- **可证伪**：`scripts/validate.py` 用合成数据验证 13 项恒等式与护栏，包括"因子面板与行业面板对同一区间主动收益"，全部通过

## 快速开始

```bash
pip install -r requirements.txt

# 自检（13 项恒等式与护栏）
python scripts/validate.py

# 端到端示例（合成组合，输出行业 + 因子归因）
python examples/run_example.py

# 用你自己的数据
python scripts/attribution.py \
  --portfolio p.csv --benchmark b.csv --returns r.csv --sectors s.csv \
  --exposures e.csv --out report/
```

示例输出（合成组合，故意超配半导体、低配银行）：

```
区间主动收益 = +0.0599%

Brinson-Fachler 行业归因
            组合权重    基准权重    配置      选股      交互      合计
半导体      41.25%    30.00%   +0.05%  +0.02%  +0.01%  +0.09%
银行        23.92%    35.00%   -0.00%  +0.04%  -0.01%  +0.02%
合计: 配置 +0.05% | 选股 +0.01% | 交互 -0.00% | 总计 +0.06%

因子归因（与行业归因对同一区间主动收益）
  mom        -0.16%
  value      +0.02%
  特质/选股   +0.20%
  合计        +0.06%
```

配置为正说明超配的半导体跑赢了基准；两个面板的合计都是 +0.06%，对上同一总账。

## 输入：只需提供「持仓」

唯一需要提供的是**每日持仓**（来自任意回测、券商对账单或实盘账户，任何平台皆可）：

```
date, symbol, weight        # 或给 market_value，由 Agent 换算权重
20240102, 600519.SH, 0.20
20240102, CASH,       0.05  # 现金记一行，否则会漏掉现金拖累
```

其余三张由 Agent 从**公开数据**自动补齐：

- **个股收益** ← 公开前复权行情（akshare `qfq` / Pandadata），`close/pre_close` 即干净日收益
- **行业分类** ← 公开行业分类
- **基准（默认：持股等权）** ← 由持仓生成，把你持有的股等权作基准。只需持仓本身、能完全对账、无停牌/成分/前视偏差噪声。可选「vs 沪深300/上证指数」需干净的指数成分数据（裸重建有前视偏差，须用 point-in-time 成分）

**安全边界**：本 skill 不含任何数据库连接/适配器，只吃"持仓 + 公开数据"，绝不接入使用方私有库。把回测持仓导出成文件，是平台的职责。

## 目录结构

```
skill-portfolio-attribution/
├── SKILL.md                    # Agent 使用说明（含 frontmatter）
├── README.md / README.en.md
├── agents/
│   ├── openai.yaml              # OpenAI-style runtime manifest
│   ├── cursor-rule.mdc          # Cursor rule entrypoint
│   └── portable-loader.md       # Hermes/OpenClaw portable loader
├── scripts/
│   ├── attribution.py          # Brinson + Carino + 因子归因 + 报告
│   └── validate.py             # 13 项恒等式与护栏自检
├── references/
│   └── methodology.md          # 方法论与公式
└── examples/
    ├── run_example.py
    ├── data/                   # 合成输入
    └── output/                 # 归因报告示例（txt + json + html）
```

## 运行时入口

本 Skill 支持 Claude Code、Codex、Cursor、Hermes 和 OpenClaw。Claude Code、Codex 与原生 Skill 运行时直接加载 `SKILL.md`；Cursor 使用 `agents/cursor-rule.mdc`；Hermes/OpenClaw 在无法原生发现 Skill 时使用 `agents/portable-loader.md`。所有入口最终都回到同一份 `SKILL.md`、方法论和归因脚本，不维护平行业务逻辑。

## 边界与不做的事

- 假设组合每期按给定权重再平衡；期内交易、费用不在 v1 范围
- 现金在持仓里记 `CASH` 行即计入现金拖累/贡献；不记则漏掉
- 因子收益用 OLS 估计，未做行业中性化与加权回归（计划 v2）
- **不含数据库适配器**：只吃"持仓 + 公开数据"，不接入任何私有库
- 收益护栏只告警不改数据；复权、剔脏值是取数环节的职责，非归因引擎

## License

GPL-3.0。本 Skill 为 QuantSkills 社区原创，Brinson-Fachler 与 Carino 链接为组合归因通用方法。
