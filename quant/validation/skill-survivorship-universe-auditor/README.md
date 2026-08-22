# 生存者偏差股票池审计

> 检查历史成员资格与上市/退市边界，按输入快照重建股票池并发现退市收益缺口。

## 解决什么问题

检查输入股票池是否包含上市前或退市后证券，按明确存在的 symbol-date 快照重建 eligible universe，并标记缺失的退市收益。

能力边界：本工具审计历史股票池，不负责因子计算、选股条件或指数估值分析。

## 快速开始

```bash
python scripts/audit_universe.py --demo
python scripts/audit_universe.py --input your_data.csv --out report.json
```

## 运行参数

| 参数 | 是否必需 | 说明 |
| --- | --- | --- |
| `--demo` | 与 `--input` 二选一 | 使用内置示例；不能与 `--input` 同时使用 |
| `--input <csv>` | 与 `--demo` 二选一 | 输入 UTF-8 CSV |
| `--out <json>` | 否 | 输出文件；省略时输出到标准输出 |

同时提供两种数据入口或均未提供时，命令以参数错误码 2 退出。

安装方式：克隆本仓库，或把整个目录复制到 Agent 的 skills 目录；无需安装第三方 Python 包。PandaData 取数请配合 [`skill-pandadata-api`](https://github.com/quantskills/skill-pandadata-api)。

## 工作流

1. 核对证券生命周期字段
2. 按输入中存在的历史日期重建 eligible universe
3. 检查上市前/退市后误入股票池
4. 检查退市日收益；有成对数据时量化收益高估

## 输入与输出

- 输入：包含 symbol、date、eligible、listed_at、delisted_at、return、delisting_return 的成员资格或收益 CSV；日期使用 `YYYY-MM-DD`，eligible 严格为 `0/1`。`return` 是未纳入退市处理的普通收益，`delisting_return` 是权威来源提供的、已包含退市影响的同周期总收益。
- 输出：JSON 审计报告和需要修复的证券/日期清单。

## 数据来源

- 接入模式：**混合接入**，同时保留 CSV 离线输入。
- PandaData 方法：`get_trade_cal`、`get_trade_list`、`get_stock_status_change`、`get_stock_daily`。
- 真实 API 调用委托给兄弟 Skill `pandadata-api`；本 Skill 不复制账号认证逻辑。
- 详细覆盖范围、字段映射和降级规则见 `references/pandadata-integration.md`。
- PandaData 未明确提供标准化退市收益；若研究要求精确 delisting_return，必须由用户或其他权威数据源补充，不能用 0 代替。

## 仓库结构

```text
skill-survivorship-universe-auditor/
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
├── scripts/audit_universe.py
├── tests/test_universe_auditor.py
├── validation/README.md
├── validation/smoke.py
└── references/
    ├── methodology.md
    ├── output-contract.md
    └── pandadata-integration.md
```

## 研究边界

本 Skill 仅用于研究和教育，不提供买卖建议、收益承诺或自动交易。所有阈值、代理变量和数据缺口都应在报告中披露。
