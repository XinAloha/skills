# 记忆项：quantskills 社区全量导入的批量流水线

**slug:** `quantskills-bulk-import` · **类型:** project · **相关:** [[skills-import-pipeline]] [[skills-organize-content]] [[github-mcp-long-output]] [[github-credentials-git-bash]]

把 [quantskills](https://github.com/quantskills/quantskills) 社区的 149 个量化 skill 全量整合进本项目的经验（2026-08-21）：

- **`quantskills/quantskills` 是导航/目录仓库**，本身无任何 SKILL.md（SKILL.md=0），只含 `site/catalog.json`（158 资产元数据）+ README 快照。真正的 skill 在各自独立仓库 `quantskills/<name>`，catalog.json 里有每个的上游 URL。
- **catalog.json schema**：每个 asset 有 `name`/`url`/`category`(01-10)/`subcategory`/`project_type`(skill|agent)/`stage`/`summary_zh`/`description`。catalog 无 star 字段（要 star 需另查 GitHub API）。
- **批量流程**（用 `_meta/generate_quant_manifest.py` 辅助）：
  1. 从 `catalog.json` 提取 skill 清单（name/category/subcategory/url/summary_zh）→ `_external_skills/_quant_skill_list.txt`。
  2. 批量浅克隆：`git clone --depth 1 https://github.com/quantskills/<name>.git` 到 `_external_skills/quantskills-skills/<name>/`（网络不稳定时逐个重试）。
  3. 生成 manifest：category→`quant/<subdir>`（01 data / 02 factors / 03 market / 04 risk / 05 backtest / 06 models / 07 validation / 08 news / 10 infra），kind 按目录内是否含 references/scripts/templates/assets/evals 判定（→135 composite / 14 atomic），repo=`quantskills/<name>`，repo_path=`/`，cluster=`-`。
  4. `import_skills.py`（IMPORT_DATE 覆盖）复制到 `quant/<subdir>/<name>` + 生成 SOURCE.md；`build_index.py` 重建 INDEX。
- **上游 skill 结构**：每个独立仓库含 `SKILL.md` + `references/`/`scripts/`/`evals/`/`tests/`/`agents/`；`agents/`（cursor-rule.mdc、openai.yaml）是平台辅助配置，**不算** composite 标记。
- **build_index 需改**：`CATEGORY_ORDER` 加 `"quant"` + `CATEGORY_BLURB`；`list_native_skills` 里目录只有含 `SKILL.md` 才算 skill（否则 `quant/<subdir>` 容器会被误判为 native）。
- **gitignore 坑**：quant skill 自带嵌套 `.gitignore`，导致 `git check-ignore quant/` 误报忽略；实际 `git add quant/` 正常暂存全部 9425 文件，以 `git status -uall` 实况为准。
- 克隆网络不稳：GitHub port 443 偶发超时，重试即可。

**Why:** 社区导航仓库无实际内容，需按 catalog 解析 + 批量克隆 + 批量生成 manifest，流程与单 skill 导入不同。
**How to apply:** 再整合 quantskills 其他资产（如 agent、或 catalog 更新）时复用 generate_quant_manifest.py + 本流程。
