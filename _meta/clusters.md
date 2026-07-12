# Cluster — 流水线集群

集群指 **多个 skill 设计上互相组合**。它们各自仍是独立 skill（可以单独挂载），但常见用法是按顺序调用。

每个集群成员的 `SOURCE.md` 都有 `Cluster: <name>` 字段。导入 manifest 在 `_meta/import-manifest.tsv` 的 `cluster` 列定义。

下面列出仓库内维护的流水线集群。同一集群中的 Skill 仍可独立调用，也可以按推荐顺序组合使用。

## `loop-engineering` — 项目级智能体循环工程

- [`loop-engineering/design-loop-project`](../loop-engineering/design-loop-project/) — 总入口，协调评估、契约、状态、工具集和审计
- [`loop-engineering/qualify-loop-task`](../loop-engineering/qualify-loop-task/) — 判断任务适合循环、确定性自动化还是人工主导
- [`loop-engineering/specify-loop-contract`](../loop-engineering/specify-loop-contract/) — 定义目标证据、预算、停止和升级条件
- [`loop-engineering/design-loop-state`](../loop-engineering/design-loop-state/) — 设计持久状态、尝试日志、检查点和恢复
- [`loop-engineering/build-loop-harness`](../loop-engineering/build-loop-harness/) — 配置指南、反馈传感器、观测与权限边界
- [`loop-engineering/audit-loop-project`](../loop-engineering/audit-loop-project/) — 用正反例验证安全性和运行就绪度
- [`loop-engineering/operate-loop-run`](../loop-engineering/operate-loop-run/) — 分流、隔离执行、独立验证、交接与恢复
- [`loop-engineering/verify-loop-delivery`](../loop-engineering/verify-loop-delivery/) — 独立审核实施代理代码，输出 pass/reject/escalate 裁决
- [`loop-engineering/improve-loop-system`](../loop-engineering/improve-loop-system/) — 将失败、审查与漂移转化为受验证的系统改良

**典型流程：** `qualify-loop-task` → `specify-loop-contract` → `design-loop-state` → `build-loop-harness` → `operate-loop-run` → `verify-loop-delivery` → `audit-loop-project` → `improve-loop-system`；新建完整工程时由 `design-loop-project` 统一编排。

## `dbs-state` — dbskill 诊断状态快照

- [`business/state-save`](../business/state-save/) — 把当前诊断结论 / 已淘汰路径 / 推荐下一步保存为本地 Markdown
- [`business/state-restore`](../business/state-restore/) — 从本地快照恢复最近一次诊断状态
- [`business/state-report`](../business/state-report/) — 合并多次 `state-save` 快照，生成可分享的 Markdown 报告

**典型流程：** 一边对话 → `state-save` 写快照 → 中断后用 `state-restore` 续上 → 阶段性产物用 `state-report` 输出。

## `dbs-core` — dbskill 调度入口

- [`business/dbs-router`](../business/dbs-router/) — 主路由：识别用户意图并派发到具体的 `dbs-*` skill

**用法：** 一次加载整组 `business/` 目录 → 让 router 作为入口；它会自己挑用 diagnosis / decision / good-question / goal 等成员。

## `humanizer` — 中文文本去 AI 痕迹

- [`content/humanizer-zh`](../content/humanizer-zh/) — 检测并改写：把 AI 味的中文改自然
- [`content/ai-check`](../content/ai-check/) — 检测：只识别 AI 痕迹并出报告
- [`content/format-markdown`](../content/format-markdown/) — 排版：把成稿 Markdown 美化

**典型流程：** 草稿 → `ai-check` 出诊断报告 → `humanizer-zh` 改写 → `format-markdown` 出版式化最终稿。

## `slide` — 演示文档 / PPT

- [`content/guizang-ppt`](../content/guizang-ppt/) — 横滑 web PPT，单 HTML 文件，含 WebGL 背景与编辑/瑞士两种风格
- [`content/slide-deck-baoyu`](../content/slide-deck-baoyu/) — 把长内容拆成幻灯片图集，含 PDF/PPTX 合并脚本

**取舍：** 想要**网页交互**的演示 → guizang-ppt；想要**导出图片/PDF/PPTX** → slide-deck-baoyu。

## `card` — 社交卡片

- [`content/guizang-social-card`](../content/guizang-social-card/) — Guizang 系社交卡片 + 微信公众号封面，瑞士/编辑双风格 HTML
- [`content/xhs-images-baoyu`](../content/xhs-images-baoyu/) — 小红书风格信息流卡片，12 风格 × 8 布局 × 3 配色

**取舍：** 标准社交平台、需要专业设计 → guizang-social-card；批量小红书图卡、需要预设套餐 → xhs-images-baoyu。

## `visual` — 文章配图 / 视觉资产

- [`content/article-illustrator`](../content/article-illustrator/) — 段落级配图规划与 prompt 生成
- [`content/cover-image`](../content/cover-image/) — 文章封面（type × palette × rendering × text × mood）
- [`content/infographic`](../content/infographic/) — 信息图（21 布局 × 22 风格）
- [`content/comic`](../content/comic/) — 知识漫画分镜与生成

**典型流程：** 文章定稿 → `article-illustrator` 规划插图位 → 各位置按需求挑 `cover-image` / `infographic` / `comic` → 出 prompt → 走 `ai-backends/image-gen` 实际出图。

## `extract` — URL / 视频 / 推文 → Markdown

- [`productivity/url-to-markdown`](../productivity/url-to-markdown/) — 通用 URL，含 X / YouTube / HN 站点适配器
- [`productivity/youtube-transcript`](../productivity/youtube-transcript/) — 专攻 YouTube 字幕 + 章节 + 说话人
- [`productivity/x-to-markdown`](../productivity/x-to-markdown/) — 专攻 X/Twitter（DANGER：逆向 API）

**取舍：** 杂网页 → `url-to-markdown` 起步；上面失败再上 YouTube/X 专用的。

## `publish` — 发布到平台

- [`content/markdown-to-html`](../content/markdown-to-html/) — 兼容微信主题的样式化 HTML，可手动复制粘贴
- [`content/post-to-wechat`](../content/post-to-wechat/) — 微信公众号自动发布（API 或 Chrome CDP）
- [`content/post-to-weibo`](../content/post-to-weibo/) — 微博自动发布（CDP）
- [`content/post-to-x`](../content/post-to-x/) — X 自动发布（多通道）

**典型流程：** 终稿 → `markdown-to-html` 出 HTML → 选定平台用对应 `post-to-*` 自动发布。

## `chatroom` — 多角色思辨

- [`methodology/chatroom`](../methodology/chatroom/) — 通用多专家会议室
- [`methodology/chatroom-austrian`](../methodology/chatroom-austrian/) — 奥地利学派会议室（Hayek / Mises / Claude）

**取舍：** 想自选嘉宾 → `chatroom`；要 Austrian 经济学视角 → `chatroom-austrian`。

## `ponytail` — 懒人最小代码工具箱

- [`workmode/ponytail`](../workmode/ponytail/) — 主模式：写码前先爬「YAGNI → stdlib → native → 依赖 → one line → 最小可用」阶梯，懒于方案、不懒于读码
- [`workmode/ponytail-review`](../workmode/ponytail-review/) — diff 级过度工程审查，一行一条（delete/stdlib/native/yagni/shrink）
- [`workmode/ponytail-audit`](../workmode/ponytail-audit/) — 整库过度工程审计，按可删减量排序，只出报告不改码
- [`workmode/ponytail-debt`](../workmode/ponytail-debt/) — 收集代码里所有 `ponytail:` 注释成「技术债台账」，避免「以后做」烂成「永远不做」
- [`workmode/ponytail-gain`](../workmode/ponytail-gain/) — 展示 ponytail 的基准测试成绩板（代码/成本/速度）
- [`workmode/ponytail-help`](../workmode/ponytail-help/) — 全部 ponytail 模式/技能/命令速查卡

**典型流程：** 写码时开 `ponytail` 模式（lite/full/ultra）→ 写完跑 `ponytail-review` 审 diff / `ponytail-audit` 审整库 → 用 `ponytail-debt` 把刻意留下的捷径登记成债 → `ponytail-help` 速查、`ponytail-gain` 看收益。与 `workmode/caveman`（极简行文）、`workmode/tame-vibe-coding`（认知/技术债控制）同属工作模式，可叠加。

---

## 还没成簇的「孤狼」也能强强联合

集群只标了 **upstream 设计层面互相绑定** 的那些。下游用户可以自由组合任意 atomic + composite，例如：

- `methodology/good-question` → `business/diagnosis` → `business/state-save` → `business/state-report`
- `productivity/url-to-markdown` → `methodology/hv-analysis` → `content/khazix-writer` → `content/markdown-to-html` → `content/post-to-wechat`

写好自己的 router（atomic skill 即可）来描述这种组合，新人就能照搬。
