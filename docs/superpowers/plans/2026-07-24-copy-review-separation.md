# 公众号复制与审核状态分离 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让正文完整但尚未完成核验的新闻审核包可以复制排版，同时把内部审核信息留在复制区域外，并独立记录是否可发布。

**Architecture:** `scripts/run.py` 负责计算正文完整性、有效核验状态、复制状态和发布状态；`scripts/rendering.py` 只根据该状态渲染按钮、外部审核区和读者正文。`#wechat-content` 不包含任何 `editor_note`，清单同时暴露 `copy_allowed` 与 `publish_ready`。

**Tech Stack:** Python 3、`unittest`、内联 HTML、JSON 清单、Pillow 图片回归测试。

---

### Task 1: 用回归测试固定复制与发布状态

**Files:**
- Modify: `wechat-content/tests/test_skill.py:211-291`
- Modify: `wechat-content/tests/test_skill.py:404-412`

- [ ] **Step 1: 将未核验复制用例改为期望按钮可用**

把 `test_complete_unverified_news_still_disables_copy` 改为：

```python
def test_complete_unverified_news_allows_copy_but_is_not_publish_ready(self):
    fixture=json.loads((SKILL/"tests/fixtures/daily-news-content-package.json").read_text(encoding="utf-8"))
    fixture["status"]="needs_review"
    fixture["items"][0]["verification_status"]="unverified"
    fixture["items"][0]["editor_note"]="内部审核：发布前补齐官方原文。"
    with tempfile.TemporaryDirectory() as temp:
        source=Path(temp)/"unverified.json"
        source.write_text(json.dumps(fixture,ensure_ascii=False),encoding="utf-8")
        out=self.build(source,temp)
        page=(out/"微信版.html").read_text(encoding="utf-8")
        manifest=json.loads((out/"render-manifest.json").read_text(encoding="utf-8"))
        button=page.split('<button id="copy-wechat"',1)[1].split("</button>",1)[0]
        article=page.split('id="wechat-content"',1)[1].split("</article>",1)[0]
        self.assertNotIn("disabled",button)
        self.assertIn("复制正文（发布前需核验）",button)
        self.assertIn("内部审核：发布前补齐官方原文。",page[:page.index('id="wechat-content"')])
        self.assertNotIn("内部审核：发布前补齐官方原文。",article)
        self.assertTrue(manifest["copy_allowed"])
        self.assertFalse(manifest["publish_ready"])
        self.assertEqual(manifest["review_counts"]["unverified"],1)
```

- [ ] **Step 2: 增加全部核验完成时的发布就绪测试**

```python
def test_verified_news_is_copyable_and_publish_ready(self):
    with tempfile.TemporaryDirectory() as temp:
        out=self.build("daily-news-content-package.json",temp)
        page=(out/"微信版.html").read_text(encoding="utf-8")
        manifest=json.loads((out/"render-manifest.json").read_text(encoding="utf-8"))
        button=page.split('<button id="copy-wechat"',1)[1].split("</button>",1)[0]
        self.assertIn("复制正文，可发布",button)
        self.assertTrue(manifest["copy_allowed"])
        self.assertTrue(manifest["publish_ready"])
```

- [ ] **Step 3: 将编辑说明测试改为外部审核区测试**

把 `test_news_render_uses_contextual_reminder_and_preserves_note` 改为：

```python
def test_news_editor_note_is_only_in_external_review_panel(self):
    with tempfile.TemporaryDirectory() as temp:
        out=self.build("daily-news-content-package.json",temp)
        article=(out/"公众号成稿.md").read_text(encoding="utf-8")
        page=(out/"微信版.html").read_text(encoding="utf-8")
        copy_start=page.index('id="wechat-content"')
        self.assertNotIn("先确认自己是否属于适用人群，再安排办理。",article)
        self.assertIn('data-role="editor-review-panel"',page[:copy_start])
        self.assertIn("先确认自己是否属于适用人群，再安排办理。",page[:copy_start])
        self.assertNotIn('data-role="editor-note"',page[copy_start:])
```

- [ ] **Step 4: 运行定向测试并确认红灯**

Run:

```powershell
python -m unittest wechat-content.tests.test_skill.WechatContentTests.test_complete_unverified_news_allows_copy_but_is_not_publish_ready wechat-content.tests.test_skill.WechatContentTests.test_verified_news_is_copyable_and_publish_ready wechat-content.tests.test_skill.WechatContentTests.test_news_editor_note_is_only_in_external_review_panel -v
```

Expected: 三个测试因按钮仍禁用、缺少 `publish_ready` 或编辑说明仍在正文中而失败。

- [ ] **Step 5: 提交测试**

```powershell
git add wechat-content/tests/test_skill.py
git commit -m "test: define copy and review separation"
```

### Task 2: 分离正文完整性、复制状态和发布状态

**Files:**
- Modify: `wechat-content/scripts/run.py:13`
- Modify: `wechat-content/scripts/run.py:68-100`
- Modify: `wechat-content/scripts/run.py:163-174`
- Test: `wechat-content/tests/test_skill.py`

- [ ] **Step 1: 将读者正文必填字段与内部字段分开**

```python
NEWS_REQUIRED_FIELDS = ("what_happened", "why_it_matters", "reader_action", "keywords")
```

- [ ] **Step 2: 让 `copy_eligibility()` 返回独立审核状态**

保留现有嵌套 `partial` 兼容逻辑，将每日新闻结果统一为：

```python
statuses=[effective_status(item) for item in payload.get("items",[])]
review_counts={name:statuses.count(name) for name in ("verified","partial","unverified")}
if incomplete:
    return {
        "allowed":False,
        "reason":f"{len(incomplete)} 条新闻缺少读者正文必填字段",
        "publish_ready":False,
        "review_counts":review_counts,
    }
publish_ready=bool(statuses) and review_counts["partial"]==0 and review_counts["unverified"]==0
reason="ready" if publish_ready else "review_required"
return {
    "allowed":bool(statuses),
    "reason":reason,
    "publish_ready":publish_ready,
    "review_counts":review_counts,
}
```

非新闻模板继续保持原有复制规则，并返回同形字段。

- [ ] **Step 3: 扩展清单并调整命令行状态**

在清单中加入：

```python
"publish_ready":copy_state["publish_ready"],
"review_counts":copy_state["review_counts"],
```

输出状态调整为：

```python
if not copy_state["allowed"]:
    print("STRUCTURE_OK_CONTENT_NEEDS_REVIEW")
elif copy_state["publish_ready"]:
    print("OK")
else:
    print("OK_WITH_REVIEW_REQUIRED")
```

- [ ] **Step 4: 运行 Task 1 定向测试**

Run: Task 1 Step 4 的命令。

Expected: 清单相关断言通过；HTML 边界相关断言仍失败。

- [ ] **Step 5: 提交状态逻辑**

```powershell
git add wechat-content/scripts/run.py
git commit -m "fix: separate copy and publish readiness"
```

### Task 3: 将编辑说明移出复制正文

**Files:**
- Modify: `wechat-content/scripts/rendering.py:349-459`
- Test: `wechat-content/tests/test_skill.py`

- [ ] **Step 1: 从 Markdown 正文构建中移除 `editor_note`**

删除 `build_article()` 中以下追加逻辑：

```python
if item.get("editor_note"):
    lines += ["", "<!-- role:editor-note -->", f"> **{reminder_label}：** {item['editor_note']}"]
```

同时删除只服务于该块的 `reminder_label` 局部变量；保留面向读者的 `reader_action`。

- [ ] **Step 2: 新增外部编辑审核区构建函数**

```python
def build_editor_review_panel(payload: dict, copy_state: dict) -> str:
    rows=[]
    for item in payload.get("items") or []:
        status=str(item.get("verification_status") or "unverified")
        note=str(item.get("editor_note") or "").strip()
        if status=="verified" and not note:
            continue
        rows.append(
            f'<section style="margin:10px 0;padding:12px;border-top:1px solid #E2E8F0">'
            f'<strong>{html.escape(item.get("title") or "未命名新闻")}</strong>'
            f'<p style="margin:6px 0 0">状态：{html.escape(status)}</p>'
            f'{f"""<p style="margin:6px 0 0">{html.escape(note)}</p>""" if note else ""}'
            f'</section>'
        )
    if not rows:
        return ""
    counts=copy_state["review_counts"]
    return (
        '<aside data-role="editor-review-panel" style="max-width:740px;margin:18px auto;'
        'padding:16px;background:#FFF7D6;color:#5F4B12;border-radius:10px">'
        f'<strong>发布审核：{counts["unverified"]} 条未核验，{counts["partial"]} 条部分核验</strong>'
        '<p style="margin:8px 0">以下内容仅供运营者审核，不会被复制到公众号正文。</p>'
        f'{"".join(rows)}</aside>'
    )
```

- [ ] **Step 3: 根据发布状态渲染按钮和警告**

在 `build_html()` 中：

```python
if ready_to_copy:
    button_attributes = 'style="..." onclick="copyWechat()"'
    button_label = "复制正文，可发布" if copy_state["publish_ready"] else "复制正文（发布前需核验）"
else:
    button_attributes = 'disabled aria-disabled="true" style="..."'
    button_label = "正文待补全，暂不可复制"
review_panel=build_editor_review_panel(payload,copy_state)
```

将 `review_panel` 放在工具栏之后、`<main>` 之前，确保位于 `#wechat-content` 外。

- [ ] **Step 4: 运行 Task 1 定向测试并确认绿灯**

Run: Task 1 Step 4 的命令。

Expected: `Ran 3 tests ... OK`。

- [ ] **Step 5: 提交渲染修复**

```powershell
git add wechat-content/scripts/rendering.py wechat-content/tests/test_skill.py
git commit -m "fix: keep editor notes outside copied article"
```

### Task 4: 更新规则文档并运行全量验证

**Files:**
- Modify: `wechat-content/SKILL.md`
- Modify: `wechat-content/references/daily-news.md`
- Modify: `wechat-content/references/visual-and-copy.md`
- Test: `wechat-content/tests/test_skill.py`

- [ ] **Step 1: 更新复制规则**

将“真正 `unverified` 时禁用复制”改为：

```markdown
正文读者字段完整时允许复制；存在 `partial` 或 `unverified` 时，必须在复制区外提示发布前核验，并明确不得把成功复制视为发布就绪。只有缺少读者正文必填字段时才禁用复制。`editor_note`、核验状态和审核要求只供运营者查看，不得进入读者正文。
```

- [ ] **Step 2: 更新版本**

将 `TEMPLATE_VERSION` 从 `2.1.2` 更新为 `2.2.0`，并同步测试中的版本断言。

- [ ] **Step 3: 运行全量测试**

Run:

```powershell
python -m unittest discover -s wechat-content/tests -v
```

Expected: 全部测试通过，无失败或错误。

- [ ] **Step 4: 运行静态差异检查**

Run:

```powershell
git diff --check
git status --short
```

Expected: `git diff --check` 无输出；状态只包含本计划范围内文件。

- [ ] **Step 5: 提交文档和版本**

```powershell
git add wechat-content/SKILL.md wechat-content/references/daily-news.md wechat-content/references/visual-and-copy.md wechat-content/scripts/run.py wechat-content/tests/test_skill.py
git commit -m "docs: clarify copy and publish workflow"
```

### Task 5: 重生成并验证 2026-07-24 审核包

**Files:**
- Read: `E:/mm/test-skill/news/outputs/daily-news/2026-07-24/content-package.json`
- Generate: `E:/mm/test-skill/news/outputs/wechat/daily-news/2026-07-24/微信版.html`
- Generate: `E:/mm/test-skill/news/outputs/wechat/daily-news/2026-07-24/render-manifest.json`
- Generate: `E:/mm/test-skill/news/outputs/wechat/daily-news/2026-07-24/运行报告.md`

- [ ] **Step 1: 使用修改后的 Skill 重建审核包**

Run:

```powershell
python E:/mm/wxgzh/skills-repo/wechat-content/scripts/run.py all --input E:/mm/test-skill/news/outputs/daily-news/2026-07-24/content-package.json --output-root E:/mm/test-skill/news/outputs --theme auto
```

Expected: 输出 `OK_WITH_REVIEW_REQUIRED`。

- [ ] **Step 2: 检查实际 HTML 边界**

验证：

- 按钮不含 `disabled`。
- 按钮文字为“复制正文（发布前需核验）”。
- `editor_note` 位于 `data-role="editor-review-panel"` 内。
- `#wechat-content` 到 `</article>` 之间不含 `editor_note` 或 `data-role="editor-note"`。

- [ ] **Step 3: 检查实际清单**

Expected:

```json
{
  "copy_allowed": true,
  "publish_ready": false,
  "review_counts": {
    "verified": 1,
    "partial": 0,
    "unverified": 5
  }
}
```

- [ ] **Step 4: 最终回归验证**

Run:

```powershell
python -m unittest discover -s wechat-content/tests -v
git diff --check
git status --short
```

Expected: 测试全部通过、差异检查无输出，并列出全部修改文件。
