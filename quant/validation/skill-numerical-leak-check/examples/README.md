# Examples

这个目录包含两个最小因子，用来盲测数值型未来泄露检查：

- `factors/factor_001.py`
- `factors/factor_002.py`

两个因子都使用 `np.convolve` 构造信号，其中一个存在未来泄露，另一个没有。文件名和说明不标注答案，适合让另一个 agent 独立检测。

运行：

```bash
python ../scripts/run_numerical_leak_check.py \
  --adapter leak_check_adapter.py \
  --config leak_check_config.json \
  --out-dir runs/convolve_example \
  --workers 1
```

因为示例里包含一个故意泄露的因子，runner 返回码预期为 `1`。结果文件：

```text
runs/convolve_example/
├── leak_check_results.csv
├── leak_check_results.json
├── leak_check_summary.json
└── leak_check_report.md
```
