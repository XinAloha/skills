# INDEX — All skills registry

Auto-generated companion to `README.md`. One row per skill. Re-run `_meta/build_index.py` after adding or moving skills.

Legend for **Kind**:

- `atomic` — single `SKILL.md`; no internal tooling. Acts as one prompt-level capability.
- `composite` — `SKILL.md` + bundled `scripts/` / `references/` / `assets/`. Internal multi-step logic; one self-contained pipeline.
- `composite-danger` — composite skill that depends on reverse-engineered or unofficial APIs; may break upstream without notice.
- `cluster: <name>` (in Cluster column) — multiple skills designed to be chained. See `_meta/clusters.md`.
- `native` — authored in this repo, not imported.

**Totals:** 54 imported · 54 native · 108 skills across 14 categories.

## `engineering/`

Code/infra: style, interfaces, docs, integration, security, diagrams, app extraction.

| Slug | Kind | Cluster | Source | Summary |
|---|---|---|---|---|
| [`code-style.md`](engineering/code-style.md) | native | — | this repo | — |
| [`design-patterns.md`](engineering/design-patterns.md) | native | — | this repo | — |
| [`documentation.md`](engineering/documentation.md) | native | — | this repo | — |
| [`extensibility.md`](engineering/extensibility.md) | native | — | this repo | — |
| [`external-integration.md`](engineering/external-integration.md) | native | — | this repo | — |
| [`new-feature-process.md`](engineering/new-feature-process.md) | native | — | this repo | — |
| [`reusable-patterns.md`](engineering/reusable-patterns.md) | native | — | this repo | — |
| [`security.md`](engineering/security.md) | native | — | this repo | — |
| [`diagram`](engineering/diagram/) | `composite` | `—` | [JimLiu/baoyu-skills](https://github.com/JimLiu/baoyu-skills/tree/main/skills/baoyu-diagram) | Professional dark-themed SVG diagrams (architecture/flow/sequence/structural/mindmap/timeline). |
| [`electron-extract`](engineering/electron-extract/) | `composite` | `—` | [JimLiu/baoyu-skills](https://github.com/JimLiu/baoyu-skills/tree/main/skills/baoyu-electron-extract) | Extract JS/resources from installed Electron apps (.asar bundles). |

## `testing/`

Tests & quality: collectors, DB, data quality, recovery, pipeline tests.

| Slug | Kind | Cluster | Source | Summary |
|---|---|---|---|---|
| [`collector-testing.md`](testing/collector-testing.md) | native | — | this repo | — |
| [`data-quality.md`](testing/data-quality.md) | native | — | this repo | — |
| [`database-testing.md`](testing/database-testing.md) | native | — | this repo | — |
| [`fault-recovery.md`](testing/fault-recovery.md) | native | — | this repo | — |
| [`pipeline-testing.md`](testing/pipeline-testing.md) | native | — | this repo | — |
| [`test-strategy.md`](testing/test-strategy.md) | native | — | this repo | — |

## `git/`

Git workflow + release engineering.

| Slug | Kind | Cluster | Source | Summary |
|---|---|---|---|---|
| [`git-branch-workflow.md`](git/git-branch-workflow.md) | native | — | this repo | — |
| [`git-code-review.md`](git/git-code-review.md) | native | — | this repo | — |
| [`git-commit-convention.md`](git/git-commit-convention.md) | native | — | this repo | — |
| [`git-rollback-recovery.md`](git/git-rollback-recovery.md) | native | — | this repo | — |
| [`git-version-control.md`](git/git-version-control.md) | native | — | this repo | — |
| [`release-workflow`](git/release-workflow/) | `atomic` | `—` | [JimLiu/baoyu-skills](https://github.com/JimLiu/baoyu-skills/tree/main/.claude/skills/release-skills) | Universal release workflow (Node/Python/Rust/Claude plugin/GitHub Releases/tags/backfill). |

## `governance/`

Project governance: cleanup, anti-patterns, requirement abstraction, refactor checks.

| Slug | Kind | Cluster | Source | Summary |
|---|---|---|---|---|
| [`auto-cleanup.md`](governance/auto-cleanup.md) | native | — | this repo | — |
| [`avoid-pitfalls.md`](governance/avoid-pitfalls.md) | native | — | this repo | — |
| [`project-manager.md`](governance/project-manager.md) | native | — | this repo | — |
| [`refactoring-checklist.md`](governance/refactoring-checklist.md) | native | — | this repo | — |
| [`reference-analysis.md`](governance/reference-analysis.md) | native | — | this repo | — |

## `methodology/`

Method-style skills: diagnose, decision systems, learning, deconstruction, research frameworks.

| Slug | Kind | Cluster | Source | Summary |
|---|---|---|---|---|
| [`README.md`](methodology/README.md) | native | — | this repo | — |
| [`diagnose.md`](methodology/diagnose.md) | native | — | this repo | — |
| [`grill-with-docs`](methodology/grill-with-docs/) | native | — | this repo | — |
| [`improve-codebase-architecture`](methodology/improve-codebase-architecture/) | native | — | this repo | — |
| [`prototype`](methodology/prototype/) | native | — | this repo | — |
| [`tdd`](methodology/tdd/) | native | — | this repo | — |
| [`triage`](methodology/triage/) | native | — | this repo | — |
| [`zoom-out.md`](methodology/zoom-out.md) | native | — | this repo | — |
| [`chatroom`](methodology/chatroom/) | `atomic` | `chatroom` | [dontbesilent2025/dbskill](https://github.com/dontbesilent2025/dbskill/tree/main/skills/dbs-chatroom) | Multi-expert directed discussion with host and judge. |
| [`chatroom-austrian`](methodology/chatroom-austrian/) | `atomic` | `chatroom` | [dontbesilent2025/dbskill](https://github.com/dontbesilent2025/dbskill/tree/main/skills/dbs-chatroom-austrian) | Austrian-economics chatroom (Hayek/Mises/Claude roles). |
| [`decision-system`](methodology/decision-system/) | `atomic` | `—` | [dontbesilent2025/dbskill](https://github.com/dontbesilent2025/dbskill/tree/main/skills/dbs-decision) | Personal decision system: 4-layer local Markdown knowledge engineering. |
| [`deconstruct`](methodology/deconstruct/) | `atomic` | `—` | [dontbesilent2025/dbskill](https://github.com/dontbesilent2025/dbskill/tree/main/skills/dbs-deconstruct) | Concept deconstruction via Wittgenstein + Austrian-economics methodology. |
| [`good-question`](methodology/good-question/) | `atomic` | `—` | [dontbesilent2025/dbskill](https://github.com/dontbesilent2025/dbskill/tree/main/skills/dbs-good-question) | Turn fuzzy questions into criticizable, verifiable problem specs. |
| [`hv-analysis`](methodology/hv-analysis/) | `composite` | `—` | [KKKKhazix/khazix-skills](https://github.com/KKKKhazix/khazix-skills/tree/main/hv-analysis) | Horizontal-Vertical analysis research method; outputs PDF. |
| [`learning-plan`](methodology/learning-plan/) | `atomic` | `—` | [dontbesilent2025/dbskill](https://github.com/dontbesilent2025/dbskill/tree/main/skills/dbs-learning) | Adaptive interactive learning sequence. |

## `workmode/`

Work modes: caveman, grill-me, handoff, slow-is-fast, goal clarification, manage-upward, tame-vibe-coding.

| Slug | Kind | Cluster | Source | Summary |
|---|---|---|---|---|
| [`README.md`](workmode/README.md) | native | — | this repo | — |
| [`manage-upward.md`](workmode/manage-upward.md) | native | — | this repo | 向上管理双向督促：三件事汇报法、2 小时风险上报、带方案沟通、摆脱学生思维。 |
| [`tame-vibe-coding.md`](workmode/tame-vibe-coding.md) | native | — | this repo | Vibe Coding 债务控制：化解认知债务（你不懂自己项目）和技术债务（代码烂账），AI 当实习生你当 mentor。 |
| [`caveman.md`](workmode/caveman.md) | native | — | this repo | — |
| [`grill-me.md`](workmode/grill-me.md) | native | — | this repo | — |
| [`handoff.md`](workmode/handoff.md) | native | — | this repo | — |
| [`goal-clarify`](workmode/goal-clarify/) | `atomic` | `—` | [dontbesilent2025/dbskill](https://github.com/dontbesilent2025/dbskill/tree/main/skills/dbs-goal) | Goal clarification via Wittgenstein-style language auditing. |
| [`slowisfast`](workmode/slowisfast/) | `atomic` | `—` | [dontbesilent2025/dbskill](https://github.com/dontbesilent2025/dbskill/tree/main/skills/dbs-slowisfast) | Slow is fast diagnostic: distinguish compounding friction from harmful shortcuts. |

## `meta/`

Meta capabilities: skill authoring, knowledge-base hygiene.

| Slug | Kind | Cluster | Source | Summary |
|---|---|---|---|---|
| [`README.md`](meta/README.md) | native | — | this repo | — |
| [`teach.md`](meta/teach.md) | native | — | this repo | — |
| [`write-a-skill.md`](meta/write-a-skill.md) | native | — | this repo | — |
| [`neat-freak`](meta/neat-freak/) | `composite` | `—` | [KKKKhazix/khazix-skills](https://github.com/KKKKhazix/khazix-skills/tree/main/neat-freak) | Knowledge Base Neat-Freak: cross-platform agent memory/docs hygiene. |

## `misc/`

Low-frequency helpers and tool references.

| Slug | Kind | Cluster | Source | Summary |
|---|---|---|---|---|
| [`README.md`](misc/README.md) | native | — | this repo | — |
| [`git-guardrails-claude-code.md`](misc/git-guardrails-claude-code.md) | native | — | this repo | — |
| [`migrate-to-shoehorn.md`](misc/migrate-to-shoehorn.md) | native | — | this repo | — |
| [`scaffold-exercises.md`](misc/scaffold-exercises.md) | native | — | this repo | — |
| [`setup-pre-commit.md`](misc/setup-pre-commit.md) | native | — | this repo | — |

## `domain/`

Domain skills (e.g. A-share data tools).

| Slug | Kind | Cluster | Source | Summary |
|---|---|---|---|---|
| [`a-stock-data.md`](domain/a-stock-data.md) | native | — | this repo | — |

## `agent-adapters/`

Platform adapter layer: same responsibility across Codex / Claude Code / etc.

| Slug | Kind | Cluster | Source | Summary |
|---|---|---|---|---|
| [`change-workflow.md`](agent-adapters/change-workflow.md) | native | — | this repo | — |
| [`data-collector-development.md`](agent-adapters/data-collector-development.md) | native | — | this repo | — |
| [`project-context.md`](agent-adapters/project-context.md) | native | — | this repo | — |
| [`release-checklist.md`](agent-adapters/release-checklist.md) | native | — | this repo | — |
| [`review-and-cleanup.md`](agent-adapters/review-and-cleanup.md) | native | — | this repo | — |
| [`testing-and-verification.md`](agent-adapters/testing-and-verification.md) | native | — | this repo | — |
| [`tools-discipline.md`](agent-adapters/tools-discipline.md) | native | — | this repo | — |
| [`agent-migration`](agent-adapters/agent-migration/) | `atomic` | `—` | [dontbesilent2025/dbskill](https://github.com/dontbesilent2025/dbskill/tree/main/skills/dbs-agent-migration) | Migrate agent workspaces across Claude Code / Codex / Grok. |

## `content/`

Writing, formatting, translation, illustration, slides, social cards, publishing.

| Slug | Kind | Cluster | Source | Summary |
|---|---|---|---|---|
| [`ai-check`](content/ai-check/) | `atomic` | `humanizer` | [dontbesilent2025/dbskill](https://github.com/dontbesilent2025/dbskill/tree/main/skills/dbs-ai-check) | Detect AI-writing traces in Chinese text. Sibling: content/humanizer-zh (rewrites), content/format-markdown. |
| [`article-illustrator`](content/article-illustrator/) | `composite` | `visual` | [JimLiu/baoyu-skills](https://github.com/JimLiu/baoyu-skills/tree/main/skills/baoyu-article-illustrator) | Article illustration planning + image prompts via Type x Style x Palette. |
| [`comic`](content/comic/) | `composite` | `visual` | [JimLiu/baoyu-skills](https://github.com/JimLiu/baoyu-skills/tree/main/skills/baoyu-comic) | Knowledge comic creator (multi art-style, tones, panel layouts, batch image gen). |
| [`content-strategy`](content/content-strategy/) | `atomic` | `—` | [dontbesilent2025/dbskill](https://github.com/dontbesilent2025/dbskill/tree/main/skills/dbs-content) | Content creation diagnosis after topic is confirmed. |
| [`content-system`](content/content-system/) | `composite` | `—` | [dontbesilent2025/dbskill](https://github.com/dontbesilent2025/dbskill/tree/main/skills/dbs-content-system) | Structured local content engineering system (scaffold + templates + JS tools). |
| [`cover-image`](content/cover-image/) | `composite` | `visual` | [JimLiu/baoyu-skills](https://github.com/JimLiu/baoyu-skills/tree/main/skills/baoyu-cover-image) | Article cover images: type x palette x rendering x text x mood. |
| [`format-markdown`](content/format-markdown/) | `composite` | `humanizer` | [JimLiu/baoyu-skills](https://github.com/JimLiu/baoyu-skills/tree/main/skills/baoyu-format-markdown) | Format MD with frontmatter/titles/summaries/headings. Sibling: content/humanizer-zh, content/ai-check. |
| [`guizang-ppt`](content/guizang-ppt/) | `composite` | `slide` | [op7418/guizang-ppt-skill](https://github.com/op7418/guizang-ppt-skill) | Horizontal swipe web PPT as single HTML file (WebGL bg, chapter covers, big-number data pages). Sibling: content/slide-deck-baoyu. |
| [`guizang-social-card`](content/guizang-social-card/) | `composite` | `card` | [op7418/guizang-social-card-skill](https://github.com/op7418/guizang-social-card-skill) | Guizang-style social cards + WeChat cover pairs (Swiss/editorial layouts). Sibling: content/xhs-images-baoyu. |
| [`hook-opener`](content/hook-opener/) | `atomic` | `—` | [dontbesilent2025/dbskill](https://github.com/dontbesilent2025/dbskill/tree/main/skills/dbs-hook) | Short-video opening optimization; hook formulas + content diagnosis. |
| [`humanizer-zh`](content/humanizer-zh/) | `atomic` | `humanizer` | [op7418/Humanizer-zh](https://github.com/op7418/Humanizer-zh) | Chinese text de-AI-ification; rewrite to natural prose. Sibling: content/ai-check (detects), content/format-markdown (formats). |
| [`infographic`](content/infographic/) | `composite` | `visual` | [JimLiu/baoyu-skills](https://github.com/JimLiu/baoyu-skills/tree/main/skills/baoyu-infographic) | Professional infographics with 21 layouts x 22 styles. |
| [`khazix-writer`](content/khazix-writer/) | `composite` | `—` | [KKKKhazix/khazix-skills](https://github.com/KKKKhazix/khazix-skills/tree/main/khazix-writer) | Personal long-form WeChat writing style (Khazix voice). |
| [`markdown-to-html`](content/markdown-to-html/) | `composite` | `publish` | [JimLiu/baoyu-skills](https://github.com/JimLiu/baoyu-skills/tree/main/skills/baoyu-markdown-to-html) | Markdown to styled HTML (WeChat-compatible themes, code highlight, math, Mermaid, PlantUML, footnotes, citations). |
| [`post-to-wechat`](content/post-to-wechat/) | `composite` | `publish` | [JimLiu/baoyu-skills](https://github.com/JimLiu/baoyu-skills/tree/main/skills/baoyu-post-to-wechat) | Post to WeChat Official Account via API or Chrome CDP. |
| [`post-to-weibo`](content/post-to-weibo/) | `composite` | `publish` | [JimLiu/baoyu-skills](https://github.com/JimLiu/baoyu-skills/tree/main/skills/baoyu-post-to-weibo) | Post to Weibo via Chrome CDP; supports articles. |
| [`post-to-x`](content/post-to-x/) | `composite` | `publish` | [JimLiu/baoyu-skills](https://github.com/JimLiu/baoyu-skills/tree/main/skills/baoyu-post-to-x) | Post to X/Twitter via Chrome extension, Computer Use, or CDP. |
| [`resonate`](content/resonate/) | `atomic` | `—` | [dontbesilent2025/dbskill](https://github.com/dontbesilent2025/dbskill/tree/main/skills/dbs-resonate) | Draft resonance diagnosis (communication psychology). |
| [`slide-deck-baoyu`](content/slide-deck-baoyu/) | `composite` | `slide` | [JimLiu/baoyu-skills](https://github.com/JimLiu/baoyu-skills/tree/main/skills/baoyu-slide-deck) | Slide deck images from content. Sibling: content/guizang-ppt. |
| [`spread`](content/spread/) | `atomic` | `—` | [dontbesilent2025/dbskill](https://github.com/dontbesilent2025/dbskill/tree/main/skills/dbs-spread) | Communication-psychology decoder: why content resonates and what audience wants next. |
| [`translate`](content/translate/) | `composite` | `—` | [JimLiu/baoyu-skills](https://github.com/JimLiu/baoyu-skills/tree/main/skills/baoyu-translate) | Three-mode translation: quick/normal/refined (with subagent polish). |
| [`xhs-images-baoyu`](content/xhs-images-baoyu/) | `composite` | `card` | [JimLiu/baoyu-skills](https://github.com/JimLiu/baoyu-skills/tree/main/skills/baoyu-xhs-images) | Xiaohongshu image cards (12 styles x 8 layouts x 3 palettes). Sibling: content/guizang-social-card. |
| [`xhs-title`](content/xhs-title/) | `atomic` | `—` | [dontbesilent2025/dbskill](https://github.com/dontbesilent2025/dbskill/tree/main/skills/dbs-xhs-title) | Xiaohongshu title formulas (75 validated viral patterns). |

## `productivity/`

URL/video extraction, storage hygiene, notebook querying, news, summarization.

| Slug | Kind | Cluster | Source | Summary |
|---|---|---|---|---|
| [`compress-image`](productivity/compress-image/) | `composite` | `—` | [JimLiu/baoyu-skills](https://github.com/JimLiu/baoyu-skills/tree/main/skills/baoyu-compress-image) | WebP/PNG compression via sips/cwebp/ImageMagick/Sharp. |
| [`news-aihot`](productivity/news-aihot/) | `atomic` | `—` | [KKKKhazix/khazix-skills](https://github.com/KKKKhazix/khazix-skills/tree/main/aihot) | Chinese AI news brief via aihot.virxact.com public REST API. |
| [`notebooklm`](productivity/notebooklm/) | `composite` | `—` | [PleasePrompto/notebooklm-skill](https://github.com/PleasePrompto/notebooklm-skill) | Query Google NotebookLM from agent for citation-backed answers; browser automation. |
| [`storage-analyzer`](productivity/storage-analyzer/) | `composite` | `—` | [KKKKhazix/khazix-skills](https://github.com/KKKKhazix/khazix-skills/tree/main/storage-analyzer) | Read-only storage analysis (macOS+Windows); interactive HTML report. |
| [`url-to-markdown`](productivity/url-to-markdown/) | `composite` | `extract` | [JimLiu/baoyu-skills](https://github.com/JimLiu/baoyu-skills/tree/main/skills/baoyu-url-to-markdown) | Any-URL to Markdown via baoyu-fetch CLI; site adapters (X, YouTube, HN). Sibling: productivity/x-to-markdown, productivity/youtube-transcript. |
| [`wechat-summary`](productivity/wechat-summary/) | `composite` | `—` | [JimLiu/baoyu-skills](https://github.com/JimLiu/baoyu-skills/tree/main/skills/baoyu-wechat-summary) | Summarize WeChat group chats via local wx-cli (macOS). |
| [`x-to-markdown`](productivity/x-to-markdown/) | `composite-danger` | `extract` | [JimLiu/baoyu-skills](https://github.com/JimLiu/baoyu-skills/tree/main/skills/baoyu-danger-x-to-markdown) | DANGER: reverse-engineered X/Twitter API to Markdown. Sibling: productivity/url-to-markdown. |
| [`youtube-transcript`](productivity/youtube-transcript/) | `composite` | `extract` | [JimLiu/baoyu-skills](https://github.com/JimLiu/baoyu-skills/tree/main/skills/baoyu-youtube-transcript) | YouTube transcripts/subtitles/covers; chapters; speaker ID. |

## `business/`

Business / product / personal diagnostic frameworks (dontbesilent toolkit).

| Slug | Kind | Cluster | Source | Summary |
|---|---|---|---|---|
| [`action-diagnose`](business/action-diagnose/) | `atomic` | `—` | [dontbesilent2025/dbskill](https://github.com/dontbesilent2025/dbskill/tree/main/skills/dbs-action) | Execution/procrastination diagnosis (Adlerian psychology). |
| [`benchmark`](business/benchmark/) | `atomic` | `—` | [dontbesilent2025/dbskill](https://github.com/dontbesilent2025/dbskill/tree/main/skills/dbs-benchmark) | Competitor benchmark imitation analysis (five-filter method). |
| [`dbs-router`](business/dbs-router/) | `atomic` | `dbs-core` | [dontbesilent2025/dbskill](https://github.com/dontbesilent2025/dbskill/tree/main/skills/dbs) | Main router for dontbesilent business toolkit; dispatches to other dbs-* skills. |
| [`diagnosis`](business/diagnosis/) | `atomic` | `—` | [dontbesilent2025/dbskill](https://github.com/dontbesilent2025/dbskill/tree/main/skills/dbs-diagnosis) | Business model diagnosis; dissolves flawed questions. |
| [`state-report`](business/state-report/) | `atomic` | `dbs-state` | [dontbesilent2025/dbskill](https://github.com/dontbesilent2025/dbskill/tree/main/skills/dbs-report) | Merge dbs-save snapshots into a Markdown report. Cluster: business/state-save + state-restore + state-report. |
| [`state-restore`](business/state-restore/) | `atomic` | `dbs-state` | [dontbesilent2025/dbskill](https://github.com/dontbesilent2025/dbskill/tree/main/skills/dbs-restore) | Restore recent dbskill diagnostic state from local snapshots. |
| [`state-save`](business/state-save/) | `atomic` | `dbs-state` | [dontbesilent2025/dbskill](https://github.com/dontbesilent2025/dbskill/tree/main/skills/dbs-save) | Save current dbskill diagnostic conclusions to structured local Markdown. |

## `ai-backends/`

AI provider adapters (image gen, gemini-web, etc.).

| Slug | Kind | Cluster | Source | Summary |
|---|---|---|---|---|
| [`gemini-web`](ai-backends/gemini-web/) | `composite-danger` | `—` | [JimLiu/baoyu-skills](https://github.com/JimLiu/baoyu-skills/tree/main/skills/baoyu-danger-gemini-web) | DANGER: reverse-engineered Gemini Web API; needs browser session. |
| [`image-gen`](ai-backends/image-gen/) | `composite` | `—` | [JimLiu/baoyu-skills](https://github.com/JimLiu/baoyu-skills/tree/main/skills/baoyu-image-gen) | Multi-provider image generation API (OpenAI/Azure/Google/OpenRouter/DashScope/Z.AI/MiniMax/Jimeng/Seedream/Replicate/Agnes). |

---

## Clusters

Skills sharing a `cluster:` tag are intended to compose. See `_meta/clusters.md` for recommended pipelines.

### `card`

- [`guizang-social-card`](content/guizang-social-card/) — Guizang-style social cards + WeChat cover pairs (Swiss/editorial layouts). Sibling: content/xhs-images-baoyu.
- [`xhs-images-baoyu`](content/xhs-images-baoyu/) — Xiaohongshu image cards (12 styles x 8 layouts x 3 palettes). Sibling: content/guizang-social-card.

### `chatroom`

- [`chatroom`](methodology/chatroom/) — Multi-expert directed discussion with host and judge.
- [`chatroom-austrian`](methodology/chatroom-austrian/) — Austrian-economics chatroom (Hayek/Mises/Claude roles).

### `dbs-core`

- [`dbs-router`](business/dbs-router/) — Main router for dontbesilent business toolkit; dispatches to other dbs-* skills.

### `dbs-state`

- [`state-report`](business/state-report/) — Merge dbs-save snapshots into a Markdown report. Cluster: business/state-save + state-restore + state-report.
- [`state-restore`](business/state-restore/) — Restore recent dbskill diagnostic state from local snapshots.
- [`state-save`](business/state-save/) — Save current dbskill diagnostic conclusions to structured local Markdown.

### `extract`

- [`url-to-markdown`](productivity/url-to-markdown/) — Any-URL to Markdown via baoyu-fetch CLI; site adapters (X, YouTube, HN). Sibling: productivity/x-to-markdown, productivity/youtube-transcript.
- [`x-to-markdown`](productivity/x-to-markdown/) — DANGER: reverse-engineered X/Twitter API to Markdown. Sibling: productivity/url-to-markdown.
- [`youtube-transcript`](productivity/youtube-transcript/) — YouTube transcripts/subtitles/covers; chapters; speaker ID.

### `humanizer`

- [`ai-check`](content/ai-check/) — Detect AI-writing traces in Chinese text. Sibling: content/humanizer-zh (rewrites), content/format-markdown.
- [`format-markdown`](content/format-markdown/) — Format MD with frontmatter/titles/summaries/headings. Sibling: content/humanizer-zh, content/ai-check.
- [`humanizer-zh`](content/humanizer-zh/) — Chinese text de-AI-ification; rewrite to natural prose. Sibling: content/ai-check (detects), content/format-markdown (formats).

### `publish`

- [`markdown-to-html`](content/markdown-to-html/) — Markdown to styled HTML (WeChat-compatible themes, code highlight, math, Mermaid, PlantUML, footnotes, citations).
- [`post-to-wechat`](content/post-to-wechat/) — Post to WeChat Official Account via API or Chrome CDP.
- [`post-to-weibo`](content/post-to-weibo/) — Post to Weibo via Chrome CDP; supports articles.
- [`post-to-x`](content/post-to-x/) — Post to X/Twitter via Chrome extension, Computer Use, or CDP.

### `slide`

- [`guizang-ppt`](content/guizang-ppt/) — Horizontal swipe web PPT as single HTML file (WebGL bg, chapter covers, big-number data pages). Sibling: content/slide-deck-baoyu.
- [`slide-deck-baoyu`](content/slide-deck-baoyu/) — Slide deck images from content. Sibling: content/guizang-ppt.

### `visual`

- [`article-illustrator`](content/article-illustrator/) — Article illustration planning + image prompts via Type x Style x Palette.
- [`comic`](content/comic/) — Knowledge comic creator (multi art-style, tones, panel layouts, batch image gen).
- [`cover-image`](content/cover-image/) — Article cover images: type x palette x rendering x text x mood.
- [`infographic`](content/infographic/) — Professional infographics with 21 layouts x 22 styles.
