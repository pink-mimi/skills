# 标准内容包 v1

必填顶层字段：`schema_version`、`content_type`、`package_id`、`run_at`、`status`、`window`、`editorial`、`items`、`sources`、`risks`。

`content_type` 固定为 `daily-news`；`status` 只使用 `ready_for_human_review` 或 `needs_review`。图片如需附带必须使用相对于内容包的路径，不得保存本机绝对路径。平台制作工具遇到未知版本必须停止，不得猜测字段。

`editorial` 可包含 `title`、`article_title`、`cover_title`、`overview`、`follow_up` 和 `summary`。`title` 可作为内部归档名称，`article_title` 是面向读者的文章标题。每条新闻除标题、时间、来源和链接外，还必须包含 `what_happened`、`editor_note` 与 `keywords`；`why_it_matters`、`reader_action` 和 `reader_tip` 仅在存在明确公共影响、可执行事项或额外实用提醒时提供。可选的 `reader_tip` 必须能够直接发布给读者，不能包含运营审核话术。必填字段不完整时状态必须为 `needs_review`。

## daily-news schema v2

v2 仍保持平台无关，但面向“今日简报”双层结构：

- `schema_version` 固定为 `2`，`content_type` 固定为 `daily-news`。
- `editorial.article_title` 使用发布日标题，例如 `8月3日今日简报：政策、科技与全球动态`。
- `editorial.lead` 是正文导读。
- `editorial.focus_event_ids` 必须引用 `items[].event_id`，不得复制新闻对象。
- `items[]` 必须包含 `event_id`、`title`、`brief`、`category`、`what_happened`、`keywords`、`verification_status`、`published_at`、`source` 和 `url`。
- `why_it_matters`、`reader_action`、`reader_tip` 只在内容确实需要时出现；`editor_note` 仅供审核，不进入读者正文。
- `edition_mode` 记录 `standard` 或 `compact`。

正常版包含 8—15 条新闻和 3—5 个重点，默认目标是 12 条新闻和 4 个重点。精简版允许 5—7 条新闻。少于 5 条、缺 `brief`、重点引用重复或不存在、关键事实未核验时必须保持 `needs_review`。
