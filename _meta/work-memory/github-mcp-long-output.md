# 记忆项：GitHub MCP 搜索结果超长输出的处理

**slug:** `github-mcp-long-output` · **类型:** reference · **相关:** [[windows-powershell-no-bash]] [[github-credentials-git-bash]]

当 GitHub MCP 工具（`search_repositories`、`list_*` 等）返回超大结果（如 `org:quantskills` 全量仓库，可达 60 万+ 字符）时：

- 工具报错 "exceeds maximum allowed tokens"，并把完整输出**落盘保存**到：
  `C:\Users\Aloha\.claude\projects\<project>\<session>\tool-results\mcp-github-*.txt`
- 该文件**行太长**（单行可达 60 万+ 字符），`Read` 的 offset/limit **行式分块无效**。
- 必须用**字符范围切片**读取：`python read()[A:B]`、`dd`、`cut -c` 等（Windows 下用 `/d/Developer_Tools/Anaconda/python`，见 [[windows-powershell-no-bash]]）。
- 优先做法：用 `jq` 做结构化查询只取需要字段，或按字符区间分块读完，控制上下文占用。
- 研究上游仓库时与 [[github-credentials-git-bash]]、[[skills-import-pipeline]] 配合。

**Why:** 避免手动逐行读超长文件，节省上下文。
**How to apply:** 遇超长 MCP 输出 → 直接按字符区间用 Python 读 + jq 过滤字段，不硬读全文。
