# AI 新发现内容包 v1

顶层字段：

- `schema_version`: 固定为 `1`。
- `content_type`: 固定为 `ai-discovery`。
- `package_id`: `ai-discovery-YYYY-MM-DD`。
- `run_at`: ISO 8601 北京时间。
- `status`: `ready_for_human_review` 或 `needs_review`。
- `window`: 搜索窗口。
- `selection`: 候选、聚焦复核和入选数量。
- `items`: 本期最终入选对象。AI 新发现每期只能有 1 条。
- `candidates`: 全部候选、是否入选和淘汰原因。
- `sources`: 入选对象的来源清单。
- `risks`: 本期风险和人工审核提示。

每个 `items[]` 至少包含：

- `name`
- `type`
- `company`
- `official_url`
- `discovered_at`
- `official_sources`
- `use_case`
- `audience`
- `not_for`
- `scenarios`
- `platforms`
- `supports_chinese`
- `mainland_availability`
- `pricing`
- `pricing_details`
- `requirements`
- `privacy_and_rights`
- `public_feedback`
- `risks`
- `verification_status`
- `verification_grade`
- `recommendation`

`mainland_availability.status` 只能使用：

- `可直接使用`
- `存在限制`
- `需海外账号`

`verification_grade`：

- `A`: 官方资料完整，并有多个独立公开反馈可参考。
- `B`: 官方资料完整，但独立反馈不足。可以进入审核包，但正文需写“主要依据官方资料”。
- `C`: 只有宣传信息、价格/限制/开放范围不清楚，或关键事实无法核验。不得入选发布。

研究层只生成平台无关内容包，不包含微信公众号 HTML、封面、发布字段或自动发布动作。
