# 标准内容包 v1

必填顶层字段：`schema_version`、`content_type`、`package_id`、`run_at`、`status`、`window`、`editorial`、`items`、`sources`、`risks`。

`content_type` 固定为 `daily-news`；`status` 只使用 `ready_for_human_review` 或 `needs_review`。图片如需附带必须使用相对于内容包的路径，不得保存本机绝对路径。平台制作工具遇到未知版本必须停止，不得猜测字段。

`editorial` 可包含 `title`、`article_title`、`cover_title`、`overview`、`follow_up` 和 `summary`。`title` 可作为内部归档名称，`article_title` 是面向读者的文章标题。每条新闻除标题、时间、来源和链接外，还必须包含 `what_happened`、`why_it_matters`、`reader_action`、`editor_note` 与 `keywords`；可选的 `reader_tip` 是能够直接发布给读者的简短提示。字段不完整时状态必须为 `needs_review`。
