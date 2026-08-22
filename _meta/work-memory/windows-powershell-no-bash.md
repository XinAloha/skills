# 记忆项：Windows 下不能直接运行 bash 命令

**slug:** `windows-powershell-no-bash` · **类型:** feedback · **相关:** [[skills-import-pipeline]] [[github-mcp-long-output]]

Claude 在 Windows 环境下的 Bash 工具跑的是 **Git Bash（POSIX sh）**，不是 cmd.exe / PowerShell：

- 用 Unix 语法：`/dev/null` 而非 `NUL`、正斜杠、`$VAR` 而非 `%VAR%`/`$env:VAR`。
- **不要**在 Bash 工具里跑 PowerShell 专属命令/语法（如 `New-Item -ItemType`）。PowerShell 专属操作（建 Junction 等）按 [[skills-import-pipeline]] 里记录的 Windows 命令片段另走 PowerShell。
- **PATH 上的 `python` 是 Windows Store 占位符**（返回 exit 49 无输出）——必须用真实解释器 `/d/Developer_Tools/Anaconda/python`。

**Why:** Bash 工具基于 Git Bash，语义与 PowerShell 不同；`python` 被 Store 占位符劫持。
**How to apply:** 在 Bash 工具用 POSIX 语法；Python 脚本一律用 `/d/Developer_Tools/Anaconda/python` 调用。
