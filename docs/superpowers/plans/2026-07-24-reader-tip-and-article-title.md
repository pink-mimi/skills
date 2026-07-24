# 每日新闻读者提示与文章标题 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为每日新闻内容包增加独立的读者提示与文章标题字段，恢复可复制的读者提示卡，并阻止内部内容包名称成为公众号标题。

**Architecture:** `daily-news-research` 负责接收和保留 `reader_tip`、`editorial.article_title`；`wechat-content` 负责标题优先级、内部标题识别和提示卡渲染。两个新字段均向后兼容，旧内容包缺失时使用安全兜底而不是复用 `editor_note`。

**Tech Stack:** Python 3、`unittest`、JSON 内容包、内联 HTML、Markdown。

---

### Task 1: 用失败测试固定新字段边界

**Files:**
- Modify: `wechat-content/tests/test_skill.py`
- Modify: `daily-news-research/tests/test_skill.py`

- [ ] **Step 1: 增加文章标题优先级测试**

```python
def test_article_title_overrides_internal_package_title(self):
    fixture=json.loads((SKILL/"tests/fixtures/daily-news-content-package.json").read_text(encoding="utf-8"))
    fixture["editorial"]["title"]="2026-07-19 新闻内容包"
    fixture["editorial"]["article_title"]="7月19日国内要闻：公共服务新安排值得关注"
    with tempfile.TemporaryDirectory() as temp:
        source=Path(temp)/"article-title.json"
        source.write_text(json.dumps(fixture,ensure_ascii=False),encoding="utf-8")
        out=self.build(source,temp)
        article=(out/"公众号成稿.md").read_text(encoding="utf-8")
        titles=(out/"备选标题.txt").read_text(encoding="utf-8")
        self.assertTrue(article.startswith("# 7月19日国内要闻：公共服务新安排值得关注"))
        self.assertTrue(titles.startswith("7月19日国内要闻：公共服务新安排值得关注"))
        self.assertNotIn("新闻内容包",article)
```

- [ ] **Step 2: 增加内部标题兜底测试**

```python
def test_internal_package_title_uses_dated_domestic_news_fallback(self):
    from rendering import build_article
    fixture=json.loads((SKILL/"tests/fixtures/daily-news-content-package.json").read_text(encoding="utf-8"))
    fixture["editorial"]["title"]="2026-07-19 新闻内容包"
    fixture["editorial"].pop("article_title",None)
    article,title,_summary=build_article(fixture)
    self.assertEqual(title,"7月19日国内要闻：1条变化值得关注")
    self.assertNotIn("新闻内容包",article)
```

- [ ] **Step 3: 增加读者提示与编辑说明隔离测试**

```python
def test_reader_tip_is_copied_while_editor_note_stays_external(self):
    fixture=json.loads((SKILL/"tests/fixtures/daily-news-content-package.json").read_text(encoding="utf-8"))
    fixture["items"][0]["reader_tip"]="选择服务前，先确认适用范围和办理时间。"
    fixture["items"][0]["editor_note"]="内部审核：发布前复核原文。"
    with tempfile.TemporaryDirectory() as temp:
        source=Path(temp)/"reader-tip.json"
        source.write_text(json.dumps(fixture,ensure_ascii=False),encoding="utf-8")
        out=self.build(source,temp)
        page=(out/"微信版.html").read_text(encoding="utf-8")
        copy=page.split('id="wechat-content"',1)[1].split("</article>",1)[0]
        before=page[:page.index('id="wechat-content"')]
        self.assertIn('data-role="reader-tip"',copy)
        self.assertIn("选择服务前，先确认适用范围和办理时间。",copy)
        self.assertNotIn("内部审核：发布前复核原文。",copy)
        self.assertIn("内部审核：发布前复核原文。",before)
```

- [ ] **Step 4: 增加研究层字段保留测试**

在研究 Skill 的编辑输入夹具中加入：

```python
"reader_tip":"办理前再核对一次官方说明。"
```

并断言：

```python
self.assertEqual(package["items"][0]["reader_tip"],"办理前再核对一次官方说明。")
```

- [ ] **Step 5: 运行定向测试确认红灯**

Run:

```powershell
python -m unittest `
  wechat-content.tests.test_skill.WechatContentTests.test_article_title_overrides_internal_package_title `
  wechat-content.tests.test_skill.WechatContentTests.test_internal_package_title_uses_dated_domestic_news_fallback `
  wechat-content.tests.test_skill.WechatContentTests.test_reader_tip_is_copied_while_editor_note_stays_external -v
```

Expected: 标题仍采用 `editorial.title`、正文缺少 `reader-tip`，测试失败。

### Task 2: 实现文章标题和读者提示渲染

**Files:**
- Modify: `wechat-content/scripts/rendering.py`
- Modify: `wechat-content/scripts/run.py`
- Modify: `wechat-content/tests/fixtures/daily-news-content-package.json`
- Test: `wechat-content/tests/test_skill.py`

- [ ] **Step 1: 增加内部标题识别与解析函数**

```python
def is_internal_package_title(value: str) -> bool:
    title=str(value or "").strip()
    return (
        not title
        or any(token in title for token in ("内容包","新闻包","审核包","工作台"))
        or bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}\s*新闻",title))
    )


def resolve_article_title(editorial: dict, date_label: str, item_count: int) -> str:
    explicit=str(editorial.get("article_title") or "").strip()
    if explicit:
        return explicit
    legacy=str(editorial.get("title") or "").strip()
    if not is_internal_package_title(legacy):
        return legacy
    return f"{date_label}国内要闻：{item_count}条变化值得关注"
```

- [ ] **Step 2: 在 `build_article()` 中使用文章标题**

```python
title=resolve_article_title(editorial,date_label,len(items))
```

- [ ] **Step 3: 渲染可选的 `reader_tip`**

在每条新闻的三个正文段落之后追加：

```python
reader_tip=item.get("reader_tip")
if isinstance(reader_tip,str) and reader_tip.strip():
    lines += ["", "<!-- role:reader-tip -->", f"> **读者提示：** {reader_tip.strip()}"]
```

在 HTML 引用块分支中加入：

```python
elif pending_role == "reader-tip":
    blocks.append(
        f'<blockquote data-role="reader-tip" style="margin:18px 0;padding:14px 16px;'
        f'background:{bg};border:1px solid {primary}26;border-left:4px solid {accent};'
        f'border-radius:10px;box-shadow:0 4px 12px {primary}0D;color:{ink};'
        f'font-size:15px;line-height:1.8">{content}</blockquote>'
    )
```

- [ ] **Step 4: 更新模板版本和夹具**

将 `TEMPLATE_VERSION` 更新为 `2.3.0`。测试夹具把原来面向读者的 `editor_note` 拆为：

```json
"reader_tip": "先确认自己是否属于适用人群，再安排办理。",
"editor_note": "内部审核：发布前复核原文。"
```

- [ ] **Step 5: 运行 Task 1 定向测试确认绿灯**

Expected: 三个排版测试通过。

### Task 3: 让研究 Skill 保留新字段

**Files:**
- Modify: `daily-news-research/scripts/run.py`
- Modify: `daily-news-research/assets/default-config.json`
- Modify: `daily-news-research/SKILL.md`
- Modify: `daily-news-research/references/content-package-v1.md`
- Modify: `daily-news-research/references/editorial-policy.md`
- Modify: `wechat-content/SKILL.md`
- Modify: `wechat-content/references/daily-news.md`
- Test: `daily-news-research/tests/test_skill.py`

- [ ] **Step 1: 扩展编辑输入白名单**

```python
allowed={
    "what_happened","why_it_matters","reader_action","reader_tip","editor_note",
    "keywords","summary","verification_status","verified_at","primary_sources",
    "background_sources","verification_notes","recheck_before_publish",
    "china_relevance","china_relevance_reason","impact_level",
}
```

- [ ] **Step 2: 保持 `reader_tip` 为可选字段**

不把 `reader_tip` 加入 `required_editorial_fields`，避免旧内容包降级。更新文档说明它是可选读者字段，`editor_note` 是内部必填审核字段。

- [ ] **Step 3: 允许 `editorial.article_title`**

编辑输入合并逻辑允许 `editorial.article_title`，内容包规范记录 `title` 与 `article_title` 的不同用途。

- [ ] **Step 4: 运行两个 Skill 的完整测试**

Run:

```powershell
python -m unittest discover -s daily-news-research/tests -v
python -m unittest discover -s wechat-content/tests -v
```

Expected: 全部测试通过。

### Task 4: 更新本期内容、重生成并提交 GitHub

**Files:**
- Modify: `E:/mm/test-skill/news/outputs/daily-news/2026-07-24/content-package.json`
- Generate: `E:/mm/test-skill/news/outputs/wechat/daily-news/2026-07-24/微信版.html`
- Generate: `E:/mm/test-skill/news/outputs/wechat/daily-news/2026-07-24/render-manifest.json`

- [ ] **Step 1: 写入本期文章标题**

```json
"article_title": "7月23日国内要闻：基础教育新部署，科研与公共安全动态受关注"
```

- [ ] **Step 2: 为本期条目增加读者提示**

每条 `reader_tip` 只能依据已有 `reader_action` 和事实边界压缩，不得包含“发布前”“核验”“补官方原文”等运营话术。

- [ ] **Step 3: 重生成审核包**

```powershell
python E:/mm/wxgzh/skills-repo/wechat-content/scripts/run.py all `
  --input E:/mm/test-skill/news/outputs/daily-news/2026-07-24/content-package.json `
  --output-root E:/mm/test-skill/news/outputs --theme auto
```

Expected: `OK_WITH_REVIEW_REQUIRED`。

- [ ] **Step 4: 验证实际页面**

确认：

- 标题为指定标题。
- `reader-tip` 位于 `#wechat-content` 内。
- `editor_note` 只位于外部审核区。
- 复制按钮启用，`publish_ready` 仍为 `false`。

- [ ] **Step 5: 同步本机安装 Skill**

将修改后的两个 Skill 文件同步到 `E:/codex-config/skills/` 对应目录。

- [ ] **Step 6: 提交并推送**

```powershell
git add docs/superpowers/plans/2026-07-24-reader-tip-and-article-title.md daily-news-research wechat-content
git commit -m "feat: add reader tips and article titles"
git push origin main
```

- [ ] **Step 7: 最终确认**

```powershell
git status -sb
git rev-parse HEAD
git rev-parse origin/main
```

Expected: `main...origin/main` 无领先或落后，两个 SHA 一致。
