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
- `popularity_signals`
- `risks`
- `verification_status`
- `verification_grade`
- `recommendation`

每个 `items[]` 可以包含可选字段 `official_images`，用于向平台制作层提供可追溯图片元数据。每条图片记录包含：

- `url`: 官方图片地址。
- `source_page`: 图片所在官方页面。
- `source_path`: 可选，本地缓存路径；没有本地文件时平台层不得假装已经有官方图。
- `description`: 图片用途说明。
- `usage_status`: `approved`、`verified` 或 `needs_review`。
- `verification_status`: `verified`、`approved` 或 `needs_review`。
- `is_official`: 仅官方发布页、官方文档、官方博客、官方模型卡等来源可标记为 `true`。

`mainland_availability.status` 只能使用：

- `可直接使用`
- `存在限制`
- `需海外账号`

`verification_grade`：

- `A`: 官方资料完整，并有多个独立公开反馈可参考。
- `B`: 官方资料完整，但独立反馈不足。可以进入审核包，但正文需写“主要依据官方资料”。
- `C`: 只有宣传信息、价格/限制/开放范围不清楚，或关键事实无法核验。不得入选发布。

研究层只生成平台无关内容包，不包含微信公众号 HTML、封面、发布字段或自动发布动作。

`popularity_signals` 记录候选为什么算“最近热门”，例如官方近期发布、多平台报道、社区讨论、GitHub/ModelScope/Hugging Face 热度、应用商店反馈或普通用户可试用路径。入选对象至少需要 2 个可追溯信号；热度不足的候选可以保留在 `candidates`，但不得作为本期重点对象。
