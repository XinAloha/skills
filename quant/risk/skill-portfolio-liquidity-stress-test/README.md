# 组合流动性压力测试

> 在成交量萎缩和赎回压力下计算清算天数、冲击成本与组合可变现比例。

## 解决什么问题

在成交量萎缩和赎回压力下计算清算天数、冲击成本与组合可变现比例。

能力边界：本模型只做流动性情景分析，不等同于监管分类，也不保证真实成交。

## 快速开始

```bash
python scripts/stress_liquidity.py --demo
python scripts/stress_liquidity.py --input your_data.csv --out report.json
```

## 运行参数

| 参数 | 是否必需 | 说明 |
| --- | --- | --- |
| `--demo` | 与 `--input` 二选一 | 使用内置示例；不能与 `--input` 同时使用 |
| `--input <csv>` | 与 `--demo` 二选一 | 输入 UTF-8 CSV |
| `--participation <float>` | 否 | 日参与率，默认 `0.1`，必须有限且在 `(0,1]` |
| `--volume-shock <float>` | 否 | ADV 压力乘数，默认 `0.5`，必须为有限正数 |
| `--horizon-days <int>` | 否 | 期限交易日，默认 `5`，必须为模型有限数值范围内的正整数 |
| `--eta <float>` | 否 | 冲击系数，默认 `0.5`，必须为有限非负数 |
| `--redemption-value <float>` | 否 | 赎回现金目标，必须为有限非负数；省略时使用组合总值 |
| `--out <json>` | 否 | 输出文件；省略时输出到标准输出 |

可用 `--redemption-value` 指定赎回现金目标。安装方式：克隆本仓库，或把整个目录复制到 Agent 的 skills 目录；无需安装第三方 Python 包。PandaData 取数请配合 [`skill-pandadata-api`](https://github.com/quantskills/skill-pandadata-api)。

## 工作流

1. 定义正常/压力 ADV 与参与率
2. 计算逐标的清算天数
3. 叠加点差和平方根冲击
4. 聚合指定期限内可变现比例与现金缺口

## 输入与输出

- 输入：包含唯一且非空的 symbol，以及 position_value、adv、spread_bps、volatility 的持仓 CSV；所有数值必须有限，`position_value` 与 `adv` 使用同币种金额口径。
- 输出：JSON 最大期限变现容量、按持仓权重比例分配的赎回现金、缺口、赎回成本和逐标的压力结果。

## 数据来源

- 接入模式：**混合接入**，同时保留 CSV 离线输入。
- PandaData 方法：`get_stock_daily`、`get_stock_min`、`get_future_daily`、`get_future_min`、`get_option_daily`。
- 真实 API 调用委托给兄弟 Skill `pandadata-api`；本 Skill 不复制账号认证逻辑。
- 详细覆盖范围、字段映射和降级规则见 `references/pandadata-integration.md`。
- 持仓市值、赎回情景和真实 bid-ask spread 属于用户/经纪商数据；若用高低价差等代理，必须标记为 proxy 并做敏感性分析。

## 仓库结构

```text
skill-portfolio-liquidity-stress-test/
├── SKILL.md
├── README.md
├── README.en.md
├── .gitignore
├── LICENSE
├── requirements.txt
├── agents/
│   ├── cursor-rule.mdc
│   ├── openai.yaml
│   └── portable-loader.md
├── scripts/stress_liquidity.py
├── tests/test_liquidity_stress.py
├── validation/README.md
├── validation/smoke.py
└── references/
    ├── methodology.md
    ├── output-contract.md
    └── pandadata-integration.md
```

## 研究边界

本 Skill 仅用于研究和教育，不提供买卖建议、收益承诺或自动交易。所有阈值、代理变量和数据缺口都应在报告中披露。
