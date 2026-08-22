# 记忆项：工作记忆档的特定保存路径

**slug:** `working-memory-repo-path` · **类型:** reference · **相关:** [[skills-import-pipeline]]

本《多轮操作行为记忆档》的存放位置与规则：

- **主存位置（随版本控制）**：`e:\Project\Quantitative_Trading\skills\_meta\work-memory\` —— 本仓库内，多个独立记忆文件 + 一个 `MEMORY.md` 索引。
- 每个记忆一个文件，文件头含 `slug` / `类型` / `相关` 元信息，正文为 bullet-point。
- 索引文件 `MEMORY.md`：每文件一行 `- [标题](文件.md) — 一句话`，便于扫读。
- 相关记忆用 `[[slug]]` 链接（slug 即文件名）。
- **区分**：本目录是"Claude 跨会话召回的多轮操作行为记忆"；`_meta/memory.md` 是"仓库管理员操作手册"（角色/规范/流水线），两者不同，别混。
- 与 Claude 项目记忆库 `C:\Users\Aloha\.claude\projects\...\memory\` 是两套，本档以仓库内为准。

**Why:** 需要知道这份工作记忆写到哪里、如何被召回；避免写错位置造成两份漂移。
**How to apply:** 新增记忆写本目录 + 更新 `MEMORY.md` 索引；仓库级操作规范写 `_meta/memory.md`。
