---
name: wechat-content
description: Use when 用户已有 daily-news 或 github-hot 标准内容包，需要生成可一键复制到微信公众号编辑器的中文文章、栏目化排版、配图和左长右方组合封面审核包。
---

# 微信公众号内容制作

## 核心原则

读取 `content-package.json`，根据 `content_type` 选择新闻或 GitHub 热门栏目模板。不得重新改变研究层事实；输入为 `needs_review` 时保留审核警告。只生成审核包，不登录、上传或发布公众号。

## 工作流程

1. 读取内容包并验证 `schema_version: 1`。
2. 按 `daily-news` 或 `github-hot` 选择栏目结构，再选择视觉主题。
3. 生成标题、摘要、Markdown、内联样式 HTML 和图片。
4. 封面固定输出 `1283×383` 合并图：左侧 `900×383` 长封面，右侧 `383×383` 方封面；同时导出两个独立上传文件。
5. 运行 `verify`，再用微信手机预览人工检查。

```powershell
python scripts/run.py all --input outputs/daily-news/2026-07-20/content-package.json --output-root outputs --theme auto
```

HTML 顶部按钮只复制 `wechat-content` 正文区域，不复制工具栏、封面预览、备用标题或审核说明。

