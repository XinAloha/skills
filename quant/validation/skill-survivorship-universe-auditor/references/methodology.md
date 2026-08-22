# 方法论

## 核心原则

1. 稳定标识符优先于 ticker
2. 退市证券必须保留到实际退市日
3. 退市收益缺失时显式标注而非填零

## 退市收益口径

本脚本把 `return` 定义为未纳入退市处理的普通简单收益，把 `delisting_return` 定义为权威来源提供的、已包含退市影响的同周期总收益。成对观测的收益高估量为：

`return - delisting_return`

如果数据源提供的是需要与普通收益复合的“额外退市收益”，必须先按供应商方法转换为同周期总收益，不能直接填入本字段。

## 推荐执行顺序

1. 冻结输入快照、时间窗、时区、单位和标识符。
2. 运行脚本并保存 JSON，不在原始文件上就地修改。
3. 人工复核所有高严重度发现，区分确定性错误与启发式风险。
4. 改变参数时保留前后版本并解释原因。
5. 在独立样本或压力场景复算，不用单一历史窗口证明稳健。

## 主要参考

- [Shumway: The Delisting Bias in CRSP Data](https://doi.org/10.1111/j.1540-6261.1997.tb03818.x)
- [CRSP market history and PERMNO](https://www.crsp.org/seeing-through-the-fog-of-market-history/)

## 解释规则

- `pass` 只表示已执行的检查未发现问题，不代表策略有效或未来盈利。
- `fail` 必须附具体记录、字段或计算证据。
- `insufficient-evidence` 用于关键字段、历史版本或真实执行信息缺失。
