---
description: 版本发布检查清单 - 发布前逐条勾选确认（测试门禁/采集smoke/回测smoke/版本/Tag/推送），与 scripts/release/release.py 工具链配套（跨平台版）
type: sub-document
applies-to: [claude-code, codex]
auto_execution_mode: 2
---

# 版本发布检查清单

> **触发场景**：用户说"准备发布 v1.x.y" / "走发布流程" / "打 tag 发版本" 时按此清单逐条执行。
> 日常开发**不要主动**触发——这是版本切片操作，跟 `VERSION` / `CHANGELOG.md` / `scripts/release/release.py` 是一套配套。
> 配合 [`testing-and-verification.md`](testing-and-verification.md) 的分层测试策略阅读。

## Agent 平台适配提醒

1. **不主动执行** `git commit / git push / git tag` —— 参照 [CLAUDE.md](../../CLAUDE.md) §3 全局硬性约束（同样适用于 Codex），最后三条 git 操作必须用户**明确指令**才能执行；本清单 §"发布执行" 中的命令应**逐条征求用户确认**后再跑
2. **Python 解释器固定走** `/d/Developer_Tools/Anaconda/python.exe`（默认 `python` 是失效 Store 桩，exit 49 静默——见对应记忆条目），所有 `python` 命令在调用时都要替换。Claude Code 用 `Bash`、Codex 用 `run_terminal_cmd`，都要替换
3. **改文件前先确认当前内容**：
   - Claude Code：先 `Read` 再 `Edit`/`Write`；改 `VERSION` / `__init__.__version__` / `CHANGELOG.md` 都遵守
   - Codex：先 `Get-Content -Raw -Encoding UTF8 <file>` 核对，再 `apply_patch`
4. **跑测试**：Claude Code 用 `Bash: pytest ...`；Codex 用 `run_terminal_cmd pytest ...`。结果摘要回报给用户后再决定是否进入下一步

---

## 预发布准备

- [ ] 当前分支为 `main` 或基于 `main` 的发布分支
- [ ] 所有临时脚本已清理（`test*.py`, `_calc_*.py`, `check_*.py`, `fix_*.py`）
- [ ] 无硬编码敏感信息（Token、密码、数据库连接串）
- [ ] `.env` 未误提交到 Git
- [ ] 代码注释和 docstring 已补充（公共 API）

## 测试门禁

- [ ] `pytest test/data_system/unit test/backtest/unit test/shared/unit -q` 通过
- [ ] `pytest test/data_system/integration test/backtest/integration -q` 通过
- [ ] `pytest test/data_system/quality -q` 通过
- [ ] `python -m compileall quant_data quant_backtest quant_shared test` 无语法错误
- [ ] `python -m quant_data.database.inspector --summary` 输出正常

## 数据与回测验证（采集与回测平台）

### 采集路由 smoke test
- [ ] `python main.py --mode smart` 可正常执行（默认入口）
- [ ] `python main.py --mode scheduled-free --delay 0 --workers 1` 可正常执行（pytdx 免费高频主路由），或有明确跳过原因
- [ ] `python main.py --mode akshare-drip --budget 1` 小预算路径可正常执行，或有明确跳过原因
- [ ] `paid-refresh` 当前边界已确认：CLI 直接支持 `stock_industry_classification`，其余付费表仍通过 `TushareFullCollector`

### 数据完整性
- [ ] `stocks` 表有数据且最新
- [ ] `daily_kline` 表最新日期为最近交易日，主口径为原始未复权（`adjust_type=0`）
- [ ] `adjust_factors` 存在 `data_source='pytdx_xdxr'` 的累计后复权因子
- [ ] `collection_log`、`job_runs`、`job_steps` 记录完整无异常

### 回测 smoke test
- [ ] `python scripts/backtest/run_backtest.py --strategy small-cap --start-date 2024-01-01 --end-date 2024-03-31` 最小样本可运行
- [ ] `python scripts/backtest/run_ptrade_backtest.py --strategy quant_backtest/strategies/ptrade_demo.py --start-date 2024-01-01 --end-date 2024-03-31 --symbols 000001.SZ` 最小样本可运行

## 版本与文档

- [ ] `VERSION` 文件已更新
- [ ] `quant_data/__init__.__version__` 与 `VERSION` 一致
- [ ] `CHANGELOG.md` 已更新（新增版本区块）
- [ ] `docs/` 相关文档已同步（如有功能变更）

## 发布执行

> ⚠️ **以下命令涉及 Tag / 推送，必须用户明确指令才能跑**。Agent 不主动执行。

```bash
# 1. 升级版本号
python scripts/release/bump_version.py patch   # 或 minor / major

# 2. 执行发布（自动打 Tag、生成启动脚本）
python scripts/release/release.py

# 3. 推送到远程
git push origin main --follow-tags
```

- [ ] 版本号升级脚本已执行
- [ ] Tag 已打：`git tag -l | tail -5`
- [ ] 启动脚本已生成：`run_v{x}.{y}.{z}.bat`
- [ ] 变更已推送到 GitHub

## 发布后验证

- [ ] GitHub 上 Tag 可见
- [ ] `git log --oneline -5` 显示版本提交
- [ ] 新版本的 `run_v*.bat` 可正常启动系统
- [ ] 无新增 `.pyc` / `__pycache__` 误提交

---

## 紧急热修流程（hotfix）

1. 从 `main` 切出 `hotfix/{问题简述}`
2. 修复代码，通过最小测试
3. 直接升级 patch 版本：`python scripts/release/bump_version.py patch`
4. 合并到 `main`，打 Tag，推送
5. 非回测相关 hotfix 可跳过完整回测门禁；**回测、复权、数据加载、`DataUpdateService` 相关 hotfix 必须跑最小回测**，并记录修复原因

---

*本清单跟随版本发布流程同步更新。当前位置 `skills/agent-adapters/release-checklist.md`，作为 Claude Code 与 Codex 共用的发版任务专属 skill。*
