# 标准内容包 v1

必填顶层字段：`schema_version`、`content_type`、`package_id`、`run_at`、`status`、`window`、`items`、`sources`、`risks`。

`content_type` 固定为 `daily-news`；`status` 只使用 `ready_for_human_review` 或 `needs_review`。图片如需附带必须使用相对于内容包的路径，不得保存本机绝对路径。平台制作工具遇到未知版本必须停止，不得猜测字段。

