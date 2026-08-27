---
name: wechat-content
description: Use when 用户已有标准内容包，需要制作“未完地图”微信公众号审核包，包括栏目化写作、内联排版、内容配图、一键复制，以及左长右方组合封面；当前内置 daily-news、github-hot 与 ai-discovery 栏目模板。
---

# 微信公众号内容制作

## 核心原则

读取 `content-package.json`，先按 `content_type` 选择栏目模板，再选择视觉主题。栏目模板决定文章结构和图片语义，视觉主题只决定色彩与装饰，禁止用一套通用图冒充所有栏目。不得改变研究层事实；输入为 `needs_review` 时保留审核警告。只生成审核包，不登录、上传或发布公众号。

## 工作流程

1. 读取内容包并验证版本：`daily-news` 与 `ai-discovery` 使用 schema v1；`github-hot` 同时兼容旧 v1，并优先消费研究 Skill 输出的 schema v2。
2. 必须读取对应栏目规范：新闻读 [references/daily-news.md](references/daily-news.md)，GitHub 热门读 [references/github-hot.md](references/github-hot.md)，AI 新发现读 [references/ai-discovery.md](references/ai-discovery.md)。
3. 新闻读者正文必须包含 `what_happened` 和 `keywords`；`why_it_matters`、`reader_action` 与 `reader_tip` 按内容需要渲染，没有实质内容时省略，不得为了卡片完整补写套话。`reader_tip` 只用于安全、出行、办理或消费等可执行提醒；含“发布前”“待核验”“运营者”“复核数字”等内部审核话术时移到复制区外。缺少必填字段时必须标记 `needs_review` 并禁用复制按钮。读者字段完整时允许复制；存在 `partial` 或 `unverified` 时，必须在复制区外提示发布前核验，并明确不得把成功复制视为发布就绪。`editor_note`、核验状态和审核要求只供运营者查看，不得进入读者正文。
4. 读取 [references/visual-and-copy.md](references/visual-and-copy.md) 和 [references/image2-workflow.md](references/image2-workflow.md)，生成标题、摘要、Markdown、内联样式 HTML 和内容相关图片。每日新闻标题必须规范为统计窗口起始日加 `国内要闻：主题概括`，上游 `article_title` 不得绕过此前缀。
   - `daily-news` 使用按北京时间星期选择的“七天七色”主题；只有配置缺失或日期异常时才使用中性“默认兜底”。
   - `github-hot` schema v2 使用编辑卡片式读者结构，并依据本期证据生成动态开头与动态结尾；完整许可证、维护、核验时间、内部风险、淘汰原因和图片授权信息必须位于复制区外，不把审核负担转嫁给读者。
   - `ai-discovery` 使用工具介绍型读者结构，说明是什么、主要功能、怎么使用、适用场景、费用/地区限制、风险和官方地址；没有实际测试时只写公开资料口径，不伪造亲身体验；只有已核验的官方来源图片才能标注为“官方示例图”。
   - GitHub 热门封面使用 Image2 无字主视觉时，优先生成“开源夜市/工具市集地图”场景；本地脚本叠加准确中文标题，并分别输出长封面和方形封面。品牌胶囊与副标共享同一行视觉中心线，不使用白色卡片遮住底图。
   - GitHub 项目图按“已批准官方真实截图 → 当期 Image2 用途示意图”选择；二者都不可用时，该项目不展示图片，禁止用低质本地项目卡硬凑。
   - GitHub 正文项目图少于 3 张时，使用 `--image-input-dir/articles/NN.png` 的 Image2 文章级主题插图补足；没有 Image2 主题图时才使用本地科技主题插图，保证整篇至少有三四张可读图片。
   - 已生成当期 Image 2 无字图时，传入 `--image-input-dir`；否则使用对应栏目兜底素材。
5. 封面固定输出 `1283×383` 合并图：左侧 `900×383` 长封面，右侧 `383×383` 方封面；同时导出两个独立上传文件。
6. 输出 `render-manifest.json`，记录内容模板、主题及版本，保证同一内容包可稳定重排。
7. 运行 `verify`。`OK` 表示正文完整且全部新闻已经核验；`OK_WITH_REVIEW_REQUIRED` 表示允许复制排版，但仍有部分核验或未核验内容、不得直接发布；`STRUCTURE_OK_CONTENT_NEEDS_REVIEW` 表示读者正文仍不完整，复制按钮禁用。再用微信手机预览人工检查。

```powershell
python scripts/run.py all --input outputs/daily-news/2026-07-20/content-package.json --output-root outputs --theme auto

# 可选：使用当期 Image 2 生成的 cover.png 与 overview.png
python scripts/run.py all --input outputs/daily-news/2026-07-20/content-package.json --output-root outputs --theme auto --image-input-dir work/news-images

# GitHub v2：官方审核图目录与 Image2 目录可同时传入，自动按优先级选择
python scripts/run.py all --input content-package.json --output-root outputs --project-image-dir work/official --image-input-dir work/image2 --image-mode auto

# AI 新发现：读取研究层内容包并生成公众号审核包
python scripts/run.py all --input outputs/ai-discovery/2026-07-30/content-package.json --output-root outputs --theme auto
```

HTML 顶部按钮只复制 `wechat-content` 正文区域，不复制工具栏、封面预览、备用标题或审核说明。新闻结尾说明按当日主题动态生成，提示标题只依据分类、关键词、标题和摘要；GitHub 热门和 AI 新发现继续使用独立规则。

## 独立运行边界

本 Skill 不在运行时调用 `wechat-article-writer`。公众号写作层级、封面安全区、正文图片和复制规则已经按“未完地图”需求内置，因此换电脑安装后仍可运行。若 Image 2 可用，可先按栏目规范生成无文字主视觉，再由本地脚本完成准确中文与封面裁切；不可用时使用内容相关的本地模板，不得退化为空白几何占位图。

新闻运行报告中的 `image_mode` 必须如实记录：有效的当期输入为 `live_image2`，内置星期素材为 `weekday_fallback`。不得把兜底图描述成当期实时生成图。

## 新增栏目

新增内容类型时同时提供栏目规范、文章构建器、图片语义、fixture 和回归测试；不得复制既有模板后只改标题。公共复制、HTML、封面尺寸和审核状态继续复用。

## daily-news v2 今日简报

`daily-news` 同时兼容 schema v1 和 v2。v1 继续走旧模板；v2 使用“今日简报”双层结构：第一屏显示发布日、星期和统计窗口，正文先按主题分组输出“今日速览”，再严格按照 `editorial.focus_event_ids` 展开“重点解读”。

v2 每条速览必须显示标题、发布级 `brief` 和来源机构，完整 URL 集中放在“参考来源”。来源优先使用 `organization`，不得把“滚动”“日期归档”等采集器标签显示给读者。缺 `brief`、`brief` 含“直接面向读者”“适合重点提示”“适合放在”等内部编辑话术、或 `focus_event_ids` 重复/引用不存在时禁用复制按钮，并把原因显示在复制区外。`editor_note`、核验状态和内部审核提示不得进入 `#wechat-content`。

标题使用发布日 `M月D日今日简报：主题概括`；统计窗口仍显示前一日 06:00 至当日 06:00。不加入每日金句、农历鸡汤或无来源装饰内容。
