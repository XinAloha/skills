# 信号校验失败

## 症状

```
ValueError: 截面均值超阈值 |mean(daily_mean)| = 0.082 (>= 0.05)
ValueError: 截面 std 不在 [0.5, 2.0]: 0.31
ValueError: 截面规模 < 30 在某些日期
ValueError: 全 NaN 行占比 > 50%
```

## 通用修复：截面 winsorize + z-score

返回信号前**必做**：

```python
def cs_winsorize_zscore(f: pd.DataFrame, n_mad: float = 3.0) -> pd.DataFrame:
    med = f.median(axis=1)
    mad = (f.sub(med, axis=0)).abs().median(axis=1)
    sigma = 1.4826 * mad
    f = f.clip(lower=med - n_mad * sigma, upper=med + n_mad * sigma, axis=0)
    mu = f.mean(axis=1)
    sd = f.std(axis=1).replace(0, np.nan)
    return f.sub(mu, axis=0).div(sd, axis=0)
```

调用规则：
1. 每个**单因子**进入组合前必做（L1）
2. **最终组合信号**返回前**再做一次**（L2）

## 子症状对照修复表

| 子症状 | 病因 | 修复 |
|---|---|---|
| `截面均值=0.082` | 没去截面均值 | 加 `f.sub(f.mean(axis=1), axis=0)` |
| `截面 std=0.31` | winsorize 太严，截到平 | n_mad 从 1.5 → 3.0 |
| `截面 std=0` | 因子全相同（lookback 太长，前期全 NaN） | 增加 `min_periods` 或缩短窗口 |
| `截面 std=2.5` | 因子未 z-score | 加 `f.div(f.std(axis=1), axis=0)` |
| `截面规模 < 30` | 因子需要长 lookback，早期全 NaN | 截掉 panel 早期段 |
| `全 NaN 行 > 50%` | 数据缺失严重 / 因子计算逻辑错 | 检查 panel 字段完整性 |

## n_mad 参数选择

| n_mad | 用途 |
|---|---|
| 1.5 | 严格 winsorize，A 股 ST 多时（推荐 baseline） |
| 3.0 | 标准 winsorize，主流场景 |
| 5.0 | 弱 winsorize，因子分布已较好（如已 rank） |

## 隔离测试

```python
import pandas as pd, alpha, prepare

train = prepare.load_train_panel()
sig_train, sig_val = alpha.run(train, prepare.load_val_panel())

# 手动校验
print("daily_mean abs:", sig_val.mean(axis=1).abs().mean())  # 期望 < 0.05
print("daily_std mean:", sig_val.std(axis=1).mean())          # 期望 0.5 ~ 2.0
print("min n_per_day :", (~sig_val.isna()).sum(axis=1).min()) # 期望 >= 30
```

## 反模式

- ❌ "校验阈值太严了，我去改 prepare.py 阈值" —— 阈值是宪法，不许改
- ❌ 把信号 clip 到 [-3, 3] 假装满足约束 —— 失真
- ❌ 只在最后 z-score 一次，不在中间 —— 单因子级别信噪比已坏
