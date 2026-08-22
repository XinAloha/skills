# 多轮操作行为记忆档 — 索引

> Claude 的跨会话工作记忆（随版本控制）。每个记忆一个文件，正文为 bullet-point；相关记忆用 `[[slug]]` 链接。仓库级操作规范另见 [`../memory.md`](../memory.md)（管理员手册），两者不同。

- [Skills 导入流水线](skills-import-pipeline.md) — 克隆→manifest→import→index→docs 的既定流程
- [Skills 内容组织模型](skills-organize-content.md) — 分类目录/kind/cluster/前缀/aux 判定
- [Git Bash 的 GitHub 凭据](github-credentials-git-bash.md) — GCM/token/SSH/gh 如何确认
- [Git 提交 Co-Authored-By 尾注](git-commit-co-authored-by.md) — 提交信息/PR body 署名规范
- [Windows 下无 bash 直跑](windows-powershell-no-bash.md) — Bash 工具是 Git Bash；python 占位符坑
- [工作记忆档保存路径](working-memory-repo-path.md) — 本档位置与规则、与 memory.md 区分
- [GitHub MCP 超长输出](github-mcp-long-output.md) — 落盘文件按字符区间读取
- [IDE 下 Git 约束](ide-git-constraints.md) — 无交互式命令、默认分支先建分支
- [权限模式与自动授权](permission-mode-auto-approve.md) — 被拒则调整、破坏性动作先确认
- [quantskills 全量导入](quantskills-bulk-import.md) — 149 量化 skill 的 catalog 解析+批量克隆+manifest 流水线
