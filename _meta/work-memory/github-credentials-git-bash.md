# 记忆项：在 Git Bash 中确定访问 GitHub 的凭据

**slug:** `github-credentials-git-bash` · **类型:** reference · **相关:** [[skills-import-pipeline]] [[github-mcp-long-output]]

在 Git Bash（Windows）中确认 git 访问 GitHub 用的凭据来源：

- 查凭据 helper：`git config --get credential.helper`（`manager` / `manager-core` 表示走 Windows 凭据管理器 GCM）。
- 查全局配置：`git config --global --list`。
- 查 `gh` 登录态：`gh auth status`（MCP / gh CLI 可能用独立 token）。
- 查环境变量：`GIT_ASKPASS`、`SSH_AUTH_SOCK`（SSH 密钥）。
- 实测连通：`git ls-remote https://github.com/<owner>/<repo>` 看是否免密成功。

**Why:** 克隆/推送前需确认走 HTTPS+token、SSH key 还是 GCM，避免授权失败。
**How to apply:** 导入流水线（[[skills-import-pipeline]]）克隆上游仓库前先确认凭据可用；也可用 GitHub MCP 工具代替裸 git。
