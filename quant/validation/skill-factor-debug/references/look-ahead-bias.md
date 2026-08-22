# 未来函数 / Look-Ahead Bias —— 最危险的 bug

## 症状

信号通过校验，但 IC 异常高（> 0.15），回测年化 50%+，"实盘"必崩。

危险信号：

- rank IC > 0.15
- 回测年化 > 50% 且 MDD < 5%
- Sharpe / IC_IR > 1.0
- train / val / test 三段 IC 量级一致且都 > 0.10

真实因子的 val IC 应该比 train IC 低 30~70%。

## 经典未来函数模式

### 模式 1：用 T 日 close 做 T 日成交价

```python
# ❌ 错误
factor[t] = close[t] / close[t - 5] - 1   # 因子计算 OK
signal[t] = factor[t]                      # OK
trade_at_t_close = signal[t]               # ❌ T 日收盘怎么会知道 T 日收盘后的信号？

# ✅ 正确
trade_at_t_plus_1_open = signal[t]
```

### 模式 2：forward return 方向反了

```python
# ❌ 错误
fwd_ret = close.pct_change(h)              # backward 收益

# ✅ 正确
fwd_ret = close.pct_change(h).shift(-h)    # shift -h 让 t 行存 [t, t+h] 的收益
fwd_ret = open.shift(-1).pct_change(h).shift(-h)  # 更准：T+1 开盘成交
```

### 模式 3：fillna(method='bfill') 用未来值填过去

```python
# ❌ 错误
factor = factor.fillna(method="bfill")     # 未来值填过去 = 未来函数

# ✅ 正确
factor = factor.fillna(method="ffill")     # 历史值填未来（注意信息饱和）
```

### 模式 4：在全段（train+val+test）拟合参数，再 reapply

```python
# ❌ 错误
mean = X.mean()                            # 包含 val/test 信息
X_normalized = (X - mean) / X.std()

# ✅ 正确
mean_train = X_train.mean()
X_val_normalized = (X_val - mean_train) / X_train.std()
```

### 模式 5：rolling 窗口包含当前

```python
# ❌ 错误（Pandas 默认 closed='right' 是包含当前）
ma = close.rolling(20).mean()              # 这行 OK
signal = close - ma                         # 这行也 OK
trade_at_t = signal                         # 但 trade_at_t = close[t] - ma[t] 是 T 日收盘后才能算
                                             # 实际只能 T+1 成交

# ✅ 正确：要么 T+1 成交，要么 rolling 用 shift(1)
ma = close.rolling(20).mean().shift(1)     # 让 t 行的 ma 只用 [t-20, t-1] 数据
```

### 模式 6：用未来字段切子样本

```python
# ❌ 错误：用 2026 年的市值切 2021 年
size_2026 = panel.loc["2026"].groupby("symbol")["close"].mean()
ic_by_size_2021 = ...用 size_2026 切 2021 年数据...

# ✅ 正确：用过去的市值切
size_proxy = (close * volume).rolling(120, min_periods=60).mean()  # T 日及之前的滚动均值
```

## 自检方法

把 IC 拆成三段（train / val / test 各算一次）：

```python
ic_train = compute_rank_ic(signal_train, fwd_ret_train).mean()
ic_val   = compute_rank_ic(signal_val, fwd_ret_val).mean()
# ic_test 由 judge.py 算，agent 不可见

print(f"train IC: {ic_train:.4f}")
print(f"val IC:   {ic_val:.4f}")
print(f"val/train: {ic_val / ic_train:.2%}")  # 期望 30% ~ 70%
```

| val/train | 解读 |
|---|---|
| 95%+ | 可能有未来函数（泛化太好） |
| 30% ~ 70% | 健康，正常衰减 |
| < 30% | 过拟合 train，但不一定有未来函数 |
| 接近 0 | 因子本身无效 |

## 二分排查

```
1. 把 alpha.py 的 FACTORS 减半，跑 IC
2. 看哪一半 IC 异常高
3. 重复二分定位单个因子
4. 检查那个因子的：
   - rolling 窗口是否包含当前
   - 是否用了 future-looking shift
   - fillna 方向
   - winsorize 时是否用了截面统计（截面 winsorize OK，时序 winsorize 危险）
```

## 反模式

- ❌ 看到 IC=0.20 立刻欢呼"找到 alpha 了" —— 先怀疑未来函数
- ❌ 修复前不写隔离测试 —— 改完不知道是不是真修好了
- ❌ 改完直接跑 runner.once，不先 smoke test —— 浪费时间
