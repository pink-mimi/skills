# 公众号复制与审核状态分离设计

## 目标

允许运营者在新闻尚未完成核验时复制公众号正文进行排版，同时保持“可复制”和“可发布”两个状态的明确区分，并确保内部审核说明不会进入读者正文。

## 当前问题

- `copy_eligibility()` 将未核验状态直接映射为禁用复制按钮，导致运营者无法先行排版。
- `editor_note` 被渲染到 `#wechat-content` 内，内部的来源补充、核验要求和发布提示会随正文一起复制给读者。
- 页面只有一个按钮状态，容易把“复制成功”误解为“内容已经可以发布”。

## 状态模型

页面保留两类独立状态：

1. **复制状态**
   - 只要正文所需的读者字段完整，就允许复制。
   - 新闻存在 `unverified` 或 `partial` 时，按钮显示“复制正文（发布前需核验）”。
   - 全部新闻均为 `verified` 时，按钮显示“复制正文，可发布”。
   - 缺少 `what_happened`、`why_it_matters`、`reader_action` 或 `keywords` 时禁用复制，因为正文自身不完整。

2. **发布状态**
   - 存在 `unverified` 时显示醒目的外部警告，明确列出未核验条目数量，并说明不得直接发布。
   - 仅存在 `partial` 时显示外部复核提示。
   - 全部为 `verified` 时不显示核验警告。
   - 复制操作不得改变内容包、清单或运行报告中的审核状态。

`editor_note` 不再作为读者正文必填字段；它是可选的内部审核字段。

## 页面边界

`#wechat-content` 只包含：

- 统计时段
- 30 秒速览
- 新闻脉络图
- 每条新闻的关键词
- 发生了什么
- 为什么重要
- 普通人需要注意什么
- 可选的后续关注
- 参考来源
- 面向读者的动态来源说明

以下内容必须位于 `#wechat-content` 外：

- `editor_note`
- `verification_notes`
- `verification_status`
- 未核验或部分核验数量
- 来源待补充要求
- 发布前人工复核要求
- 封面和标题预览

外部审核区按新闻条目列出标题、核验状态和 `editor_note`，供运营者处理，但复制按钮只复制 `#wechat-content`。

## 生成清单

`render-manifest.json` 保留并明确以下字段：

- `copy_allowed`：正文是否完整、是否允许复制。
- `copy_reason`：允许或禁止复制的原因。
- `publish_ready`：所有条目是否均为 `verified`。
- `review_counts`：`verified`、`partial`、`unverified` 的数量。
- `input_status`：原始内容包状态，不因成功排版而提升。

## 测试标准

- 完整但含 `unverified` 的新闻包可以复制，按钮不带 `disabled`。
- 未核验页面显示“发布前需核验”，且不能显示“可发布”。
- 全部 `verified` 时按钮显示“复制正文，可发布”。
- 缺少读者正文必填字段时仍禁用复制。
- `editor_note` 出现在复制区域外，但不出现在 `#wechat-content` 或公众号成稿 Markdown 中。
- `render-manifest.json` 同时正确记录 `copy_allowed` 和 `publish_ready`。
- 现有图片内嵌、封面尺寸、来源链接和 GitHub 热门模板测试继续通过。

## 非目标

- 不自动登录、上传或发布微信公众号内容。
- 不把未核验条目自动升级为 `partial` 或 `verified`。
- 不隐藏未核验风险。
- 不改变新闻采集与事实核验流程。
