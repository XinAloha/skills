# 记忆项：在本仓库组织内容

**slug:** `skills-organize-content` · **类型:** project · **相关:** [[skills-import-pipeline]]

`skills/` 的组织模型：

- **单一事实源**：`skills/` 是事实源；平台入口和其他项目靠软链接接入，不复制。
- **分类目录**：engineering / testing / git / governance / methodology / workmode / meta / misc / domain / agent-adapters / content / productivity / business / ai-backends / loop-engineering 等。详见 `README.md` 目录结构表。
- **kind**：`atomic` / `composite` / `composite-danger`（判定：含 scripts/references/assets → composite；逆向 API → composite-danger）。
- **cluster**：设计上串联的 skill 共用一个集群名，见 `_meta/clusters.md`；独立 skill 用 `-`。
- **前缀策略**：纯作者命名空间前缀剥掉（`dbs-`→`diagnosis`、`baoyu-`→`article-illustrator`）；产品/命令名前缀保留（`ponytail-audit` 不剥，剥了断交叉引用）。
- **aux 目录陷阱**：`agents/`（含 openai.yaml 等）是平台辅助配置，随每个 dbskill skill 一起导入，**不是** composite 标记（如 content/ai-check 有 agents/ 但属 atomic）。
- 每个导入 skill 自带 `SOURCE.md`（记录上游、kind、cluster、挂载片段、更新流程）。

**Why:** 让 skill 目录井然、可路由、可挂载；判断 kind/归属有明确规则。
**How to apply:** 新增 skill 按此模型归到对应分类 + 定 kind/cluster；路由用户需求时先翻 `INDEX.md` 和 `_meta/clusters.md` 再回答。
