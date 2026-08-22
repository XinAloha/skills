# 记忆项：在本仓库导入外部 skill 的流水线

**slug:** `skills-import-pipeline` · **类型:** project · **相关:** [[github-credentials-git-bash]] [[windows-powershell-no-bash]] [[git-commit-co-authored-by]] [[skills-organize-content]]

`e:\Project\Quantitative_Trading\skills` 是多源 agent skill 集合，导入上游 skill 走既定流水线，不手抄：

- **1. 克隆上游仓库**到 `_external_skills/<reponame>/`（该目录已 gitignore，作暂存源，不入库）。
- **2. 在 `_meta/import-manifest.tsv` 每 skill 加一行**：`source_subpath \t target_subpath \t kind \t repo \t repo_path \t cluster \t notes`（TSV，CRLF 行尾）。
- **3. 跑 `import_skills.py`**：复制到 `skills/<target>/`、生成 `SOURCE.md`（记录上游/kind/cluster/挂载片段/更新流程）。
- **4. 跑 `build_index.py`**：重生 `INDEX.md`（自动更新 imported/native 计数与来源表）。
- **5. 更新 `README.md`** 计数/来源表；新增集群补 `_meta/clusters.md`。

关键细节：
- **kind**：`atomic`（单 SKILL.md）/ `composite`（SKILL.md + scripts/references/assets）/ `composite-danger`（逆向 API）。
- **cluster**：设计上互相串联的 skill 共用一个集群名（`dbs-core`、`dbs-state`、`humanizer` 等）；独立 skill 用 `-`。
- **重跑安全**：跳过暂存源已不存在的行（打印 `Missing sources`），不会动已导入 skill。
- **`IMPORT_DATE` 硬编码**在脚本里，运行时覆盖当天日期又不动已提交脚本：
  `import import_skills as I; I.IMPORT_DATE="YYYY-MM-DD"; I.main()`
- **前缀策略**：纯作者命名空间前缀剥掉（`dbs-`→`diagnosis`）；产品/命令名前缀保留（`ponytail-audit` 不剥）。
- 前置依赖：确认上游可访问（[[github-credentials-git-bash]]）、用真实 python（[[windows-powershell-no-bash]]）、提交加尾注（[[git-commit-co-authored-by]]）。

**Why:** 保持单一事实源 + 分类 + kind/cluster 体系井然；改导入 skill 必须在它的 `SOURCE.md` → `Local modifications` 记账。
**How to apply:** 拿到新上游仓库按 1-5 步走；覆盖更新则重跑 3-5 并更新 manifest 日期。
