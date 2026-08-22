# 黑名单 PermissionError — 禁词命中

## 症状

```
PermissionError: 黑名单命中 'factor_library' / '_test_metrics' / 'judge' / ...
```

## 原因

为防未来数据泄漏，runner 在 import alpha 之前先做**源码静态扫描**，命中即拒。

典型禁词清单（按 `auto_research_alpha` 项目）：

```
_load_test_panel        # prepare 私有函数
AUTOALPHA_TEST_LOCKED   # 测试段环境变量锁
factor_library          # 归档目录（含每张卡的 _test_metrics.json）
_test_metrics           # 私有产物
journal                 # 含 best.json / runs.jsonl / test_eval.jsonl
test_eval               # judge.py 产出
judge                   # judge.py 模块
splits.json             # 切分定义（含 test 段日期）
```

## 为什么必须禁

- 看到了 test 段数据就**已经污染了"未见性"**，三段切分立刻作废
- 读了别人的 `card.json` 或 `_test_metrics.json` 等于偷看真未来
- 读了 `journal/best.json` 等于知道"哪条路径分数高"，会引导走捷径
- 即使是无意识的 `import factor_library` 也会触发 —— **有意为之**

## 修复

```bash
# 1. 看完整错误堆栈
cat journal/last_failed/run_XXXX_error.txt

# 2. grep alpha.py 找命中行
grep -n "factor_library\|_test_metrics\|journal\|judge" alpha.py

# 3. 删掉所有命中（包括注释 — 静态扫描不区分注释和代码）
```

## 想做某分析时怎么办

| 你想做的事 | 不许做 | 改做 |
|---|---|---|
| 看自己上次的 IC decay | `import journal.runs` | 在 `metrics.py` 里用 in-process 数据算 |
| 比较 best 因子和当前因子 | 读 `factor_library/<id>/card.json` | runner 会自动比较，你只看 `score` 字段 |
| 检查测试段表现 | 任何形式触碰 test 段 | 等人类跑 `judge.py --best` |

## 反模式

- ❌ 把禁词拆成字符串拼接绕过：`"factor_" + "library"` —— 也会被检出（部分实现会做拼接还原）
- ❌ 读了禁词产物再删除 —— 已经污染
- ❌ "我只看一眼，不影响" —— 看了就废
