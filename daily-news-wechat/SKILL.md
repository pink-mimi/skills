---
name: daily-news-wechat
description: Use when 用户需要采集每日新闻、整理昨日国内外大事、生成经核验的中文新闻摘要、微信公众号文章或定时新闻审核包。
---

# 每日新闻微信公众号工作流

## 概述

生成一套“先审核、后发布”的每日新闻材料，明确时间边界、保留来源追溯、兼顾类别覆盖，并输出微信公众号正文、HTML 和独立封面。不得虚构发布时间，也不得用弱新闻凑数量。

## 工作流程

1. 读取 `assets/default-config.json`；只有需要自定义时才复制到调用项目。
2. 筛选和写作前先读取 `references/editorial-policy.md`。
3. 运行 `python scripts/run.py collect --output-root <project>` 进行确定性的 RSS 采集；需要时可使用可用的网络工具补充权威来源。
4. 在 JSON 中保留完整发布时间和时区。发布时间未知的内容进入待核验区，不得猜测。
5. 运行 `python scripts/run.py build --output-root <project> [--custom extra.json]`。
6. 打开 `selected.json`、`needs-review.json` 和原始链接。政策、灾情、公共安全及重要数字必须对照第一方来源核验。
7. 参照 `assets/article-template.md` 优化 `article.md`：事实表述客观，说明普通人影响，并提供可执行的“小清提醒”。
8. 重新生成或更新 `wechat.html`、横版封面、方形封面、备选标题、核验说明和运行报告。
9. 运行 `python scripts/run.py verify --output-root <project>`。如果状态为 `needs_review`，应说明缺口，不得声称内容已达到发布条件。

## 命令

| 命令 | 用途 |
|---|---|
| `collect` | 从配置的 RSS 来源采集到 `raw-news.json` |
| `build` | 过滤、去重、筛选并生成审核包 |
| `verify` | 检查必要文件和准备状态 |
| `all` | 依次运行以上三个阶段 |

使用 `--run-at 2026-07-19T06:20:00+08:00` 可复现指定运行；使用 `--config <file>` 调整时间窗口、地区、来源、数量限制或主题。

## 编辑审核门槛

- 严格使用配置的左闭右开时间窗口。
- 默认选取 5—8 条，至少覆盖 4 个类别，每个类别最多 2 条。
- 政策、灾情和公共安全信息必须有官方来源。
- 动态数字注明“截至某时”，不同来源数字冲突时不得取平均值。
- 信息来源显示“机构名称 + 可点击文章标题”，正文不展示裸网址。
- 仅生成待审核材料。除非用户另行明确授权，不得自动发布或保存微信公众号密钥。

## 自定义

- 在 `assets/default-config.json` 中修改时间和新闻范围。
- 需要国外新闻时，在 `regions` 中启用 `international`，并启用对应国际来源。
- 新增 RSS 来源无需修改核心代码；只有非 RSS 格式才增加采集模块。
- 平台定时任务保持在核心流程之外。Codex、Claude Code、cron 和 Windows 任务计划程序都应调用同一组 Python 命令。

## 常见错误

- 把网页更新时间当作事件发生或正式发布时间。
- 未转换时区就混合比较发布时间。
- 将同一事件的多篇报道计为多条新闻。
- 为达到最低数量而加入旧闻、营销内容或无法核验的信息。
- 把横版与方形封面拼成一张图片上传。
- `verify` 返回非零状态时仍宣称审核包可以发布。
