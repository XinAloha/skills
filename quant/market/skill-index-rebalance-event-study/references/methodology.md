# 方法论

## 核心原则

1. 使用历史成分而非当前成分
2. 公告日与生效日分别建窗
3. 处理盘后公告、停牌和公司行动

## 推荐执行顺序

1. 冻结输入快照、时间窗、时区、单位和标识符。
2. 运行脚本并保存 JSON，不在原始文件上就地修改。
3. 人工复核所有高严重度发现，区分确定性错误与启发式风险。
4. 改变参数时保留前后版本并解释原因。
5. 在独立样本或压力场景复算，不用单一历史窗口证明稳健。

## 主要参考

- [S&P Index Mathematics Methodology](https://www.spglobal.com/spdji/en/methodology/article/index-mathematics-methodology/)
- [Nasdaq-100 adds and deletes](https://www.nasdaq.com/articles/looking-nasdaq-100-index-adds-and-deletes)

## 解释规则

- `pass` 只表示已执行的检查未发现问题，不代表策略有效或未来盈利。
- `fail` 必须附具体记录、字段或计算证据。
- `insufficient-evidence` 用于关键字段、历史版本或真实执行信息缺失。
