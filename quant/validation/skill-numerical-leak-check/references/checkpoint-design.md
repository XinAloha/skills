# Checkpoint 设计

数值型未来泄露检查会失效的常见原因是 cut 没打到泄露暴露的位置。checkpoint 设计比单纯增加数据长度更重要。

## 默认切点

建议从三类切点合并去重：

1. 固定比例：10%、20%、25%、30%、40%、50%、70%、82%、93%。
2. 固定位置：20、40、60、80、120、160、200、240、250、252、300、400、500。
3. 敏感点邻域：对每个敏感点 `x`，测试 `x-10,x-5,x-3,x-2,x-1,x,x+1,x+2,x+3,x+5,x+10`。

## 敏感点来源

优先从项目上下文中识别：

- period、window、lookback、horizon、lag、delay。
- rolling warmup、min_periods、expanding 起点。
- `shift`、未来收益标签、forward return horizon。
- resample、bar 聚合、session 开收盘、日内/日频边界。
- 调仓日、换月日、成分股重构日、截面 rank/groupby 日期。
- 用户指出的历史失败 cut 或历史泄露位置。
- 代码中 if/else 切换阈值对应的时间点。

## 批量检查时避免爆炸

如果一批因子都有自己的 period/window：

- 每个 case 只围绕该 case 的核心参数加密。
- 不要对所有参数做全量笛卡尔积。
- 先用轻量默认切点批量 gate。
- 对 FAIL/WARN 或重点候选做严检模式。

## 严检模式

当用户特别担心某个区间，或历史上出现过 “period 前后泄露”：

- 对 `period-k` 到 `period+k` 连续扫描，`k` 可取 10、20 或用户指定。
- 对 `2*period`、`3*period`、warmup 附近重复连续扫描。
- 增加随机 cut，记录 seed。
- 对 FAIL 附近做二次局部 sweep，缩小首个失败边界。

## 结果解释

checkpoint 覆盖越密，越能降低漏检风险，但永远不是形式证明。报告中必须说明本次覆盖了哪些敏感点，以及哪些真实生产边界没有覆盖。
