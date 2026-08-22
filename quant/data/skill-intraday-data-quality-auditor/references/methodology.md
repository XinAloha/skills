# 方法论

## 核心原则

1. 先识别交易时段再判断缺失
2. 异常价格要结合停牌、涨跌幅与更正记录
3. 原始数据与清洗数据都要保留

## 推荐执行顺序

1. 冻结输入快照、时间窗、时区、单位和标识符。
2. 运行脚本并保存 JSON，不在原始文件上就地修改。
3. 人工复核所有高严重度发现，区分确定性错误与启发式风险。
4. 改变参数时保留前后版本并解释原因。
5. 在独立样本或压力场景复算，不用单一历史窗口证明稳健。

## 主要参考

- [FINRA Clearly Erroneous Transactions](https://www.finra.org/rules-guidance/rulebooks/immediately-effective-rule-changes-pending-sec-notification-3)
- [Shenzhen Stock Exchange Trading Rules](https://www.szse.cn/English/rules/siteRule/P020240911598586572526.pdf)

## 解释规则

- `pass` 只表示已执行的检查未发现问题，不代表策略有效或未来盈利。
- `fail` 必须附具体记录、字段或计算证据。
- `insufficient-evidence` 用于关键字段、历史版本或真实执行信息缺失。
