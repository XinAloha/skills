# INDEX — All skills registry

Auto-generated companion to `README.md`. One row per skill. Re-run `_meta/build_index.py` after adding or moving skills.

Legend for **Kind**:

- `atomic` — single `SKILL.md`; no internal tooling. Acts as one prompt-level capability.
- `composite` — `SKILL.md` + bundled `scripts/` / `references/` / `assets/`. Internal multi-step logic; one self-contained pipeline.
- `composite-danger` — composite skill that depends on reverse-engineered or unofficial APIs; may break upstream without notice.
- `cluster: <name>` (in Cluster column) — multiple skills designed to be chained. See `_meta/clusters.md`.
- `native` — authored in this repo, not imported.

**Totals:** 128 imported · 60 native · 188 skills across 16 categories.

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
| [`ecosystem-governance.md`](governance/ecosystem-governance.md) | native | — | this repo | — |
| [`project-manager.md`](governance/project-manager.md) | native | — | this repo | — |
| [`refactoring-checklist.md`](governance/refactoring-checklist.md) | native | — | this repo | — |
| [`reference-analysis.md`](governance/reference-analysis.md) | native | — | this repo | — |

## `methodology/`

Method-style skills: diagnose, decision systems, learning, deconstruction, research frameworks.

| Slug | Kind | Cluster | Source | Summary |
|---|---|---|---|---|
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
| [`jtbd`](methodology/jtbd/) | `atomic` | `—` | [dontbesilent2025/dbskill](https://github.com/dontbesilent2025/dbskill/tree/main/skills/dbs-jtbd) | Jobs-to-be-done task clarification: identify the progress/switch forces/observable criteria; optimize product, content, service, decision, AI prompts. |
| [`knowledge`](methodology/knowledge/) | `atomic` | `—` | [dontbesilent2025/dbskill](https://github.com/dontbesilent2025/dbskill/tree/main/skills/dbs-knowledge) | Build a local folder into an agent-searchable/maintainable knowledge base with navigation, version judgment, health checks, SOT tiered governance. |
| [`learning-plan`](methodology/learning-plan/) | `atomic` | `—` | [dontbesilent2025/dbskill](https://github.com/dontbesilent2025/dbskill/tree/main/skills/dbs-learning) | Adaptive interactive learning sequence. |
| [`standard-answer`](methodology/standard-answer/) | `composite` | `—` | [dontbesilent2025/dbskill](https://github.com/dontbesilent2025/dbskill/tree/main/skills/dbs-standard-answer) | Find structurally-similar success/failure/counterexamples from business/management/tech/career/institutional history; distill conditional repeated mechanisms. |

## `workmode/`

Work modes: caveman, ponytail (lazy minimal coding), grill-me, handoff, slow-is-fast, goal clarification.

| Slug | Kind | Cluster | Source | Summary |
|---|---|---|---|---|
| [`caveman.md`](workmode/caveman.md) | native | — | this repo | — |
| [`grill-me.md`](workmode/grill-me.md) | native | — | this repo | — |
| [`handoff.md`](workmode/handoff.md) | native | — | this repo | — |
| [`manage-upward.md`](workmode/manage-upward.md) | native | — | this repo | — |
| [`tame-vibe-coding.md`](workmode/tame-vibe-coding.md) | native | — | this repo | — |
| [`goal-clarify`](workmode/goal-clarify/) | `atomic` | `—` | [dontbesilent2025/dbskill](https://github.com/dontbesilent2025/dbskill/tree/main/skills/dbs-goal) | Goal clarification via Wittgenstein-style language auditing. |
| [`leader`](workmode/leader/) | `composite` | `—` | [KKKKhazix/khazix-skills](https://github.com/KKKKhazix/khazix-skills/tree/main/leader) | Turn a one-line idea into a runnable agent goal brief (<=4000 chars, verified numbers, whitelist bounds, anti-cheat acceptance, resume); splits execution vs exploration. |
| [`ponytail`](workmode/ponytail/) | `atomic` | `ponytail` | [DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail/tree/main/skills/ponytail) | Lazy senior-dev coding mode: force the minimal solution that works (YAGNI -> stdlib -> native -> one line -> minimum). Levels lite/full/ultra. Sibling: workmode/caveman. |
| [`ponytail-audit`](workmode/ponytail-audit/) | `atomic` | `ponytail` | [DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail/tree/main/skills/ponytail-audit) | Whole-repo audit for over-engineering: ranked list of what to delete/simplify/replace with stdlib/native. One-shot report, no fixes. |
| [`ponytail-debt`](workmode/ponytail-debt/) | `atomic` | `ponytail` | [DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail/tree/main/skills/ponytail-debt) | Harvest every ponytail: comment into a debt ledger so deliberate shortcuts get tracked. One-shot report, changes nothing. |
| [`ponytail-gain`](workmode/ponytail-gain/) | `atomic` | `ponytail` | [DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail/tree/main/skills/ponytail-gain) | Display ponytail's measured benchmark scoreboard (less code/cost, more speed). One-shot display, not a persistent mode. |
| [`ponytail-help`](workmode/ponytail-help/) | `atomic` | `ponytail` | [DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail/tree/main/skills/ponytail-help) | Quick-reference card for all ponytail modes/skills/commands. One-shot display. |
| [`ponytail-review`](workmode/ponytail-review/) | `atomic` | `ponytail` | [DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail/tree/main/skills/ponytail-review) | Code review hunting only over-engineering: one line per finding (delete/stdlib/native/yagni/shrink). Complements correctness-focused review. |
| [`slowisfast`](workmode/slowisfast/) | `atomic` | `—` | [dontbesilent2025/dbskill](https://github.com/dontbesilent2025/dbskill/tree/main/skills/dbs-slowisfast) | Slow is fast diagnostic: distinguish compounding friction from harmful shortcuts. |

## `meta/`

Meta capabilities: skill authoring, knowledge-base hygiene.

| Slug | Kind | Cluster | Source | Summary |
|---|---|---|---|---|
| [`teach.md`](meta/teach.md) | native | — | this repo | — |
| [`write-a-skill.md`](meta/write-a-skill.md) | native | — | this repo | — |
| [`dbs-update`](meta/dbs-update/) | `atomic` | `—` | [dontbesilent2025/dbskill](https://github.com/dontbesilent2025/dbskill/tree/main/skills/dbs-update) | Update the official dbskill suite while preserving other skills and user archives. |
| [`neat-freak`](meta/neat-freak/) | `composite` | `—` | [KKKKhazix/khazix-skills](https://github.com/KKKKhazix/khazix-skills/tree/main/neat-freak) | Knowledge Base Neat-Freak: cross-platform agent memory/docs hygiene. |
| [`skill-cleaner`](meta/skill-cleaner/) | `composite` | `—` | [dontbesilent2025/dbskill](https://github.com/dontbesilent2025/dbskill/tree/main/skills/dbs-skill-cleaner) | Scan local skills for ad/stealth-commercial intent, task hijacking, suspicious external calls, sensitive-data reads; report-only by default. |

## `misc/`

Low-frequency helpers and tool references.

| Slug | Kind | Cluster | Source | Summary |
|---|---|---|---|---|
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
| [`bridge`](agent-adapters/bridge/) | `composite` | `—` | [dontbesilent2025/dbskill](https://github.com/dontbesilent2025/dbskill/tree/main/skills/dbs-bridge) | Bridge a single skill or skill-set across agents (Agents/Claude Code/Codex/WorkBuddy/Grok/Hermes/Kiro/Qwen Code/Cline): install/sync/list/dedup/unlink. |

## `content/`

Writing, formatting, translation, illustration, slides, social cards, publishing.

| Slug | Kind | Cluster | Source | Summary |
|---|---|---|---|---|
| [`ai-check`](content/ai-check/) | `atomic` | `humanizer` | [dontbesilent2025/dbskill](https://github.com/dontbesilent2025/dbskill/tree/main/skills/dbs-ai-check) | Detect AI-writing traces in Chinese text. Sibling: content/humanizer-zh (rewrites), content/format-markdown. |
| [`article-illustrator`](content/article-illustrator/) | `composite` | `visual` | [JimLiu/baoyu-skills](https://github.com/JimLiu/baoyu-skills/tree/main/skills/baoyu-article-illustrator) | Article illustration planning + image prompts via Type x Style x Palette. |
| [`comic`](content/comic/) | `composite` | `visual` | [JimLiu/baoyu-skills](https://github.com/JimLiu/baoyu-skills/tree/main/skills/baoyu-comic) | Knowledge comic creator (multi art-style, tones, panel layouts, batch image gen). |
| [`content-risk-check`](content/content-risk-check/) | `atomic` | `—` | [dontbesilent2025/dbskill](https://github.com/dontbesilent2025/dbskill/tree/main/skills/dbs-content-risk-check) | Content publishing risk check: sentence-by-sentence for titles/body/image text/captions/account bio/video frames; pinpoints positions + minimal fixes. |
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
| [`script-flow`](content/script-flow/) | `atomic` | `—` | [dontbesilent2025/dbskill](https://github.com/dontbesilent2025/dbskill/tree/main/skills/dbs-script-flow) | Check short-video script flow: paragraph transitions, information density, delivery smoothness; locate where viewers drop off. |
| [`slide-deck-baoyu`](content/slide-deck-baoyu/) | `composite` | `slide` | [JimLiu/baoyu-skills](https://github.com/JimLiu/baoyu-skills/tree/main/skills/baoyu-slide-deck) | Slide deck images from content. Sibling: content/guizang-ppt. |
| [`spread`](content/spread/) | `atomic` | `—` | [dontbesilent2025/dbskill](https://github.com/dontbesilent2025/dbskill/tree/main/skills/dbs-spread) | Communication-psychology decoder: why content resonates and what audience wants next. |
| [`translate`](content/translate/) | `composite` | `—` | [JimLiu/baoyu-skills](https://github.com/JimLiu/baoyu-skills/tree/main/skills/baoyu-translate) | Three-mode translation: quick/normal/refined (with subagent polish). |
| [`wechat-html`](content/wechat-html/) | `composite` | `—` | [dontbesilent2025/dbskill](https://github.com/dontbesilent2025/dbskill/tree/main/skills/dbs-wechat-html) | Convert Markdown to paste-ready WeChat Official Account HTML with 15 built-in styles. |
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

## `loop-engineering/`

Project-level agent loop qualification, contracts, state, harnesses, scaffolding, and audits.

| Slug | Kind | Cluster | Source | Summary |
|---|---|---|---|---|
| [`audit-loop-project`](loop-engineering/audit-loop-project/) | native | — | this repo | — |
| [`build-loop-harness`](loop-engineering/build-loop-harness/) | native | — | this repo | — |
| [`design-loop-project`](loop-engineering/design-loop-project/) | native | — | this repo | — |
| [`design-loop-state`](loop-engineering/design-loop-state/) | native | — | this repo | — |
| [`improve-loop-system`](loop-engineering/improve-loop-system/) | native | — | this repo | — |
| [`operate-loop-run`](loop-engineering/operate-loop-run/) | native | — | this repo | — |
| [`qualify-loop-task`](loop-engineering/qualify-loop-task/) | native | — | this repo | — |
| [`specify-loop-contract`](loop-engineering/specify-loop-contract/) | native | — | this repo | — |
| [`verify-loop-delivery`](loop-engineering/verify-loop-delivery/) | native | — | this repo | — |

## `quant/`

Quantitative investment skills (quantskills community): data, factor research, market analysis, risk, backtesting, models, validation, news, infrastructure.

| Slug | Kind | Cluster | Source | Summary |
|---|---|---|---|---|
| [`skill-backtest`](quant/backtest/skill-backtest/) | `composite` | `—` | [quantskills/skill-backtest](https://github.com/quantskills/skill-backtest) | 提供横截面多头回测协议，固定 T+1 开盘成交、费用、涨跌停剔除与诊断图表。 |
| [`skill-brinson-performance-attribution`](quant/backtest/skill-brinson-performance-attribution/) | `composite` | `—` | [quantskills/skill-brinson-performance-attribution](https://github.com/quantskills/skill-brinson-performance-attribution) | 执行 Brinson-Fachler 或 BHB 归因、HHI 与贡献排序，并支持 Carino 多期链接。 |
| [`skill-factor-backtest`](quant/backtest/skill-factor-backtest/) | `composite` | `—` | [quantskills/skill-factor-backtest](https://github.com/quantskills/skill-factor-backtest) | 对给定因子和行情数据执行long-only横截面因子回测并生成诊断报告。 |
| [`skill-portfolio-attribution`](quant/backtest/skill-portfolio-attribution/) | `composite` | `—` | [quantskills/skill-portfolio-attribution](https://github.com/quantskills/skill-portfolio-attribution) | 将组合主动收益分解为行业配置、个股选择、交互效应和因子贡献。 |
| [`skill-portfolio-optimize`](quant/backtest/skill-portfolio-optimize/) | `composite` | `—` | [quantskills/skill-portfolio-optimize](https://github.com/quantskills/skill-portfolio-optimize) | 将alpha信号转为受权重、行业、暴露和换手约束的优化组合权重。 |
| [`skill-risk-return-metrics`](quant/backtest/skill-risk-return-metrics/) | `composite` | `—` | [quantskills/skill-risk-return-metrics](https://github.com/quantskills/skill-risk-return-metrics) | 计算投资组合或策略的风险收益指标。 |
| [`skill-transaction-cost-analysis`](quant/backtest/skill-transaction-cost-analysis/) | `composite` | `—` | [quantskills/skill-transaction-cost-analysis](https://github.com/quantskills/skill-transaction-cost-analysis) | 将成交记录相对 VWAP/TWAP 分解为多类交易成本。 |
| [`skill-transaction-cost-calibration`](quant/backtest/skill-transaction-cost-calibration/) | `composite` | `—` | [quantskills/skill-transaction-cost-calibration](https://github.com/quantskills/skill-transaction-cost-calibration) | 从成交和市场数据校准佣金、价差、滑点与冲击成本假设。 |
| [`skill-a-share-pit-fundamental-vintage-builder`](quant/data/skill-a-share-pit-fundamental-vintage-builder/) | `composite` | `—` | [quantskills/skill-a-share-pit-fundamental-vintage-builder](https://github.com/quantskills/skill-a-share-pit-fundamental-vintage-builder) | 按披露可见时点构建并审计 A 股财务数据，避免使用后续重述信息。 |
| [`skill-corporate-action-adjustment-auditor`](quant/data/skill-corporate-action-adjustment-auditor/) | `composite` | `—` | [quantskills/skill-corporate-action-adjustment-auditor](https://github.com/quantskills/skill-corporate-action-adjustment-auditor) | 在研究或回测前审计原始与复权价格中的拆分和现金分红一致性。 |
| [`skill-intraday-data-quality-auditor`](quant/data/skill-intraday-data-quality-auditor/) | `composite` | `—` | [quantskills/skill-intraday-data-quality-auditor](https://github.com/quantskills/skill-intraday-data-quality-auditor) | 审计标准化日内OHLCV数据的时间戳、缺口、价格、成交量和交易日缺陷。 |
| [`skill-build-b10-factor-evaluation`](quant/factors/skill-build-b10-factor-evaluation/) | `atomic` | `—` | [quantskills/skill-build-b10-factor-evaluation](https://github.com/quantskills/skill-build-b10-factor-evaluation) | 评估因子的 IC、IR、分层回测、单调性、换手率和衰减表现。 |
| [`skill-factor-alpha191-alpha101`](quant/factors/skill-factor-alpha191-alpha101/) | `composite` | `—` | [quantskills/skill-factor-alpha191-alpha101](https://github.com/quantskills/skill-factor-alpha191-alpha101) | 从长表OHLCV CSV批量计算Alpha101和Alpha191因子并输出宽表CSV。 |
| [`skill-factor-blend`](quant/factors/skill-factor-blend/) | `composite` | `—` | [quantskills/skill-factor-blend](https://github.com/quantskills/skill-factor-blend) | 将多个因子信号去冗余、加权并合成为复合信号。 |
| [`skill-factor-evaluate`](quant/factors/skill-factor-evaluate/) | `composite` | `—` | [quantskills/skill-factor-evaluate](https://github.com/quantskills/skill-factor-evaluate) | 对单个截面因子计算IC、夏普、回撤、单调性和换手的综合评分。 |
| [`skill-factor-idea-generation`](quant/factors/skill-factor-idea-generation/) | `composite` | `—` | [quantskills/skill-factor-idea-generation](https://github.com/quantskills/skill-factor-idea-generation) | 根据默认数据范围生成包含经济逻辑和风险说明的因子候选想法。 |
| [`skill-factor-mason`](quant/factors/skill-factor-mason/) | `composite` | `—` | [quantskills/skill-factor-mason](https://github.com/quantskills/skill-factor-mason) | 检查单因子研究中的时点、IC/IR、成本和中性化质量。 |
| [`skill-factor-mine`](quant/factors/skill-factor-mine/) | `composite` | `—` | [quantskills/skill-factor-mine](https://github.com/quantskills/skill-factor-mine) | 提供从假设、实验记录到评分和接受或回滚的因子挖掘SOP。 |
| [`skill-factor-optimize`](quant/factors/skill-factor-optimize/) | `composite` | `—` | [quantskills/skill-factor-optimize](https://github.com/quantskills/skill-factor-optimize) | 对已有股票或期货因子执行参数扫描、消融和版本增强。 |
| [`skill-factor-orthogonalize`](quant/factors/skill-factor-orthogonalize/) | `composite` | `—` | [quantskills/skill-factor-orthogonalize](https://github.com/quantskills/skill-factor-orthogonalize) | 对截面因子进行逐日OLS正交化，并输出残差因子和暴露诊断。 |
| [`skill-factor-pool-evolution`](quant/factors/skill-factor-pool-evolution/) | `composite` | `—` | [quantskills/skill-factor-pool-evolution](https://github.com/quantskills/skill-factor-pool-evolution) | 根据种子因子池的评估生成变异、交叉和推荐。 |
| [`skill-factor-ranking-sage`](quant/factors/skill-factor-ranking-sage/) | `composite` | `—` | [quantskills/skill-factor-ranking-sage](https://github.com/quantskills/skill-factor-ranking-sage) | 在本地因子和标签数据上运行mRMR或Marginal-SAGE并输出Top-K排名。 |
| [`skill-factor-review`](quant/factors/skill-factor-review/) | `composite` | `—` | [quantskills/skill-factor-review](https://github.com/quantskills/skill-factor-review) | 扫描因子库和实验日志，生成量化盘点、结构分析和研究建议。 |
| [`skill-factormad-debate-factor-mining`](quant/factors/skill-factormad-debate-factor-mining/) | `composite` | `—` | [quantskills/skill-factormad-debate-factor-mining](https://github.com/quantskills/skill-factormad-debate-factor-mining) | 参考FactorMAD多智能体辩论框架进行可解释的股票Alpha因子挖掘。 |
| [`skill-fundamental-factor-analysis`](quant/factors/skill-fundamental-factor-analysis/) | `composite` | `—` | [quantskills/skill-fundamental-factor-analysis](https://github.com/quantskills/skill-fundamental-factor-analysis) | 从季度财报计算并验证A股估值、质量和成长因子。 |
| [`skill-ic-analysis`](quant/factors/skill-ic-analysis/) | `composite` | `—` | [quantskills/skill-ic-analysis](https://github.com/quantskills/skill-ic-analysis) | 评估量化因子的IC、分组表现和预测有效性。 |
| [`skill-ml-factor-ensemble`](quant/factors/skill-ml-factor-ensemble/) | `composite` | `—` | [quantskills/skill-ml-factor-ensemble](https://github.com/quantskills/skill-ml-factor-ensemble) | 用防泄漏滚动验证将机器学习模型集成为因子元信号。 |
| [`skill-overseas-equity-factor-miner`](quant/factors/skill-overseas-equity-factor-miner/) | `composite` | `—` | [quantskills/skill-overseas-equity-factor-miner](https://github.com/quantskills/skill-overseas-equity-factor-miner) | 发现并以IC、衰减和换手率验证港美股横截面alpha因子。 |
| [`skill-quant-factor-directional-alpha`](quant/factors/skill-quant-factor-directional-alpha/) | `atomic` | `—` | [quantskills/skill-quant-factor-directional-alpha](https://github.com/quantskills/skill-quant-factor-directional-alpha) | 提供用于趋势、突破和反转研究的 OHLCV 方向因子库。 |
| [`skill-quant-factor-risk-pattern-alpha`](quant/factors/skill-quant-factor-risk-pattern-alpha/) | `atomic` | `—` | [quantskills/skill-quant-factor-risk-pattern-alpha](https://github.com/quantskills/skill-quant-factor-risk-pattern-alpha) | 提供用于波动、K 线形态和回撤压力研究的 OHLCV 因子库。 |
| [`skill-quant-factor-volume-stat-alpha`](quant/factors/skill-quant-factor-volume-stat-alpha/) | `atomic` | `—` | [quantskills/skill-quant-factor-volume-stat-alpha](https://github.com/quantskills/skill-quant-factor-volume-stat-alpha) | 提供用于成交量和量价统计研究的 OHLCV 因子库。 |
| [`skill-residual-guided-factor-selection`](quant/factors/skill-residual-guided-factor-selection/) | `composite` | `—` | [quantskills/skill-residual-guided-factor-selection](https://github.com/quantskills/skill-residual-guided-factor-selection) | 使用残差 IC 和样本外评估筛选因子组合。 |
| [`skill-quant-factor-skill-factory`](quant/infra/skill-quant-factor-skill-factory/) | `composite` | `—` | [quantskills/skill-quant-factor-skill-factory](https://github.com/quantskills/skill-quant-factor-skill-factory) | 批量生成、验证并打包框架中立的 OHLCV 因子技能。 |
| [`skill-template`](quant/infra/skill-template/) | `composite` | `—` | [quantskills/skill-template](https://github.com/quantskills/skill-template) | 提供 QuantSkills 技能项目的模板结构和说明。 |
| [`skill-index-rebalance-event-study`](quant/market/skill-index-rebalance-event-study/) | `composite` | `—` | [quantskills/skill-index-rebalance-event-study](https://github.com/quantskills/skill-index-rebalance-event-study) | 围绕指数纳入、剔除和权重调整公告或生效日运行可复现事件研究。 |
| [`skill-model-hpo-evidence-driven`](quant/models/skill-model-hpo-evidence-driven/) | `composite` | `—` | [quantskills/skill-model-hpo-evidence-driven](https://github.com/quantskills/skill-model-hpo-evidence-driven) | 以固定验证流程和试验级证据优化量化多因子模型超参数。 |
| [`skill-pair-correlation`](quant/models/skill-pair-correlation/) | `composite` | `—` | [quantskills/skill-pair-correlation](https://github.com/quantskills/skill-pair-correlation) | 计算和解释资产对的相关性、滚动关系及其研究用途。 |
| [`skill-paper-replication`](quant/models/skill-paper-replication/) | `composite` | `—` | [quantskills/skill-paper-replication](https://github.com/quantskills/skill-paper-replication) | 支持论文检索、数据提取、实验复现和研究结果报告。 |
| [`skill-quant-research`](quant/models/skill-quant-research/) | `composite` | `—` | [quantskills/skill-quant-research](https://github.com/quantskills/skill-quant-research) | 指导量化研究、回测设计和统计验证工作流。 |
| [`skill-statistical-arbitrage-time-series`](quant/models/skill-statistical-arbitrage-time-series/) | `composite` | `—` | [quantskills/skill-statistical-arbitrage-time-series](https://github.com/quantskills/skill-statistical-arbitrage-time-series) | 构建统计套利时间序列研究并生成可追溯报告。 |
| [`skill-time-series-analysis`](quant/models/skill-time-series-analysis/) | `composite` | `—` | [quantskills/skill-time-series-analysis](https://github.com/quantskills/skill-time-series-analysis) | 对金融时间序列进行诊断并生成分析报告。 |
| [`skill-capital-flow-crowding-monitor`](quant/risk/skill-capital-flow-crowding-monitor/) | `composite` | `—` | [quantskills/skill-capital-flow-crowding-monitor](https://github.com/quantskills/skill-capital-flow-crowding-monitor) | 聚合融资融券、北向持股和大宗交易，计算资金一致性、背离与拥挤度分位信号。 |
| [`skill-market-regime-analysis`](quant/risk/skill-market-regime-analysis/) | `composite` | `—` | [quantskills/skill-market-regime-analysis](https://github.com/quantskills/skill-market-regime-analysis) | 结合指数、宏观、期货期限结构和波动率特征划分A股市场状态。 |
| [`skill-northbound-margin-monitor`](quant/risk/skill-northbound-margin-monitor/) | `composite` | `—` | [quantskills/skill-northbound-margin-monitor](https://github.com/quantskills/skill-northbound-margin-monitor) | 监测北向资金、融资融券和期货全景的多类风险信号。 |
| [`skill-portfolio-liquidity-stress-test`](quant/risk/skill-portfolio-liquidity-stress-test/) | `composite` | `—` | [quantskills/skill-portfolio-liquidity-stress-test](https://github.com/quantskills/skill-portfolio-liquidity-stress-test) | 在成交量压力下估算组合清算天数、期限内变现、赎回缺口和冲击成本。 |
| [`skill-quant-portfolio-risk`](quant/risk/skill-quant-portfolio-risk/) | `composite` | `—` | [quantskills/skill-quant-portfolio-risk](https://github.com/quantskills/skill-quant-portfolio-risk) | 分析组合风险暴露、约束和压力情景。 |
| [`skill-risk-model`](quant/risk/skill-risk-model/) | `composite` | `—` | [quantskills/skill-risk-model](https://github.com/quantskills/skill-risk-model) | 构建多因子风险模型并进行风险归因。 |
| [`skill-rolling-beta-exposure`](quant/risk/skill-rolling-beta-exposure/) | `composite` | `—` | [quantskills/skill-rolling-beta-exposure](https://github.com/quantskills/skill-rolling-beta-exposure) | 估计资产或组合相对于基准的滚动贝塔暴露。 |
| [`skill-backtest-overfit`](quant/validation/skill-backtest-overfit/) | `composite` | `—` | [quantskills/skill-backtest-overfit](https://github.com/quantskills/skill-backtest-overfit) | 评估回测过拟合与多重检验风险，计算 DSR、PBO、净化交叉验证和 Harvey-Liu 折减。 |
| [`skill-backtesting-bias-avoidance`](quant/validation/skill-backtesting-bias-avoidance/) | `composite` | `—` | [quantskills/skill-backtesting-bias-avoidance](https://github.com/quantskills/skill-backtesting-bias-avoidance) | 构建无前视偏差的回测并审计前视、幸存者、过拟合、成本和样本外检验风险。 |
| [`skill-calendar-anomaly-scanner`](quant/validation/skill-calendar-anomaly-scanner/) | `composite` | `—` | [quantskills/skill-calendar-anomaly-scanner](https://github.com/quantskills/skill-calendar-anomaly-scanner) | 从带日期收益序列扫描日历异常，结合稳健检验、Bootstrap 和多重检验校正输出结果。 |
| [`skill-factor-debug`](quant/validation/skill-factor-debug/) | `composite` | `—` | [quantskills/skill-factor-debug](https://github.com/quantskills/skill-factor-debug) | 提供按症状、病因和验证手段组织的因子失效诊断手册。 |
| [`skill-factor-decay`](quant/validation/skill-factor-decay/) | `composite` | `—` | [quantskills/skill-factor-decay](https://github.com/quantskills/skill-factor-decay) | 分析多期限Rank IC、换手和分组收益的衰减，并估计半衰期。 |
| [`skill-forecast-calibration-audit`](quant/validation/skill-forecast-calibration-audit/) | `composite` | `—` | [quantskills/skill-forecast-calibration-audit](https://github.com/quantskills/skill-forecast-calibration-audit) | 审计概率预测的校准程度，而非只评估样本排序。 |
| [`skill-numerical-leak-check`](quant/validation/skill-numerical-leak-check/) | `composite` | `—` | [quantskills/skill-numerical-leak-check](https://github.com/quantskills/skill-numerical-leak-check) | 通过数值测试检测量化研究流程中的前视和数据泄漏。 |
| [`skill-signal-stability-audit`](quant/validation/skill-signal-stability-audit/) | `composite` | `—` | [quantskills/skill-signal-stability-audit](https://github.com/quantskills/skill-signal-stability-audit) | 审计量化信号跨期和跨样本的稳定性。 |
| [`skill-survivorship-universe-auditor`](quant/validation/skill-survivorship-universe-auditor/) | `composite` | `—` | [quantskills/skill-survivorship-universe-auditor](https://github.com/quantskills/skill-survivorship-universe-auditor) | 审计回测前的点时证券池成员、标识和退市收益数据。 |
| [`skill-walk-forward-validator`](quant/validation/skill-walk-forward-validator/) | `composite` | `—` | [quantskills/skill-walk-forward-validator](https://github.com/quantskills/skill-walk-forward-validator) | 用净化和隔离的滚动窗口验证截面信号的样本外表现。 |

---

## Clusters

Skills sharing a `cluster:` tag are intended to compose. See `_meta/clusters.md` for recommended pipelines.

### `loop-engineering`

- [`design-loop-project`](loop-engineering/design-loop-project/) — Orchestrates the complete loop-engineering workflow.
- [`qualify-loop-task`](loop-engineering/qualify-loop-task/) — Determines whether a task should be a loop, automation, or human-led process.
- [`specify-loop-contract`](loop-engineering/specify-loop-contract/) — Defines evidence, budgets, stop conditions, and escalation.
- [`design-loop-state`](loop-engineering/design-loop-state/) — Designs persistent state, attempt history, checkpoints, and recovery.
- [`build-loop-harness`](loop-engineering/build-loop-harness/) — Builds guidance, feedback sensors, observability, and permission boundaries.
- [`audit-loop-project`](loop-engineering/audit-loop-project/) — Audits safety, recoverability, and readiness before unattended execution.
- [`operate-loop-run`](loop-engineering/operate-loop-run/) — Runs triage, isolated execution, independent verification, and safe handoff.
- [`verify-loop-delivery`](loop-engineering/verify-loop-delivery/) — Independently reviews implementer output and returns an evidence-backed verdict.
- [`improve-loop-system`](loop-engineering/improve-loop-system/) — Evolves controls from evidence, review feedback, and drift.

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

### `ponytail`

- [`ponytail`](workmode/ponytail/) — Lazy senior-dev coding mode: force the minimal solution that works (YAGNI -> stdlib -> native -> one line -> minimum). Levels lite/full/ultra. Sibling: workmode/caveman.
- [`ponytail-audit`](workmode/ponytail-audit/) — Whole-repo audit for over-engineering: ranked list of what to delete/simplify/replace with stdlib/native. One-shot report, no fixes.
- [`ponytail-debt`](workmode/ponytail-debt/) — Harvest every ponytail: comment into a debt ledger so deliberate shortcuts get tracked. One-shot report, changes nothing.
- [`ponytail-gain`](workmode/ponytail-gain/) — Display ponytail's measured benchmark scoreboard (less code/cost, more speed). One-shot display, not a persistent mode.
- [`ponytail-help`](workmode/ponytail-help/) — Quick-reference card for all ponytail modes/skills/commands. One-shot display.
- [`ponytail-review`](workmode/ponytail-review/) — Code review hunting only over-engineering: one line per finding (delete/stdlib/native/yagni/shrink). Complements correctness-focused review.

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
