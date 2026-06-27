# 架构 — kind（atomic / composite / composite-danger）与 cluster

本仓库是一个 **skill 集合大全**：既要容纳大量从社区收集的高质量 skill，又要保持每个 skill 可以独立挂载到其他项目里使用。两条正交的维度共同描述一个 skill：

- **kind**（三选一，描述「单个 skill 长什么样」）：`atomic` / `composite` / `composite-danger`
- **cluster**（可选，描述「这个 skill 与哪些 skill 设计上串联使用」）：见 [`clusters.md`](clusters.md)

## 三种 kind

### atomic — 原子 skill

只有一个 `SKILL.md`，没有内部 `scripts/`、`references/`、`assets/`。整个能力就是一段大型 prompt 加少量上下文规则。

- 例子：`workmode/caveman.md`、`workmode/goal-clarify/SKILL.md`、`business/diagnosis/SKILL.md`
- 特征：**普攻**，一发一个动作；调用方只需把 `SKILL.md` 注入上下文即可
- 挂载：把整个目录（或者单个 `.md`）软链接到目标项目

### composite — 复合 skill

`SKILL.md` + `scripts/` + `references/` + 可选 `assets/`。`SKILL.md` 是入口，但执行过程中会调用本目录内的脚本或读取参考资料，构成一个 **自包含的多步流水线**。

- 例子：`content/guizang-ppt/`（含 `assets/template.html` 等 + 多个 reference）、`productivity/notebooklm/`（含 Python 脚本 + 浏览器自动化）、`engineering/diagram/`（含 TS 生成脚本）
- 特征：**一招一整套**，单次调用本身就是一个动态流程
- 挂载：必须软链接 **整个目录**，让所有相对路径能解析

### composite-danger — 危险复合 skill

`composite`，但依赖逆向工程的非官方 API、未公开 endpoint 或浏览器会话注入。**上游会随时失效**。

- 例子：`ai-backends/gemini-web/`、`productivity/x-to-markdown/`
- 调用前：通读 `SOURCE.md` 中的 DANGER 警示；准备 fallback。

## cluster — 流水线集群（与 kind 正交的组合机制）

多个 skill 各自独立（每个都有自己的 kind），但设计上互相组合成一条流程。集群名写在每个成员 `SOURCE.md` 的 `Cluster` 字段，并在 `INDEX.md` 末尾汇总。一个 skill 要么不属于任何集群，要么只属于一个集群。

- 例子：`business/state-save` → `business/state-restore` → `business/state-report` 是 dbskill 的诊断状态快照三件套，集群名 `dbs-state`。
- 一般用法：在调用入口 skill（router/orchestrator）里按顺序调用集群里的其他成员。
- 注意：cluster 不是第四种 kind —— 集群里每个成员仍各自是 atomic 或 composite。

## 何时升级 / 拆分

- atomic 的 `SKILL.md` 超过 ~600 行，或开始出现 `bash:` `python:` 大段代码段 → 考虑拆出 `scripts/` 与 `references/`，升格为 composite。
- composite 内部 `scripts/` 出现多个互相独立的子流程（每个都能单独使用） → 考虑拆分为多个 atomic + 一个 router atomic（参考 `business/dbs-router`）。
- 两个不同来源做的事情粒度相同 → 暂时各自保留为 sibling；在它们的 `SOURCE.md` 中互相引用；后续可以新建一个共同的 atomic「门面」skill 让用户选择实现。

## 与上游同步

每个导入的 skill 目录里都有 `SOURCE.md`：

- `Repository` / `Skill path in repo` / `Canonical URL` — 上游定位三件套
- `Imported on` — 此次拷贝的日期
- `Updating from upstream` — 拉取上游更新的步骤
- `Local modifications` — 本仓库做过的本地修改，更新前必须 review

详见 `_meta/clusters.md`、`_meta/symlink-mount.md`、`_meta/import-manifest.tsv`、`_meta/import_skills.py`、`_meta/build_index.py`。
