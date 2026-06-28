---
description: 硬 bug / 性能回归的反馈循环驱动诊断流程 - 复现→最小化→假设→工具→修复→回归
type: methodology
parent: dev-guidelines.md
auto_execution_mode: 2
source: Matt Pocock skills - engineering/diagnose
---

# Diagnose - 诊断

> 触发：用户说 "诊断 / 修这个 bug / 这个有问题 / 性能回归"，或报告报错、抛异常、跑不通、运行变慢。

## 核心理念

**第 1 阶段（构建反馈循环）就是这门 skill 的全部**。其他都是机械流程。如果你拥有一个**快速、确定性、可由 Agent 自动跑**的 pass/fail 信号，就一定能定位到 bug——二分、假设验证、加埋点都只是消费这个信号；如果没有，盯着代码看再久也救不了你。

> 本项目特别提示：A 股数据问题往往涉及网络、外部 API、时区、复权、停牌等不可控因素。把它们 mock 掉、用 fixture 重放，是构建确定性反馈循环的关键。

## 阶段 1 - 构建反馈循环

按粗略优先级尝试以下方式：

1. **失败的测试**（首选）：用 pytest 在合适的 seam 上写一个能复现 bug 的测试。本项目示例：
   ```bash
   pytest test/unit/test_xxx_collector.py::test_handle_suspended -v
   pytest test/data_quality/test_daily_kline_completeness.py -k "specific_case"
   ```
2. **CLI 重放**：把出问题的请求/参数固化为 fixture，用 `python -m data_collection.cli ...` 或 `python -m data_collection.database.inspector --check ...` 重放。
3. **采集器单点调试**：单独构造一个 `XxxCollector(...)` 实例，用最小参数集 `fetch_daily(...)` / `fetch_basic_info(...)`，观察输出。
4. **重放抓取的数据**：把外部 API 响应（Tushare/AKShare/adata 的 JSON / DataFrame）保存为 pickle/parquet，写一个测试在隔离环境里跑。
5. **数据库快照对比**：旧库 vs 新库（或修复前 vs 修复后），用 `data_collection.database.inspector --summary` diff。
6. **属性/模糊测试**：当 bug 偶发时，跑 1000 个不同股票/不同日期，找规律。
7. **二分**：bug 在两个已知状态间出现，用 `git bisect run` + 一段验证脚本。
8. **差异回归**：旧版本 vs 新版本相同输入，diff 输出。

把循环本身当成产品来打磨：

- 让它**更快**（缩窄测试范围、跳过无关初始化、缓存 setup）。
- 让信号**更尖锐**（断言精确症状，而不是"没崩"）。
- 让它**更确定**（pin 时间、seed RNG、隔离文件系统、freeze 网络）。

> 30 秒的 flaky 循环几乎等于没循环；2 秒的确定性循环是调试超能力。

### 偶发 bug

目标不是干净复现，而是**提高复现率**。循环 100 次、并发、加压、缩窄时序窗、注 sleep。50% 概率的 flaky 能调，1% 不能——把概率往上抬，抬到能调为止。

### 实在做不出循环

**停下来明确说明**。列出试过什么。请用户给：(a) 能复现的环境访问权限；(b) 抓取的产物（HAR、日志 dump、core dump、带时间戳的录屏）；(c) 临时加生产埋点的许可。**没有循环不要往下走**。

## 阶段 2 - 复现

跑循环，看见 bug 出现。确认：

- [ ] 循环复现的是**用户描述的故障模式**——不是附近另一个相似 bug。错的 bug = 错的修复。
- [ ] 故障在多次运行中可复现（偶发 bug 则保证足够高的复现率）。
- [ ] 已捕获精确症状（错误信息、错误输出、慢的耗时），后续阶段才能验证修复对症。

复现不出来，**不要往下走**。

## 阶段 3 - 假设

在测试任何一个之前，先生成 **3-5 个排序的假设**。单一假设很容易 anchor 在第一个看起来合理的想法上。

每个假设必须**可证伪**：

> 格式：「如果 <X> 是原因，那么 <改 Y> 会让 bug 消失 / <改 Z> 会让它更严重」。

讲不出预测的"假设"是 vibe，删掉或锐化。

**把排序后的清单先给用户看**。他们经常有领域知识能立刻重排（"#3 我们刚改过部署"），或知道哪些已经排除过。便宜的 checkpoint，省时间多。但用户不在场就按你的排序往下走，不要 block。

## 阶段 4 - 加工具

每个埋点要**对应阶段 3 的某个具体预测**。**一次只改一个变量**。

工具优先级：

1. **debugger / REPL**（环境支持就用）。一个断点胜十条日志。Python 用 `breakpoint()` / `pdb` / IDE 调试器。
2. **定向日志**：放在能区分假设的边界处。
3. 永远不要"全部打印 + grep"。

**所有调试日志加唯一前缀**，例如 `[DEBUG-a4f2]`。最后清理就是一次 grep 的事。无前缀的日志会幸存下来，有前缀的能成批删。

**性能分支**：性能回归用日志通常是错的。先建立**基线测量**（计时器、`time.perf_counter()`、profiler、SQL `EXPLAIN ANALYZE`），然后二分。先量后修。

## 阶段 5 - 修复 + 回归测试

在写修复**之前**写回归测试——但只在有**正确 seam** 的前提下。

正确 seam = 测试在**真实 bug 发生的调用点**触发同样的 bug 模式。如果可用 seam 太浅（bug 需要多个调用方组合，但只能写单调用方测试；单元测试无法重现真实链条），在那里写回归测试只会给你**虚假信心**。

**找不到正确 seam，本身就是发现**。记下来。这说明代码架构在阻止 bug 被锁住。给阶段 6 留 flag。

如果有正确 seam：

1. 把最小化的复现转成失败测试。
2. 看它失败。
3. 应用修复。
4. 看它通过。
5. 把阶段 1 的循环用**未最小化的原始场景**再跑一遍。

## 阶段 6 - 清理 + 复盘

声明 done 之前必须：

- [ ] 原始复现不再复现（重跑阶段 1 循环）。
- [ ] 回归测试通过（或"无 seam"已记录）。
- [ ] 所有 `[DEBUG-...]` 埋点删除（`grep` 前缀验证）。
- [ ] 一次性原型删除（或挪到明显的 debug 位置）。
- [ ] **正确假设写进 commit / PR 信息**——下一个调试者就能学到。

**然后问：什么能阻止这个 bug 再次发生？** 如果答案涉及架构变更（缺正确 seam、调用链纠缠、隐藏耦合），把具体内容交给 [improve-codebase-architecture](improve-codebase-architecture/SKILL.md)。建议在**修完之后**给，不是之前——你现在比开始时知道得多。

## 本项目适配示例

### 反馈循环示例

**采集器对停牌股票字段填充错误**：

```python
# test/unit/test_tushare_collector.py
def test_suspended_stock_fields_should_be_null():
    fixture = load_pickle("test/fixtures/tushare_suspended_600000_20251010.pkl")
    collector = TushareCollector(api=MockApi(returns=fixture))
    df = collector.fetch_daily("600000.SH", "20251010")
    # 假设：停牌日 close 应为 None 而不是前一日 close
    assert df.iloc[0]["close"] is None  # 失败 -> 复现成功
```

```bash
pytest test/unit/test_tushare_collector.py::test_suspended_stock_fields_should_be_null -v --tb=short
```

### 性能回归示例

**全市场日线落库慢了 3 倍**：

```python
# 先建立基线
import time
t0 = time.perf_counter()
result = pipeline.run_daily_collection(date="20260615", limit=100)
print(f"[DEBUG-perf01] 100 stocks: {time.perf_counter()-t0:.2f}s")
```

二分到具体阶段（fetch / transform / write）后再细化。

## 相关 skill

- [fault-recovery](../testing/fault-recovery.md) - 重试、部分失败、采集中断恢复
- [test-strategy](../testing/test-strategy.md) - pytest 分层、覆盖率
- [collector-testing](../testing/collector-testing.md) - 采集器测试模板
- [avoid-pitfalls](../governance/avoid-pitfalls.md) - 已知陷阱清单
