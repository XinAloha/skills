# op_types — 单点假设的 8 种合法改动

> 每次实验只改一件事。这份清单定义"一件事"的边界。

| op_type | 含义 | 触发相关性门控 | 典型 score 变化 |
|---|---|---|---|
| `add_factor` | 在 FACTORS 列表加 1 个新因子 | ✅ 强制（与所有已有因子算 ρ） | +0.05 ~ +0.5 |
| `modify_factor` | 改已有因子的窗口 / 参数 / 实现细节 | ✅ 与原版本算 ρ | ±0.05 ~ ±0.2 |
| `delete_factor` | 从 FACTORS 删 1 个 | ❌ | 通常 ≤ 0 |
| `combine_method` | 改组合方法（等权 → IC_IR → Ridge → LGBM → MLP） | ❌ | ±0.1 ~ ±0.5 |
| `label_kind` | 改标签口味（raw / market_neutral / vol_adjusted / rank / zscore） | ❌ | ±0.05 ~ ±0.2 |
| `horizon` | 改持有期（1 / 3 / 5 / 10 / 20） | ❌ | ±0.1 ~ ±1.0 |
| `preprocess` | 改预处理（winsorize n_mad、z-score 方式、NaN 填充） | ❌ | ±0.05 ~ ±0.1 |
| `other` | 重构 / 兼容性变更，逻辑不变 | ❌ | ≈ 0 |

## 跨多个 op_type 的改动

**违反单点假设**。请拆成两次实验：

```
❌ 一次性"加 amihud + 把组合改成 Ridge + horizon 5→20"
   即使提分也无法归因，后续无法复用

✅ 拆三次：
   Iter N+1: add_factor   amihud          [+0.04]
   Iter N+2: combine_method Ridge         [+0.08]
   Iter N+3: horizon 5→20                 [+0.11]
   每一步都可独立验证、独立回滚
```

## 边界情况

- **同时加 2 个因子** → 算两次 `add_factor`，分两轮
- **改一个因子的同时优化它的参数** → 算 `modify_factor`，但说清楚是哪个参数
- **删 1 个加 1 个**（"等价替换"）→ 拆成两次：先 `delete_factor` 看分数下降幅度，再 `add_factor` 看新因子贡献
- **重构代码不改逻辑**（如把 5 个因子函数合并成一个工厂函数） → `other`，预期 score ≈ 0

> 参考实现：`auto_research_alpha/program.md §11`，runner 通过 `ITER_NOTE.op_type` 决定是否触发相关性门控。
