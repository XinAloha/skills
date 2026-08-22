# ITER_NOTE — 实验便签强制模板

每次改 `alpha.py` 都同步更新顶层 `ITER_NOTE: dict`。

## 必填四字段

```python
ITER_NOTE: dict = {
    "op_type":    "add_factor",   # 见 op-types.md
    "hypothesis": "...",          # 你为什么觉得这个改动会提分（经济 or 统计含义）
    "change":     "...",          # 你具体改了什么（一句话能说清）
    "expected":   "...",          # 预期 score 区间 + 副作用（turnover / MDD）
}
```

## 推荐字段（强烈建议）

```python
    "parent_iter": 7,             # 当前 best 来自第几次实验
    "reasoning":   "...",         # 更深的因果链：上一轮发现了什么 → 这一轮做什么
```

## op_type 特定字段

| op_type | 推荐字段 |
|---|---|
| `add_factor` | `new_factor`: "f_amihud_20" — 新因子函数名 |
| `modify_factor` | `target_factor`: "f_vol_20"，`old_param`、`new_param` |
| `combine_method` | `from_method`: "equal_weight"，`to_method`: "ic_ir_weighted" |
| `horizon` | `from_h`: 5，`to_h`: 20，`reason_for_h`（IC decay 显示更长 H 信息更饱满）|

## 完整示例

```python
ITER_NOTE: dict = {
    "op_type":    "add_factor",
    "hypothesis": "新增 amihud 流动性因子（mean(|ret|/amount, 20d）），与现有低波家族相关性 < 0.6，应能补充流动性溢价信息。",
    "change":     "在 FACTORS 末尾加 f_amihud_20；其它不动。",
    "expected":   "score +0.35 → +0.40 左右；turnover 略升 2~3。",
    "parent_iter": 7,
    "reasoning":   "F0004 单调性 0.93 但 turnover=33 偏高；amihud 倾向稳健大票，应能压换手。",
    "new_factor":  "f_amihud_20",
}
```

## 为什么强制

没写 ITER_NOTE 的实验 = 没有假设的实验 = 蒙对了也无法复用。

- runner 在 import alpha 之前先 `getattr(alpha, "ITER_NOTE")`，缺字段 → CRASH，不会真的跑分
- ACCEPTED 时把 note 同步进 `card.json` 的 `note` 字段（永久档案）
- REJECTED 时把 note 落到 `journal/notes/{iter}.md`（让你回看自己的思考链）

## 反模式

| 反模式 | 修复 |
|---|---|
| `hypothesis: "试试看"` | 写出经济/统计因果（"流动性溢价" / "lottery preference"） |
| `expected: "提升"` | 给具体区间（"+0.03 ~ +0.07"） |
| `change: "优化代码"` | 说清楚改了哪一行 / 哪个参数 |
| 把"换标签 + 加因子"挤一个 ITER_NOTE | 拆成两次实验，两个 ITER_NOTE |

> 参考实现：`auto_research_alpha/program.md §7.1`，runner 在 `_validate_iter_note()` 强制校验。
