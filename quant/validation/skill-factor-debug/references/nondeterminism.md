# 不可复现（Non-determinism）

## 症状

同代码两次跑结果不一样。

## 常见原因和修复

| 来源 | 修复 |
|---|---|
| `dict` / `set` 顺序 | 排序后再迭代：`for k in sorted(d.keys())` |
| `np.random` / `torch.manual_seed` 未固定 | 显式设种子（见下） |
| `dropna(how="any")` 行集随浮点波动 | 用稳定的过滤逻辑（如 `.notna().all(axis=1)`） |
| 多线程 / `joblib` 浮点 reduction 顺序 | 限定单线程：`n_jobs=1` |
| `pandas groupby().apply()` 不同版本顺序不同 | 显式 `sort=True`，或先 `sort_values` |
| LightGBM / XGBoost 多线程 | 设 `num_threads=1` 或 `seed=...` 同时设 `deterministic=True` |
| GPU 浮点非确定 | CUDA 设 `torch.use_deterministic_algorithms(True)` |

## 固定种子的标准做法

```python
import os, random
import numpy as np

SEED = 42

random.seed(SEED)
np.random.seed(SEED)
os.environ["PYTHONHASHSEED"] = str(SEED)

# 如果用了 sklearn
from sklearn.utils import check_random_state
rng = check_random_state(SEED)

# 如果用了 LightGBM
import lightgbm as lgb
params = {"seed": SEED, "deterministic": True, "num_threads": 1}

# 如果用了 PyTorch
import torch
torch.manual_seed(SEED)
torch.cuda.manual_seed_all(SEED)
torch.use_deterministic_algorithms(True)
```

## 验证可复现

```python
# 跑两次比对
sig1 = alpha.run(train, val)
sig2 = alpha.run(train, val)

assert sig1[0].equals(sig2[0]), "signal_train 不可复现！"
assert sig1[1].equals(sig2[1]), "signal_val 不可复现！"
```

## 浮点累加顺序问题

```python
# ❌ 不可复现：reduce 顺序依赖线程数
result = arr.sum()  # 多线程下结果可能 ±1e-15 不同

# ✅ 可复现：强制单线程
import numpy as np
np.set_printoptions(precision=17)
# 用 numpy 的 add.reduce(axis) 而不是 sum()，或者强制 single-thread

# 或者：用确定性 reduction
result = float(np.sum(arr.astype(np.float64)))
```

通常 1e-15 量级的差异不影响 IC 这类指标，但**会影响 score 在 ±0.001 边界上的接受/拒绝**。

## 反模式

- ❌ 设了 `np.random.seed` 就以为可复现 —— 还有其它源
- ❌ 觉得"差别在小数点 10 位以后没关系" —— score 边界附近会翻盘
- ❌ 用线程并行加速，但没加 deterministic —— 高并发下肯定崩

## 项目里如何检查

```bash
# 跑两次 runner.once，对比 score
py runner.py once
score_1=$(cat journal/runs.jsonl | tail -1 | jq .score)

py runner.py once
score_2=$(cat journal/runs.jsonl | tail -1 | jq .score)

diff <(echo $score_1) <(echo $score_2)
```

如果两次 score 不一样 → 因子有非确定性，先修复再继续。
