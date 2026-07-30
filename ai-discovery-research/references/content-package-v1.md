# AI 新发现内容包 v1

顶层字段：

- `schema_version`: 固定为 `1`。
- `content_type`: 固定为 `ai-discovery`。
- `package_id`: `ai-discovery-YYYY-MM-DD`。
- `run_at`: ISO 8601 北京时间。
- `status`: `ready_for_human_review` 或 `needs_review`。
- `window`: 搜索窗口。
- `selection`: 候选和入选数量。
- `items`: 入选条目。
- `candidates`: 全部候选和淘汰原因。
- `sources`: 入选条目的来源清单。
- `risks`: 本期风险和人工审核提示。

每个 `items[]` 至少包含：

- `name`
- `type`
- `official_url`
- `discovered_at`
- `official_sources`
- `use_case`
- `audience`
- `pricing`
- `requirements`
- `risks`
- `verification_status`
- `recommendation`
