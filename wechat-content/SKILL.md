---
name: wechat-content
description: Use when 用户已有标准内容包，需要制作“未完地图”微信公众号审核包，包括栏目化写作、内联排版、内容配图、一键复制，以及左长右方组合封面；当前内置 daily-news 与 github-hot 两种独立栏目模板。
---

# 微信公众号内容制作

## 核心原则

读取 `content-package.json`，先按 `content_type` 选择栏目模板，再选择视觉主题。栏目模板决定文章结构和图片语义，视觉主题只决定色彩与装饰，禁止用一套通用图冒充所有栏目。不得改变研究层事实；输入为 `needs_review` 时保留审核警告。只生成审核包，不登录、上传或发布公众号。

## 工作流程

1. 读取内容包并验证 `schema_version: 1`。
2. 必须读取对应栏目规范：新闻读 [references/daily-news.md](references/daily-news.md)，GitHub 热门读 [references/github-hot.md](references/github-hot.md)。
3. 读取 [references/visual-and-copy.md](references/visual-and-copy.md)，生成标题、摘要、Markdown、内联样式 HTML 和内容相关图片。
4. 封面固定输出 `1283×383` 合并图：左侧 `900×383` 长封面，右侧 `383×383` 方封面；同时导出两个独立上传文件。
5. 输出 `render-manifest.json`，记录内容模板、主题及版本，保证同一内容包可稳定重排。
6. 运行 `verify`，再用微信手机预览人工检查。

```powershell
python scripts/run.py all --input outputs/daily-news/2026-07-20/content-package.json --output-root outputs --theme auto
```

HTML 顶部按钮只复制 `wechat-content` 正文区域，不复制工具栏、封面预览、备用标题或审核说明。

## 独立运行边界

本 Skill 不在运行时调用 `wechat-article-writer`。公众号写作层级、封面安全区、正文图片和复制规则已经按“未完地图”需求内置，因此换电脑安装后仍可运行。若 Image 2 可用，可先按栏目规范生成无文字主视觉，再由本地脚本完成准确中文与封面裁切；不可用时使用内容相关的本地模板，不得退化为空白几何占位图。

## 新增栏目

新增内容类型时同时提供栏目规范、文章构建器、图片语义、fixture 和回归测试；不得复制新闻或 GitHub 模板后只改标题。公共复制、HTML、封面尺寸和审核状态继续复用。
