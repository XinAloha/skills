# 结果解读

## 状态定义

`PASS`：在当前输入、checkpoint、扰动和比较口径下，历史输出没有超过容忍度的变化。

`WARN`：出现小差异、非确定性或边界异常。需要判断是否为浮点误差、随机性、缓存、排序不稳定、NaN 处理差异，还是弱泄露。

`FAIL`：prefix replay 或 future mutation 导致 checkpoint 及以前的历史输出发生明确变化。

`ERROR`：adapter、目标计算、输入构造或比较逻辑运行失败。ERROR 不等于无泄露。

## FAIL 分析顺序

1. 看 `test_type`：prefix 失败通常指 full run 和历史前缀 run 不一致；mutation 失败通常指未来值直接影响了历史输出。
2. 看 `first_bad_cut` 和 `first_bad_idx`：定位最早暴露位置。
3. 看 `max_abs_diff` 和 `bad_points`：判断是局部边界问题还是大面积污染。
4. 对失败 cut 附近做更密的局部 sweep。
5. 查目标代码中的未来窗口、全样本 fit/rank/normalize、缓存、排序和对齐逻辑。

## 对话摘要

最终对话中至少给出一个小表：

| status | cases |
|---|---:|
| PASS | n |
| WARN | n |
| FAIL | n |
| ERROR | n |

如果有 FAIL/WARN，再给：

| case_id | worst_status | first_bad_cut | test_type | max_abs_diff | likely_area |
|---|---|---:|---|---:|---|

不要只输出“报告已生成”。
