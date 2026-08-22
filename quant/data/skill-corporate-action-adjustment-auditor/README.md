# 公司行动复权审计

> 验证现金分红和拆并股在原始价格、复权价格与收益序列中的处理是否一致。

## 解决什么问题

验证现金分红和拆并股的输入是否合法，并核对原始总收益与复权收益。配股、分拆、并购和代码迁移不在当前可执行检查范围内。

与社区现有能力的边界：它验证数据处理，不预测公司行动，也不提供事件交易信号。

## 快速开始

```bash
python scripts/audit_adjustments.py --demo
python scripts/audit_adjustments.py --input your_data.csv --out report.json
```

## 运行参数

| 参数 | 是否必需 | 说明 |
| --- | --- | --- |
| `--demo` | 与 `--input` 二选一 | 使用内置示例；不能与 `--input` 同时使用 |
| `--input <csv>` | 与 `--demo` 二选一 | 输入 UTF-8 CSV，`date` 使用 `YYYY-MM-DD` |
| `--return-tolerance <float>` | 否 | 收益偏差容忍度，默认 `0.02`，必须是有限非负数 |
| `--jump-threshold <float>` | 否 | 无事件价格跳点阈值，默认 `0.40`，必须是有限正数 |
| `--out <json>` | 否 | 输出文件；省略时输出到标准输出 |

同时提供两种数据入口或均未提供时，命令以参数错误码 2 退出。

安装方式：克隆本仓库，或把整个目录复制到 Agent 的 skills 目录；无需安装第三方 Python 包。PandaData 取数请配合 [`skill-pandadata-api`](https://github.com/quantskills/skill-pandadata-api)。

## 工作流

1. 按证券和日期排序原始/复权序列
2. 将现金分红和拆并股映射为价格调整
3. 核对原始总收益与复权收益
4. 定位复权收益冲突和未解释跳点

## 输入与输出

- 输入：至少包含 symbol、date、close、adj_close、split_factor、cash_dividend 的 CSV；symbol 非空且不含首尾空白，每个 symbol 至少两个日期不同的观测值。`split_factor` 为当前行每一旧股对应的新股数，无事件填 `1`；`cash_dividend` 为当前行每一旧股现金分红，无事件填 `0`。两种价格必须同币种、同单位且为正数。
- 输出：JSON 异常清单，包含原始总收益、复权收益和冲突原因。

## 数据来源

- 接入模式：**直接接入**，同时保留 CSV 离线输入。
- PandaData 方法：`get_stock_daily`、`get_stock_daily_pre`、`get_stock_daily_post`、`get_adj_factor`、`get_stock_dividend`、`get_stock_split`、`get_stock_cash_dividend`、`get_stock_allotment`。
- 真实 API 调用委托给兄弟 Skill `pandadata-api`；本 Skill 不复制账号认证逻辑。
- 详细覆盖范围、字段映射和降级规则见 `references/pandadata-integration.md`。
- 分拆、并购换股、代码迁移等复杂事件若不在返回结果中，必须保留为未覆盖事件，不能据此宣布完整通过。

## 仓库结构

```text
skill-corporate-action-adjustment-auditor/
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
├── scripts/audit_adjustments.py
├── tests/test_audit_adjustments.py
├── validation/README.md
├── validation/smoke.py
└── references/
    ├── methodology.md
    ├── output-contract.md
    └── pandadata-integration.md
```

## 研究边界

本 Skill 仅用于研究和教育，不提供买卖建议、收益承诺或自动交易。所有阈值、代理变量和数据缺口都应在报告中披露。
