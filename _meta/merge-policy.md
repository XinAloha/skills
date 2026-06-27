# Merge policy — 同源 / 同任务 skill 的并轨准则

> 多个来源的 skill 做同一件事时，本仓库不二选一，也不简单合并代码。准则是：**同粒度的指令越具体越好**，所以并轨方向是「把各家长处吸纳到同一个 SKILL.md 里」。短期内先并存 siblings，长期再合并。

## 当前 sibling 对

| 任务 | siblings | 长期方向 |
|---|---|---|
| 演示文档 | `content/guizang-ppt` (HTML 单文件 / WebGL) vs `content/slide-deck-baoyu` (图集导出 PDF/PPTX) | 暂保留两条路径；用户按交付物挑选；未来抽出共享的「内容到分页布局」atomic |
| 社交卡片 | `content/guizang-social-card` (瑞士/编辑风) vs `content/xhs-images-baoyu` (套餐式) | 暂保留；未来共享「卡片视觉系统」references |
| 中文 humanizer | `content/humanizer-zh` (改写) + `content/ai-check` (检测) + `content/format-markdown` (排版) | 已经分工清楚；维持 cluster `humanizer` |
| URL → MD 抽取 | `productivity/url-to-markdown` (主路径) + `productivity/youtube-transcript` (视频专精) + `productivity/x-to-markdown` (X 专精，DANGER) | 已经分工；维持 cluster `extract` |

## 合并步骤（当真正要把两个 siblings 合并时）

1. **挑底盘。** 取覆盖范围更大、references 更结构化的那个作为底盘。
2. **抽差异。** 对照另一份 skill 的 SKILL.md，列出底盘里没覆盖的 trigger、术语、参数、边界条件。
3. **写进底盘。** 把差异以 *同等粒度的指令* 增补进去。粒度判断：现有指令多详细，新增的就多详细；不要出现一段「abstract」夹一段「super concrete」。
4. **保留两份来源。** 合并后保留两个 `SOURCE.md`，或在底盘的 `SOURCE.md` 里加 `Additional upstream` 段落，把另一份的 repo + path + 上次同步日期写清楚。
5. **测试一次。** 让 agent 拿同一道题分别跑「合并前底盘」与「合并后」，确认行为只增不减。
6. **Sibling 目录降级。** 合并完成后，被合并的 sibling 目录改为只放一个 `MOVED.md`，指向新主目录。**不要直接删除**——其他项目可能正在通过软链接挂着。

## 不要合并的情况

- 两个 skill 表面看似相同，但调用方差异大（例如 `post-to-wechat` 走 API，`post-to-weibo` 走 CDP）。这是**实现差**不是任务差，应该保留为不同 skill。
- 上游仍在快速迭代，合并会导致更新冲突。先维持 siblings + 文档对照表，等上游稳定再合并。
- 一边是 atomic、一边是 composite，规模差距太大。先把 atomic 的精华移到 composite 的 `references/` 里，作为快速版本入口。

## 合并标准（"指令越详细越好" 的具体落地）

判断当前 SKILL.md 是否「足够详细」：

- ❌ 指令停在「分析内容结构」「输出合适的样式」这种动词层 → 不够
- ✅ 指令到了「按 H2 数量分组：≤3 用 layout-A；4–7 用 layout-B；>7 提示用户拆文」 → 足够

每次合并都应该让 SKILL.md 在判定边界、参数命名、错误兜底这三个维度上更精细，而不是仅仅变长。
