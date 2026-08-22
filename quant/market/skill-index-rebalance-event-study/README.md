# 指数调仓事件研究

> 研究指数纳入、剔除和权重调整在公告日、生效日及之后的价格、成交与反转效应。

## 解决什么问题

研究指数纳入、剔除和权重调整在公告日、生效日及之后的价格、成交与反转效应。

与社区现有能力的边界：它是指数调仓专项事件研究，不重复一般指数估值轮动，也不假设纳入必涨。

## 快速开始

```bash
python scripts/study_index_rebalance.py --demo
python scripts/study_index_rebalance.py --input your_data.csv --out report.json
```

## 运行参数

| 参数 | 是否必需 | 说明 |
| --- | --- | --- |
| `--demo` | 与 `--input` 二选一 | 使用内置示例；不能与 `--input` 同时使用 |
| `--input <csv>` | 与 `--demo` 二选一 | 输入 UTF-8 CSV |
| `--start <int>` | 否 | 窗口起始相对日，默认 `0` |
| `--end <int>` | 否 | 窗口结束相对日，默认 `1`，不得小于 start |
| `--out <json>` | 否 | 输出文件；省略时输出到标准输出 |

同时提供两种数据入口或均未提供时，命令以参数错误码 2 退出。

安装方式：克隆本仓库，或把整个目录复制到 Agent 的 skills 目录；无需安装第三方 Python 包。PandaData 取数请配合 [`skill-pandadata-api`](https://github.com/quantskills/skill-pandadata-api)。

## 工作流

1. 收集历史公告和生效日
2. 区分 add/delete/weight change
3. 通过可选 `relative_to=announcement/effective` 分别计算 AR/CAR 和成交量
4. 分别运行事前、实施和事后窗口，比较不同阶段的描述性结果

## 输入与输出

- 输入：包含 event_id、symbol、action、announcement_date、effective_date、relative_day、return、benchmark_return、volume_ratio 的 CSV；事件日期使用 `YYYY-MM-DD`，相对日为整数。推荐增加 `relative_to=announcement/effective`，脚本会按事件与锚点分别计算；权重研究可增加有限数值的 `weight_before/weight_after`。
- 输出：JSON 逐事件锚点 CAR、成交量比和按 action、锚点分层的聚合结果。

## 数据来源

- 接入模式：**直接接入**，同时保留 CSV 离线输入。
- PandaData 方法：`get_index_weights`、`get_index_daily`、`get_stock_daily`、`get_trade_cal`。
- 真实 API 调用委托给兄弟 Skill `pandadata-api`；本 Skill 不复制账号认证逻辑。
- 详细覆盖范围、字段映射和降级规则见 `references/pandadata-integration.md`。
- 若研究要求官方公告时间而不仅是权重快照变化，仍需补充指数公司公告；不得把首次观测日期冒充 announcement_date。

## 仓库结构

```text
skill-index-rebalance-event-study/
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
├── scripts/study_index_rebalance.py
├── tests/test_index_rebalance.py
├── validation/README.md
├── validation/smoke.py
└── references/
    ├── methodology.md
    ├── output-contract.md
    └── pandadata-integration.md
```

## 研究边界

本 Skill 仅用于研究和教育，不提供买卖建议、收益承诺或自动交易。所有阈值、代理变量和数据缺口都应在报告中披露。
