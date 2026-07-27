# GitHub 热门内容包 v2

顶层固定为 `schema_version: 2`、`content_type: github-hot`，并包含运行窗口、状态、筛选统计、入选项目、完整候选、来源和全局风险。

## 筛选契约

- 候选 12—20 个，深度核验至少 8 个，入选 5—7 个，默认目标 5 个。
- AI 项目最多 3 个，同类项目最多 3 个，最近 8 期默认去重。
- `candidates` 保留所有候选；未入选项必须有 `rejection_reasons`。
- 合格项目不足 5 个时允许减少，不用低质量项目凑数，但状态必须为 `needs_review`。

## 入选项目

每项包含：

- `reader_card`：栏目标签、名称、摘要、一句话推荐、3 个亮点、受众、难度、指标和面向读者的提醒。
- `verification`：README、许可证、维护、使用条件、分级风险和证据链接。
- `visual_candidates`：图片类型、原始地址、来源页、是否真实界面、许可证、使用状态和核验时间。
- `image2_brief`：只依据已核验用途生成；必须规避 Logo、虚构软件界面、文字和虚构数据。

`stars`、`forks`、`weekly_stars` 等动态指标必须带 `verified_at`。无法可靠确认周增 Star 时写 `null`，不得写 0。未找到许可证时使用 `license.status: not_found`，不得推断项目可自由商用。

只有来源明确、许可证已核验且 `usage_status: approved` 的官方截图可自动使用。授权未知、需复核、Logo 或社交预览图只能留作审核候选。
