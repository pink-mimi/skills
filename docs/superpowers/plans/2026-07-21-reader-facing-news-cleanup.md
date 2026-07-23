# Reader-Facing News Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ensure daily-news copy output contains only reader-facing language, with dynamic notices, reliable reminder labels, deduplicated follow-up points, clear sources, and safe handling of incomplete packages.

**Architecture:** Add small deterministic helpers in `rendering.py` for reminder inputs, dynamic notices, and follow-up filtering. Keep quality status in `run.py`, but let `build_html` disable copying outside the article when status is `needs_review`; `build_article` must never emit internal placeholders. All behavior remains scoped to `daily-news`.

**Tech Stack:** Python 3.10+, standard library, Pillow, `unittest`, existing Markdown-to-inline-HTML renderer.

---

### Task 1: Make reader-facing decisions deterministic

**Files:**
- Modify: `wechat-content/scripts/rendering.py`
- Modify: `wechat-content/tests/test_skill.py`

- [ ] **Step 1: Write failing tests for reminder inputs and dynamic notices**

Add tests that assert:

```python
def test_reminder_label_ignores_action_and_editor_note_keywords(self):
    from rendering import choose_news_reminder_label
    item = {
        "category": "international",
        "title": "联合声明发布",
        "keywords": ["合作"],
        "summary": "各方公布合作方向。",
        "reader_action": "关注后续安全通报。",
        "editor_note": "这不代表规则立即改变。",
    }
    self.assertEqual(choose_news_reminder_label(item), "值得留意")

def test_dynamic_news_notice_matches_selected_topics(self):
    from rendering import build_news_notice
    items = [
        {"category": "society", "title": "强降雨预警", "keywords": ["天气", "灾害"]},
        {"category": "finance", "title": "市场数据公布", "keywords": ["市场"]},
        {"category": "politics", "title": "政策发布", "keywords": ["政策"]},
    ]
    notice = build_news_notice(items)
    self.assertIn("权威预警", notice)
    self.assertIn("统计口径", notice)
    self.assertIn("正式文件", notice)
    self.assertNotIn("人工审核", notice)

def test_dynamic_news_notice_has_neutral_fallback(self):
    from rendering import build_news_notice
    self.assertEqual(
        build_news_notice([{"category": "sports", "title": "比赛结束", "keywords": ["比赛"]}]),
        "本文依据公开资料整理，相关信息请以原始来源最新内容为准。",
    )
```

- [ ] **Step 2: Run the three tests and verify RED**

Expected: the action-keyword test fails and `build_news_notice` is missing.

- [ ] **Step 3: Narrow reminder inputs and add `build_news_notice`**

Change `choose_news_reminder_label` to join only `category`, `title`, `summary`, and `keywords`. Add ordered topic rules and return one combined paragraph, with the exact neutral fallback from the design.

- [ ] **Step 4: Run targeted tests and all `wechat-content` tests**

Expected: targeted tests and the full suite pass.

- [ ] **Step 5: Commit**

```powershell
git add wechat-content/scripts/rendering.py wechat-content/tests/test_skill.py
git commit -m "feat: add reader-facing news decisions"
```

### Task 2: Clean article text, follow-up points, and sources

**Files:**
- Modify: `wechat-content/scripts/rendering.py`
- Modify: `wechat-content/tests/test_skill.py`

- [ ] **Step 1: Write failing article regression tests**

Generate the daily fixture and assert:

```python
self.assertNotIn("内容包核验", article)
self.assertNotIn("人工审核包", article)
self.assertNotIn("尚未发布", article)
self.assertIn("## 参考来源", article)
self.assertNotIn("## 信息来源与动态说明", article)
self.assertRegex(article, r"\[官方来源：.+\]\(https://example.com/news\)\n\s+原文地址：https://example.com/news")
```

Create an incomplete package and assert the Markdown contains none of:

```python
("待人工补充", "内容包未提供", "发布前请结合原文补充")
```

Create duplicate follow-up data and assert exact/highly overlapping news-title repeats are removed; if every point is removed, `## 今天值得关注` is absent.

- [ ] **Step 2: Run tests and verify RED**

Expected: fixed internal text, old source heading, placeholders, and duplicate follow-up behavior cause failures.

- [ ] **Step 3: Implement article cleanup**

- Emit only `统计时段：{window_text}。`.
- Build each explanatory subsection only when its value exists; do not insert internal fallback strings.
- Build the editor-note block only when `editor_note` exists.
- Add a normalization helper that removes punctuation/whitespace and filters exact, containment, or strongly overlapping follow-up/title pairs deterministically.
- Omit the follow-up heading when no points survive.
- Rename the source heading to `参考来源` and output a linked source line followed by an indented visible `原文地址：URL` line.
- Append `build_news_notice(items)` without audit language.

- [ ] **Step 4: Run targeted tests and full suite**

Expected: all pass and GitHub template tests remain green.

- [ ] **Step 5: Commit**

```powershell
git add wechat-content/scripts/rendering.py wechat-content/tests/test_skill.py
git commit -m "fix: keep internal language out of news copy"
```

### Task 3: Disable copying for incomplete packages

**Files:**
- Modify: `wechat-content/scripts/rendering.py`
- Modify: `wechat-content/tests/test_skill.py`

- [ ] **Step 1: Write a failing incomplete-package HTML test**

Assert a `needs_review` render has:

```python
self.assertIn('id="copy-wechat"', page)
self.assertIn("disabled", copy_button_tag)
self.assertIn('data-role="review-notice"', page)
self.assertLess(page.index('data-role="review-notice"'), page.index('id="wechat-content"'))
```

Also assert a complete package button is not disabled and the review notice is absent.

- [ ] **Step 2: Run the tests and verify RED**

Expected: the existing button remains enabled for incomplete packages.

- [ ] **Step 3: Render safe button and outside notice**

Build the toolbar button attributes from `payload["status"]`. For `needs_review`, add `disabled`, muted styles, and an outside `data-role="review-notice"` explaining that required fields must be completed before copying. Keep the article container unchanged and do not put the notice inside it.

- [ ] **Step 4: Run targeted and full tests**

Expected: complete/incomplete copy behavior and all existing tests pass.

- [ ] **Step 5: Commit**

```powershell
git add wechat-content/scripts/rendering.py wechat-content/tests/test_skill.py
git commit -m "fix: disable copy for incomplete news packages"
```

### Task 4: Document, verify, preview, install, and push

**Files:**
- Modify: `wechat-content/README.md`
- Modify: `wechat-content/references/daily-news.md`
- Modify: `wechat-content/SKILL.md`

- [ ] **Step 1: Update Chinese documentation**

Document reader/audit separation, dynamic notices, reminder input fields, follow-up filtering, source layout, and disabled copying for `needs_review`. State that GitHub uses its own rules.

- [ ] **Step 2: Scan reader-facing runtime files**

Search `wechat-content/scripts/*.py`, README, and references for internal phrases. Runtime fallback/error-report code may contain internal phrases only if it is guaranteed outside `#wechat-content`; the generated complete and incomplete article Markdown must contain none.

- [ ] **Step 3: Run validation**

Run all six repository test suites, `quick_validate.py`, and installed-Skill tests. Expected: every command passes.

- [ ] **Step 4: Regenerate real preview**

Generate from `E:\mm\test-skill\news\outputs\daily-news\2026-07-21\content-package.json`; inspect the Markdown/HTML for dynamic notices, reminder labels, source formatting, copy boundaries, and absence of internal phrases.

- [ ] **Step 5: Sync installed Skill without deleting files**

Copy updated Skill files into `E:\codex-config\skills\wechat-content` and compare hashes of key runtime/docs files.

- [ ] **Step 6: Commit and push**

```powershell
git add wechat-content/SKILL.md wechat-content/README.md wechat-content/references/daily-news.md
git commit -m "docs: explain reader-facing news cleanup"
git push origin codex/modular-content-pipeline
```
