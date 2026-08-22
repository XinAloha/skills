# 报告模板

建议将报告写入 `<out_dir>/leak_check_report.md`。

```markdown
# 数值型未来泄露检查报告

## 检查范围

- 检查对象：
- case 数量：
- 输入来源：
- 输出对象：
- 比较口径：

## 方法

- Prefix replay：
- Future mutation：
- Checkpoint 策略：
- 容忍度：
- 随机种子：

## 总览

| status | cases |
|---|---:|
| PASS |  |
| WARN |  |
| FAIL |  |
| ERROR |  |

## Case 汇总

| case_id | worst_status | tests | worst_test_type | first_bad_cut | max_abs_diff | bad_points |
|---|---|---:|---|---:|---:|---:|

## FAIL/WARN 明细

| case_id | status | test_type | cut | first_bad_idx | max_abs_diff | bad_points | notes |
|---|---|---|---:|---|---:|---:|---|

## 可能泄露路径

- 

## 稳健性和局限

- 本次覆盖的敏感点：
- 未覆盖的真实生产边界：
- 可能漏检的条件：

## 建议

- 
```
