# 标准内容包 v1

必填顶层字段：`schema_version`、`content_type`、`package_id`、`run_at`、`status`、`window`、`items`、`sources`、`risks`。

`content_type` 固定为 `github-hot`；每个项目必须保留仓库、用途、许可证、最近提交、平台、安装门槛、受众、风险和官方地址。平台制作工具遇到未知版本必须停止，不得猜测字段。

