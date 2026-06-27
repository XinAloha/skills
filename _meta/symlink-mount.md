# 软链接挂载到其他项目

本仓库的 skill 目录是 **自包含** 的：每个 skill 目录里所有 `scripts/` / `references/` / `assets/` 路径都相对 `SKILL.md` 解析。这意味着你可以用一条软链接 / Junction 把整个 skill 挂载到任何其他项目里，而不需要复制文件。

> 升级本仓库的 skill ⇒ 所有挂载它的项目自动得到新版本。这也是为什么我们维护单一事实源 + SOURCE.md 跟踪。

## Linux / macOS

```bash
# 把单个 skill 挂到目标项目
cd /path/to/target-project
mkdir -p .claude/skills .codex/workflows/skill
ln -s /abs/path/to/skills/content/humanizer-zh .claude/skills/humanizer-zh
ln -s /abs/path/to/skills/content/humanizer-zh .codex/workflows/skill/humanizer-zh
```

## Windows

PowerShell（推荐 Junction，因为不需要管理员权限，跨盘符可用）：

```powershell
# 目录 junction（无需管理员）
New-Item -ItemType Junction `
  -Path .\.claude\skills\humanizer-zh `
  -Target E:\Project\Quantitative_Trading\skills\content\humanizer-zh
```

如果要用真正的符号链接：

```powershell
# 需要开发者模式或管理员
New-Item -ItemType SymbolicLink `
  -Path .\.claude\skills\humanizer-zh `
  -Target E:\Project\Quantitative_Trading\skills\content\humanizer-zh
```

Git Bash：

```bash
# 仓库内已经使用过的形式，参考 .codex/workflows/skill/
cmd <<'EOF'
mklink /J ".claude\skills\humanizer-zh" "E:\Project\Quantitative_Trading\skills\content\humanizer-zh"
EOF
```

## 整组挂载（按 category）

很多时候你想让目标项目继承一整组能力，比如所有 `content/` 系列。直接挂目录：

```bash
ln -s /abs/path/to/skills/content .claude/skills/content
```

之后目标 agent 入口写 `skill/content/<skill-name>/SKILL.md` 就能找到所有内容。

## 只挂某个 cluster

集群里的 skill 互相依赖（例如 `dbs-state` 集群的 `state-save` / `state-restore` / `state-report`）。要么挂整个 `business/` 目录，要么单独挂三个 skill 并保持它们对外的目录名一致（成员之间靠相对路径找彼此）。

## 不要做的事

- 不要把单独的 `SKILL.md` 文件孤立拷贝出来——composite skill 会因为找不到自己的 `scripts/` / `references/` 而损坏。
- 不要把同一个 skill 拷贝多份散到不同项目里——这样上游修复时不能传播。
- 不要在挂载的项目里直接修改 skill 的 `SKILL.md`——会改到事实源。本地分歧请在目标项目里建立 wrapper。
