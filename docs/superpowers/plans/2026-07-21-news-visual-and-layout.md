# News Seven-Day Visual and Layout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 `wechat-content` 的新闻栏目实现七天七色、七种构图、Image 2 动态优先与默认主题兜底，并恢复更适合公众号连续阅读的正文排版。

**Architecture:** 新建独立的新闻视觉选择模块，按北京时间星期选择主题与备用素材；渲染器接收明确的视觉上下文，不再自行猜测图片来源。代理可把当期 Image 2 无字图片放入输入目录，脚本验证后使用；否则稳定选择星期素材，主题缺失时使用第 8 套默认主题。GitHub 热门继续沿用原有独立主题和渲染路径。

**Tech Stack:** Python 3、Pillow、JSON、内联 HTML/CSS、unittest、Image 2 无字 PNG 素材。

---

## 文件结构

- Create: `wechat-content/scripts/news_visuals.py`：新闻星期主题、素材选择和输入图片验证。
- Modify: `wechat-content/assets/default-config.json`：七天色板、默认主题和素材版本。
- Create: `wechat-content/assets/news-weekday/<variant>/cover.png`：8 张封面备用底图。
- Create: `wechat-content/assets/news-weekday/<variant>/overview.png`：8 张正文备用底图。
- Modify: `wechat-content/scripts/rendering.py`：接受视觉上下文并恢复新闻正文排版。
- Modify: `wechat-content/scripts/run.py`：新增动态图片输入参数、manifest 字段和验证。
- Modify: `wechat-content/tests/test_skill.py`：星期轮换、默认兜底、动态输入、栏目隔离和排版回归测试。
- Create: `wechat-content/tests/fixtures/daily-news-content-package-monday.json`：确定星期选择的离线 fixture。
- Modify: `wechat-content/SKILL.md`：代理生成 Image 2 图片并传入脚本的流程。
- Modify: `wechat-content/references/image2-workflow.md`：七天色板、提示词、检查与降级规则。
- Modify: `wechat-content/references/daily-news.md`：新闻排版的稳定规则。
- Modify: `wechat-content/README.md`：中文使用步骤、运行模式和效果说明。

### Task 1: 七天主题选择器

**Files:**
- Create: `wechat-content/scripts/news_visuals.py`
- Modify: `wechat-content/assets/default-config.json`
- Test: `wechat-content/tests/test_skill.py`

- [ ] **Step 1: 写星期轮换和默认兜底的失败测试**

```python
def test_seven_weekdays_use_seven_news_themes_and_default_is_separate(self):
    from news_visuals import choose_news_visual
    names=[]
    for day in range(13,20):
        choice=choose_news_visual(datetime.fromisoformat(f"2026-07-{day:02d}T06:00:00+08:00"),CONFIG,ASSETS)
        names.append(choice["name"])
    self.assertEqual(len(set(names)),7)
    self.assertEqual(
        choose_news_visual(datetime.fromisoformat("2026-07-20T06:00:00+08:00"),CONFIG,ASSETS)["name"],
        names[0],
    )
    self.assertNotIn(CONFIG["news_visuals"]["default"]["name"],names)

def test_missing_weekday_theme_uses_default(self):
    broken=json.loads(json.dumps(CONFIG))
    broken["news_visuals"]["weekdays"].pop("monday")
    choice=choose_news_visual(datetime.fromisoformat("2026-07-20T06:00:00+08:00"),broken,ASSETS)
    self.assertEqual(choice["name"],"unfinished-map-default")
    self.assertEqual(choice["fallback_reason"],"weekday_theme_missing")
```

- [ ] **Step 2: 运行测试并确认因模块不存在而失败**

Run: `python -m unittest wechat-content.tests.test_skill.WechatContentTests.test_seven_weekdays_use_seven_news_themes_and_default_is_separate -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'news_visuals'`.

- [ ] **Step 3: 写最小主题选择器**

```python
WEEKDAY_KEYS=("monday","tuesday","wednesday","thursday","friday","saturday","sunday")

def choose_news_visual(run_at, config, assets_root):
    key=WEEKDAY_KEYS[run_at.weekday()]
    data=config["news_visuals"]["weekdays"].get(key)
    reason=""
    if not data:
        data=config["news_visuals"]["default"]
        reason="weekday_theme_missing"
    result=dict(data)
    result["weekday"]=key
    result["fallback_reason"]=reason
    result["cover_path"]=assets_root/result["cover"]
    result["overview_path"]=assets_root/result["overview"]
    return result
```

在 `default-config.json` 中加入 `news_visuals.version: "1.0.0"`、7 个 weekday 项和 `default` 项；每项明确 `name`、`palette`、`cover`、`overview`。

- [ ] **Step 4: 运行两个选择器测试并确认通过**

Run: `python -m unittest wechat-content.tests.test_skill.WechatContentTests.test_seven_weekdays_use_seven_news_themes_and_default_is_separate wechat-content.tests.test_skill.WechatContentTests.test_missing_weekday_theme_uses_default -v`

Expected: 2 tests, OK.

- [ ] **Step 5: 提交主题选择器**

```powershell
git add wechat-content/scripts/news_visuals.py wechat-content/assets/default-config.json wechat-content/tests/test_skill.py
git commit -m "feat: add seven-day news theme selection"
```

### Task 2: 七天备用图片素材

**Files:**
- Create: `wechat-content/assets/news-weekday/monday/cover.png`
- Create: `wechat-content/assets/news-weekday/monday/overview.png`
- Create: corresponding `tuesday` through `sunday` and `default` pairs
- Test: `wechat-content/tests/test_skill.py`

- [ ] **Step 1: 写 16 张素材存在性、尺寸和体积失败测试**

```python
def test_all_news_visual_assets_exist_and_are_valid(self):
    for variant in (*WEEKDAY_KEYS,"default"):
        for filename in ("cover.png","overview.png"):
            path=SKILL/"assets/news-weekday"/variant/filename
            self.assertTrue(path.exists(),path)
            with Image.open(path) as image:
                self.assertGreaterEqual(image.width,1200)
                self.assertEqual(round(image.width/image.height,2),round(16/9,2))
            self.assertLess(path.stat().st_size,2*1024*1024)
```

- [ ] **Step 2: 运行测试并确认缺少素材而失败**

Run: `python -m unittest wechat-content.tests.test_skill.WechatContentTests.test_all_news_visual_assets_exist_and_are_valid -v`

Expected: FAIL on the first missing weekday asset.

- [ ] **Step 3: 用 Image 2 生成无字素材**

对 8 套主题分别生成 cover 和 overview。每次调用使用完整提示词：

```text
Asset type: 16:9 WeChat daily-news {cover|overview} reusable fallback.
Subject: {weekday theme scenes from the approved specification}.
Style: premium soft 3D paper-cut miniature diorama on a pale map, continuous route and coordinate nodes.
Palette: {configured weekday palette}.
Composition: cover leaves a safe title area; overview uses a distinct full-width route composition.
Constraints: no text, letters, numbers, labels, blank boxes, UI, logo, watermark, brand marks, or real news footage.
```

逐张使用 `view_image` 检查，再复制到对应目录；使用 Pillow 只做尺寸和 PNG 压缩，不改变内容。

- [ ] **Step 4: 运行素材测试并确认通过**

Run: `python -m unittest wechat-content.tests.test_skill.WechatContentTests.test_all_news_visual_assets_exist_and_are_valid -v`

Expected: 1 test, OK.

- [ ] **Step 5: 提交备用图库**

```powershell
git add wechat-content/assets/news-weekday wechat-content/tests/test_skill.py
git commit -m "feat: add weekday news visual library"
```

### Task 3: 动态 Image 2 输入与降级记录

**Files:**
- Modify: `wechat-content/scripts/news_visuals.py`
- Modify: `wechat-content/scripts/run.py`
- Modify: `wechat-content/scripts/rendering.py`
- Test: `wechat-content/tests/test_skill.py`

- [ ] **Step 1: 写动态输入成功和损坏输入降级的失败测试**

```python
def test_valid_live_images_are_used_and_recorded(self):
    live=Path(temp)/"live"; live.mkdir()
    shutil.copy(FIXTURE_COVER,live/"cover.png")
    shutil.copy(FIXTURE_OVERVIEW,live/"overview.png")
    out=self.build("daily-news-content-package.json",temp,extra=["--image-input-dir",str(live)])
    manifest=json.loads((out/"render-manifest.json").read_text(encoding="utf-8"))
    self.assertEqual(manifest["image_mode"],"live_image2")
    self.assertEqual(manifest["fallback_reason"],"")

def test_invalid_live_images_fall_back_to_weekday_asset(self):
    live=Path(temp)/"live"; live.mkdir()
    (live/"cover.png").write_bytes(b"not-png")
    out=self.build("daily-news-content-package.json",temp,extra=["--image-input-dir",str(live)])
    manifest=json.loads((out/"render-manifest.json").read_text(encoding="utf-8"))
    self.assertEqual(manifest["image_mode"],"weekday_fallback")
    self.assertEqual(manifest["fallback_reason"],"live_image_invalid")
```

- [ ] **Step 2: 运行测试并确认参数尚不存在而失败**

Run: `python -m unittest wechat-content.tests.test_skill.WechatContentTests.test_valid_live_images_are_used_and_recorded wechat-content.tests.test_skill.WechatContentTests.test_invalid_live_images_fall_back_to_weekday_asset -v`

Expected: FAIL with unrecognized argument `--image-input-dir`.

- [ ] **Step 3: 实现输入验证和视觉上下文**

```python
def valid_live_pair(directory, maximum_bytes):
    if not directory:
        return False
    paths=(directory/"cover.png",directory/"overview.png")
    try:
        for path in paths:
            if not path.exists() or path.stat().st_size>maximum_bytes:
                return False
            with Image.open(path) as image:
                image.verify()
        return True
    except (OSError,ValueError):
        return False
```

`run.py` 新增 `--image-input-dir`，构建：

```python
visual=choose_news_visual(run_at,config,ROOT/"assets")
if valid_live_pair(args.image_input_dir,config["images"]["maximum_bytes"]):
    visual.update(image_mode="live_image2",cover_path=args.image_input_dir/"cover.png",overview_path=args.image_input_dir/"overview.png",fallback_reason="")
else:
    if args.image_input_dir: visual["fallback_reason"]="live_image_invalid"
    visual["image_mode"]="weekday_fallback"
```

`render_images` 接收 `visual`，不再硬编码 `news-cover-base.png` 和 `news-overview-base.png`。

- [ ] **Step 4: 写入完整 manifest 字段并让测试通过**

```python
manifest.update({
    "image_mode":visual["image_mode"],
    "visual_variant":visual["name"],
    "color_theme":visual["palette_name"],
    "asset_version":config["news_visuals"]["version"],
    "fallback_reason":visual["fallback_reason"],
})
```

Run: `python -m unittest discover -s wechat-content/tests -v`

Expected: all tests OK.

- [ ] **Step 5: 提交动态输入路径**

```powershell
git add wechat-content/scripts/news_visuals.py wechat-content/scripts/run.py wechat-content/scripts/rendering.py wechat-content/tests/test_skill.py
git commit -m "feat: support live news visuals with fallback"
```

### Task 4: 恢复新闻正文排版

**Files:**
- Modify: `wechat-content/scripts/rendering.py`
- Modify: `wechat-content/tests/test_skill.py`

- [ ] **Step 1: 写排版结构失败测试**

```python
def test_news_layout_uses_continuous_reading_hierarchy(self):
    out=self.build("daily-news-content-package.json",temp)
    page=(out/"微信版.html").read_text(encoding="utf-8")
    self.assertIn('data-role="time-window"',page)
    self.assertIn('border-left:4px solid',page)
    self.assertIn('data-role="keywords"',page)
    self.assertIn('data-role="editor-note"',page)
    self.assertIn('data-role="section-label"',page)
    self.assertNotIn('data-role="section-label" style="background:',page)
```

- [ ] **Step 2: 运行测试并确认缺少语义标记而失败**

Run: `python -m unittest wechat-content.tests.test_skill.WechatContentTests.test_news_layout_uses_continuous_reading_hierarchy -v`

Expected: FAIL because `data-role="time-window"` is absent.

- [ ] **Step 3: 为 Markdown 构建器输出语义标记**

使用内部标记 `<!-- role:time-window -->`、`<!-- role:keywords -->`、`<!-- role:section-label -->` 和 `<!-- role:editor-note -->`；HTML 构建器读取标记并只对下一个块应用对应样式。不要把标记输出到复制正文。

- [ ] **Step 4: 实现旧版连续阅读样式**

```html
<blockquote data-role="time-window" style="margin:18px 0;padding:14px 16px;border-left:4px solid {primary};background:{soft};border-radius:0 7px 7px 0;line-height:1.8">...</blockquote>
<p data-role="keywords" style="padding:11px 14px;background:{soft};color:{primary};border-radius:6px;font-weight:700">...</p>
<p data-role="section-label" style="margin:18px 0 6px;color:{ink};font-size:17px;font-weight:800">...</p>
<blockquote data-role="editor-note" style="margin:18px 0;padding:14px 16px;background:{soft};border-radius:7px;color:{ink}">...</blockquote>
```

“30 秒速览”列表使用 `margin:6px 0 6px 18px;line-height:1.75`；新闻标题为深色 22px/800；正文卡片背景保持白色，不给三个解释小标题增加背景框。

- [ ] **Step 5: 运行排版测试和整套测试**

Run: `python -m unittest discover -s wechat-content/tests -v`

Expected: all tests OK.

- [ ] **Step 6: 提交排版恢复**

```powershell
git add wechat-content/scripts/rendering.py wechat-content/tests/test_skill.py
git commit -m "fix: restore continuous news reading layout"
```

### Task 5: 保证 GitHub 栏目隔离

**Files:**
- Modify: `wechat-content/tests/test_skill.py`
- Modify: `wechat-content/scripts/run.py` only if the failing test exposes coupling

- [ ] **Step 1: 写栏目隔离失败保护测试**

```python
def test_github_render_does_not_use_news_weekday_visuals(self):
    out=self.build("github-hot-content-package.json",temp)
    manifest=json.loads((out/"render-manifest.json").read_text(encoding="utf-8"))
    page=(out/"微信版.html").read_text(encoding="utf-8")
    self.assertEqual(manifest["content_template"],"github-hot")
    self.assertNotIn("weekday",manifest.get("visual_variant",""))
    self.assertNotIn("昨日新闻",page)
    self.assertIn("开源坐标",page)
```

- [ ] **Step 2: 运行隔离测试**

Run: `python -m unittest wechat-content.tests.test_skill.WechatContentTests.test_github_render_does_not_use_news_weekday_visuals -v`

Expected before any coupling fix: PASS. If it fails, restrict `choose_news_visual` and news manifest fields to `content_type == "daily-news"`.

- [ ] **Step 3: 运行两类 fixture 端到端测试**

Run: `python -m unittest wechat-content.tests.test_skill.WechatContentTests.test_both_column_templates wechat-content.tests.test_skill.WechatContentTests.test_github_uses_project_template -v`

Expected: 2 tests, OK.

- [ ] **Step 4: 提交隔离保护**

```powershell
git add wechat-content/tests/test_skill.py wechat-content/scripts/run.py
git commit -m "test: protect column-specific visual rendering"
```

### Task 6: 更新 Skill 工作流和中文说明

**Files:**
- Modify: `wechat-content/SKILL.md`
- Modify: `wechat-content/references/image2-workflow.md`
- Modify: `wechat-content/references/daily-news.md`
- Modify: `wechat-content/README.md`

- [ ] **Step 1: 写文档结构失败测试**

```python
def test_chinese_docs_explain_live_and_weekday_fallback(self):
    combined="\n".join((SKILL/path).read_text(encoding="utf-8") for path in ("SKILL.md","README.md","references/image2-workflow.md"))
    for text in ("七天七色","--image-input-dir","live_image2","weekday_fallback","默认兜底"):
        self.assertIn(text,combined)
```

- [ ] **Step 2: 运行测试并确认文档尚未包含新接口而失败**

Run: `python -m unittest wechat-content.tests.test_skill.WechatContentTests.test_chinese_docs_explain_live_and_weekday_fallback -v`

Expected: FAIL on `--image-input-dir`.

- [ ] **Step 3: 更新代理工作流**

`SKILL.md` 明确：读取内容包后组装无字 Image 2 提示词；保存为 `cover.png` 与 `overview.png`；检查后调用：

```powershell
python scripts/run.py all `
  --input outputs/daily-news/2026-07-21/content-package.json `
  --output-root outputs `
  --image-input-dir work/daily-news-visuals/2026-07-21
```

没有 Image 2 时省略参数，脚本自动使用星期素材；不得把固定底图报告成动态生成。

- [ ] **Step 4: 更新 README 与参考规范**

README 用中文说明七天七色、默认兜底、新闻与 GitHub 独立模板、图片输入目录和 manifest 检查方法。`image2-workflow.md` 写出两个无字提示词模板和逐项视觉检查清单。`daily-news.md` 固化连续阅读排版。

- [ ] **Step 5: 运行文档测试与 Skill 校验**

Run: `python -m unittest wechat-content.tests.test_skill.WechatContentTests.test_chinese_docs_explain_live_and_weekday_fallback -v`

Run: `python E:/codex-config/skills/.system/skill-creator/scripts/quick_validate.py wechat-content`

Expected: test OK and `Skill is valid!`.

- [ ] **Step 6: 提交文档**

```powershell
git add wechat-content/SKILL.md wechat-content/README.md wechat-content/references wechat-content/tests/test_skill.py
git commit -m "docs: explain dynamic news visual workflow"
```

### Task 7: 完整验证、真实预览与本机安装

**Files:**
- Modify: `wechat-content/assets/previews/daily-news-cover.png`
- Modify: `wechat-content/assets/previews/daily-news-article.png` if the README references it

- [ ] **Step 1: 运行全部仓库测试**

```powershell
$py='C:\Users\11046\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
& $py -m unittest discover -s tests -v
& $py -m unittest discover -s daily-news-research/tests -v
& $py -m unittest discover -s github-hot-research/tests -v
& $py -m unittest discover -s wechat-content/tests -v
& $py -m unittest discover -s daily-news-wechat/tests -v
& $py -m unittest discover -s github-hot-wechat/tests -v
```

Expected: all tests OK, zero failures.

- [ ] **Step 2: 用真实 2026-07-21 内容包生成预览**

Run:

```powershell
& $py wechat-content/scripts/run.py all `
  --input E:/mm/test-skill/news/outputs/daily-news/2026-07-21/content-package.json `
  --output-root $env:TEMP/wechat-seven-day-check
```

Expected: `OK`; manifest 为对应星期主题；图片尺寸正确且单张小于 2 MB。

- [ ] **Step 3: 视觉检查**

使用 `view_image` 检查合并封面和新闻脉络图；打开 HTML 检查统计时段边线、30 秒速览、新闻标题、关键词、三个纯文字小标题、小清提醒、来源网址和结尾。发现错位必须回到对应任务补测试后修复。

- [ ] **Step 4: 更新 README 真实预览并复核运行结果**

将本次真实生成的合并封面和文章截图复制到 `assets/previews/`，再次运行 README 结构测试和 `quick_validate.py`。

- [ ] **Step 5: 同步本机安装的 Skill**

```powershell
Copy-Item -Path E:/mm/wxgzh/skills-repo/wechat-content/* `
  -Destination E:/codex-config/skills/wechat-content `
  -Recurse -Force
```

确认安装目录的 `SKILL.md`、`default-config.json`、星期素材和脚本均为新版本。

- [ ] **Step 6: 最终提交与推送**

```powershell
git add wechat-content
git commit -m "feat: add seven-day news visuals and restored layout"
git status --short
git -c http.proxy=http://127.0.0.1:7890 -c https.proxy=http://127.0.0.1:7890 push origin codex/modular-content-pipeline
```

Expected: working tree clean and remote branch updated. Do not publish any WeChat article.
