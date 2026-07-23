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
3. 新闻条目必须包含 `what_happened`、`why_it_matters`、`reader_action`、`editor_note` 和 `keywords`；缺少时不得假装成稿完整，必须标记 `needs_review`、禁用复制按钮，并把审核提示放在复制区域之外。读者正文不得出现内部占位语。
4. 读取 [references/visual-and-copy.md](references/visual-and-copy.md) 和 [references/image2-workflow.md](references/image2-workflow.md)，生成标题、摘要、Markdown、内联样式 HTML 和内容相关图片。
   - `daily-news` 使用按北京时间星期选择的“七天七色”主题；只有配置缺失或日期异常时才使用中性“默认兜底”。
   - `github-hot` 使用独立的开源栏目主题，不参与新闻星期轮换。
   - 已生成当期 Image 2 无字图时，传入 `--image-input-dir`；否则使用对应星期素材。
5. 封面固定输出 `1283×383` 合并图：左侧 `900×383` 长封面，右侧 `383×383` 方封面；同时导出两个独立上传文件。
6. 输出 `render-manifest.json`，记录内容模板、主题及版本，保证同一内容包可稳定重排。
7. 运行 `verify`。只有输出为 `OK` 才表示内容和结构均达到可复制条件；`STRUCTURE_OK_CONTENT_NEEDS_REVIEW` 只表示文件结构正常，必须退回研究 Skill 补齐内容，不得称为验证通过。再用微信手机预览人工检查。

```powershell
python scripts/run.py all --input outputs/daily-news/2026-07-20/content-package.json --output-root outputs --theme auto

# 可选：使用当期 Image 2 生成的 cover.png 与 overview.png
python scripts/run.py all --input outputs/daily-news/2026-07-20/content-package.json --output-root outputs --theme auto --image-input-dir work/news-images
```

HTML 顶部按钮只复制 `wechat-content` 正文区域，不复制工具栏、封面预览、备用标题或审核说明。新闻结尾说明按当日主题动态生成，提示标题只依据分类、关键词、标题和摘要；GitHub 热门继续使用独立规则。

## 独立运行边界

本 Skill 不在运行时调用 `wechat-article-writer`。公众号写作层级、封面安全区、正文图片和复制规则已经按“未完地图”需求内置，因此换电脑安装后仍可运行。若 Image 2 可用，可先按栏目规范生成无文字主视觉，再由本地脚本完成准确中文与封面裁切；不可用时使用内容相关的本地模板，不得退化为空白几何占位图。

新闻运行报告中的 `image_mode` 必须如实记录：有效的当期输入为 `live_image2`，内置星期素材为 `weekday_fallback`。不得把兜底图描述成当期实时生成图。

## 新增栏目

新增内容类型时同时提供栏目规范、文章构建器、图片语义、fixture 和回归测试；不得复制新闻或 GitHub 模板后只改标题。公共复制、HTML、封面尺寸和审核状态继续复用。
