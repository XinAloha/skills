# 日内行情质量审计

> 在日内研究前检查标准化 OHLCV K 线的时间戳、缺口、OHLC 关系、价格与成交量。

## 解决什么问题

在日内研究前检查时间戳、缺失 K 线、OHLC 关系、非正价格、负成交量和交易日错配。缺口是待核查标记，不自动判定为停牌或数据错误。

与社区现有能力的边界：它识别数据异常，不自动删除成交，也不替代交易所最终裁定。

## 快速开始

```bash
python scripts/audit_bars.py --demo
python scripts/audit_bars.py --input your_data.csv --out report.json
python scripts/audit_bars.py --input your_data.csv --expected-seconds 300 --out report.json
```

安装方式：克隆本仓库，或把整个目录复制到 Agent 的 skills 目录；无需安装第三方 Python 包。PandaData 取数请配合 [`skill-pandadata-api`](https://github.com/quantskills/skill-pandadata-api)。

## 工作流

1. 按交易所日历和时区规范时间
2. 检测重复、缺口和乱序
3. 验证 OHLCV 不变量
4. 将缺口与时段边界交给交易所日历或供应商证据复核

## 输入与输出

- 输入：包含 symbol、trading_date、session、timestamp、open、high、low、close、volume 的分钟/秒级 CSV。脚本按 `symbol + trading_date + session` 分组；合法跨自然日夜盘应显式使用 `night`、`night_session`、`overnight` 或 `night_*` session 标签。同组 ISO-8601 时间戳不得混用带时区和不带时区的格式。
- 输出：JSON 数据质量报告和逐时间戳问题清单。

## 运行参数

| 参数 | 类型/默认值 | 说明 |
|---|---|---|
| `--demo` | 开关 | 使用内置异常样例，与 `--input` 二选一 |
| `--input` | CSV 路径 | 真实数据模式必填 |
| `--out` | 可选 JSON 路径 | 省略时输出到标准输出 |
| `--expected-seconds` | 正整数，默认 `60` | 预期 K 线间隔；实际间隔超过 `1.5 ×` 该值时标记缺口 |

`--demo` 与 `--input` 同时提供或同时缺失时，CLI 输出用法并以退出码 `2` 结束。非正的 `--expected-seconds` 或证据不足的输入会生成 `insufficient-evidence` JSON 报告。

## 数据来源

- 接入模式：**直接接入**，同时保留 CSV 离线输入。
- PandaData 方法：`get_trade_cal`、`get_stock_min`、`get_stock_rt_min`、`get_index_min`、`get_future_min`、`get_future_detail`。
- 真实 API 调用委托给兄弟 Skill `pandadata-api`；本 Skill 不复制账号认证逻辑。
- 详细覆盖范围、字段映射和降级规则见 `references/pandadata-integration.md`。
- 分钟接口不是逐笔成交或 Level-2 盘口；不能用它验证队列位置、撤单或逐笔撮合顺序。

## 仓库结构

```text
skill-intraday-data-quality-auditor/
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
├── scripts/audit_bars.py
├── tests/test_audit_bars.py
├── validation/
│   ├── README.md
│   └── smoke.py
└── references/
    ├── methodology.md
    ├── output-contract.md
    └── pandadata-integration.md
```

## 研究边界

本 Skill 仅用于研究和教育，不提供买卖建议、收益承诺或自动交易。所有阈值、代理变量和数据缺口都应在报告中披露。
