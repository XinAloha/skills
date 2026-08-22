# 实战示例 —— auto_research_alpha 项目

> 不是要你照搬，是给一个"完整运转中的因子挖掘系统"长什么样的样本。

## 项目位置

参考项目：`auto_research_alpha`（自动挖因子框架，由本 skill 蓝本作者维护）。
你的副本可放在任意位置，下文用 `<project_root>` 表示其根目录。

## 关键文件分工

```
prepare.py        🔒 数据/切分/标签/回测/主分（人类锁定，不要改）
evaluation.md     🔒 评估宪法（主分公式 / 标签菜单 / 硬约束）
program.md        🔒 研究议程（方向 / 风格 / 禁词清单）
alpha.py          🔓 agent 唯一可改文件（≤ 1600 行）
metrics.py        🔓 诊断指标（不入主分）
runner.py         ⚙️ 实验循环
judge.py          ⚖️ 测试集守门人
factor_library/   📦 合格因子档案（card.json / chart_overview.png / 数据 csv）
journal/          📓 实验日志（best.json / runs.jsonl / snapshots / last_failed）
cache/            🗄 行情面板缓存 + 冻结切分
```

## 三段切分（永久冻结）

```
train: 2016-01-04 → 2021-12-03    (~5.9 年)
val:   2021-12-04 → 2024-12-03    (3.0 年)
test:  2024-12-04 → 2026-06-04    (1.5 年)
```

任何对 splits.json 的人为修改、对 parquet 文件的替换都会被 checksum 校验抓出。

## v2.3 主分公式（截面研究）

```python
score = 0.20 * ic_term      # IC：截面有效性
      + 0.30 * shp_term     # Sharpe：风险调整收益
      + 0.30 * ret_term     # 年化收益
      + 0.20 * mdd_term     # MDD：最大回撤
      + 0.10 * mono_term    # 单调性
      + 0.10 * turn_term    # 换手惩罚
```

每个分量先归一到 ~[-2, +2]，整体 score 范围 ~[-2, +2]。

v2.3 升级（2026-06-10）：half-life=2 年时间加权 + fold 32→16。

## 一轮典型迭代

```bash
# 1. 改 alpha.py（包括 ITER_NOTE）
# 2. 跑：
py runner.py once

# 输出：
[ACCEPTED] score +0.6234 (Δ +0.03)
        -> archived factor_library/20260612_103045_F0068_xxx/

# 失败示例：
[CRASH] PermissionError: 黑名单命中 'factor_library'
        -> reverted to journal/snapshots/best.py
        -> failed code at journal/last_failed/run_0068_error.txt

[CRASH] PermissionError: 因子相关性 ρ=0.91 (>= 0.85) with f_reversal_5
        -> reverted

# 3. 看进度：
py runner.py status
cat factor_library/INDEX.md
```

## 黑名单禁词（agent 永远不许碰）

```
_load_test_panel        # prepare 私有函数
AUTOALPHA_TEST_LOCKED   # 测试段环境变量锁
factor_library          # 归档目录
_test_metrics           # 私有产物
journal                 # 实验日志
test_eval               # judge.py 产出
judge                   # judge.py 模块
splits.json             # 切分定义
```

源码里出现任何一个 → runner 在 import alpha 之前就判 CRASH，不会真的执行。

## 记忆（你已存的）

详见 Claude Code 的项目记忆（`<user_home>/.claude/projects/<project-id>/memory/MEMORY.md`）：

- `autoalpha-overview` — 项目总览
- `autoalpha-scoring-v2` — v2 主分公式
- `autoalpha-v21-benchmark` — v2.1 评估增强
- `autoalpha-v22-rolling` — v2.2 滚动训练
- `autoalpha-v23-time-weighted` — v2.3 时间加权
- `autoalpha-alpha-contract` — alpha.py 契约
- `autoalpha-forbidden-tokens` — 禁词黑名单
- `autoalpha-runtime-cmds` — 运行命令
