# Memory — Skills 仓库管理员的操作记忆

> 本文件是 Claude 作为本仓库（`skills/`）**管理员 / 路由员**的持久操作记忆，**随仓库版本控制**。每次进入仓库都知道：自己是谁、按什么规范干、怎么把用户需求路由到既有 skill。补充 [`symlink-mount.md`](symlink-mount.md) / [`clusters.md`](clusters.md) / [`import-manifest.tsv`](import-manifest.tsv) 这些「仓库长什么样」之外，**「怎么操作」**的层面。

## 我的角色

本仓库的 skill 管理员。两条核心职责：

1. **组织**：保持单一事实源 + 分类目录 + kind/cluster 体系井然。导入、归类、建索引都走既定流水线，不手抄。
2. **路由**：用户描述需求时，**优先映射到既有 skill**，而不是现造一个。先翻 [`../INDEX.md`](../INDEX.md) 和 [`clusters.md`](clusters.md) 再回答。

### 仓库组织模型（速查）

- **单一事实源**：`skills/` 是事实源；平台入口（`.claude/workflows/skill/` 等）和其他项目靠软链接接入（见下文「软链接到其他项目」）。
- **分类目录**：engineering / testing / git / governance / methodology / workmode / meta / misc / domain / agent-adapters / content / productivity / business / ai-backends。详见 [`../README.md`](../README.md) 的目录结构表。
- **kind**：`atomic`（单 `SKILL.md`）/ `composite`（`SKILL.md` + `scripts/`/`references/`/`assets/`）/ `composite-danger`（逆向 API）。
- **cluster**：设计上互相串联的 skill 共用一个集群名，见 [`clusters.md`](clusters.md)。
- **每个导入 skill 自带 `SOURCE.md`**：记录上游、kind、cluster、挂载片段、更新流程；改导入 skill 必须在它的 `SOURCE.md` → `Local modifications` 记账。

### 导入流水线（拿到新上游仓库时）

1. 把克隆仓库挪进 `_external_skills/<reponame>/`（已 gitignore，作暂存源）。
2. 在 `import-manifest.tsv` 按 skill 各加一行：`source_subpath \t target_subpath \t kind \t repo \t repo_path \t cluster \t notes`。
3. 跑 `import_skills.py` → 复制 skill 到 target、生成 `SOURCE.md`。
4. 跑 `build_index.py` → 重生 `INDEX.md`。
5. 更新 `README.md` 计数 / 来源表；新集群还要补 `clusters.md`。

### 本机操作坑

- PATH 上的 `python` 是 Windows Store 占位符，返回 exit 49 无输出。用真实解释器 `/d/Developer_Tools/Anaconda/python`。
- `import_skills.py` 重跑会扫全 manifest，但**跳过**暂存源已不存在的行（打印 `Missing sources`），所以重跑安全，不会动到已导入的 skill。
- 脚本 `IMPORT_DATE` 硬编码 `2026-06-27`。给新批次打当天日期又不动已提交脚本：`import import_skills as I; I.IMPORT_DATE="YYYY-MM-DD"; I.main()`。
- **前缀策略**：纯作者命名空间前缀剥掉（`dbs-`→`diagnosis`、`baoyu-`→`article-illustrator`）；但产品 / 命令名前缀保留（`ponytail-audit` 不剥，因为 `/ponytail-audit` 是命令名、剥了会断交叉引用）。

## 软链接到其他项目（背景 + 执行动作）

> 完整命令见 [`symlink-mount.md`](symlink-mount.md)。这里只存**决策层**：为什么这么做 + 怎么做的关键动作。

### 背景（为什么用软链接，不复制）

- **单一事实源 → 自动传播**：本仓库是事实源。上游 skill 在这里更新后，所有挂载它的项目自动拿到新版。复制文件会断掉这条传播链——源一改进，副本就腐烂。
- **skill 目录自包含**：每个 skill 目录里 `scripts/`/`references/`/`assets/` 都相对自己的 `SKILL.md` 解析，所以一条软链接就够，目标项目不用改路径。
- **composite 必须整目录挂**：composite skill 少了 `scripts/`/`references/`/`assets/` 就坏。所以永远挂**整个 skill 目录**，绝不挂单个 `SKILL.md`。
- **编辑单向流**：目标项目不得改挂载来的 `SKILL.md`——那会污染所有人的事实源。分歧在目标项目里写 wrapper 解决，不改源。

### 执行动作

0. **定范围**：单个 skill / 整 category / 整 cluster。cluster 成员靠相对路径互找，要挂就全挂且目录名一致。
1. **Linux / macOS**：
   ```bash
   cd /path/to/target-project && mkdir -p .claude/skills
   ln -s /abs/path/to/skills/<category>/<slug> .claude/skills/<slug>
   # 整 category： ln -s /abs/path/to/skills/<category> .claude/skills/<category>
   ```
2. **Windows（优先 Junction，免管理员、跨盘符可用）**：
   ```powershell
   New-Item -ItemType Junction -Path .\.claude\skills\<slug> -Target E:\Project\Quantitative_Trading\skills\<category>\<slug>
   ```
   （真 `SymbolicLink` 需开发者模式或管理员；Windows 上优先 Junction。）
3. **agent 入口**指向 `skill/<slug>/SKILL.md`。

**必须 / 禁止**：
- ✅ 挂整个 skill 目录 + 绝对目标路径；✅ cluster 全挂且名字一致。
- ❌ 别拷单个 `SKILL.md`（composite 会坏）；❌ 别拷多份散到不同项目（断传播）；❌ 别在目标里改挂载的 `SKILL.md`（污染源，用 wrapper）。

**本仓库常用挂载目标**：
- 懒人最小代码 → `workmode/ponytail` 全家桶 6 件（`ponytail` / `-review` / `-audit` / `-debt` / `-gain` / `-help`）。
- 中文去 AI 味 → `content/humanizer-zh` + `content/ai-check` + `content/format-markdown`（`humanizer` 集群）。
- 商业诊断 → 整个 `business/` 目录（`dbs-core` + `dbs-state` 集群）。
