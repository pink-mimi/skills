# Contextual News Reminder Labels Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the fixed “小清提醒” label with a deterministic label chosen from each news item's content.

**Architecture:** Add one pure selector function to `rendering.py`, then call it only from the `daily-news` article builder. Preserve `editor_note` verbatim and keep the existing `editor-note` HTML role and styling; GitHub rendering remains untouched.

**Tech Stack:** Python 3.10+, `unittest`, existing Markdown/HTML renderer.

---

### Task 1: Add the deterministic label selector

**Files:**
- Modify: `wechat-content/tests/test_skill.py`
- Modify: `wechat-content/scripts/rendering.py`

- [ ] **Step 1: Write the failing selector test**

Add this test to `WechatContentTests`:

```python
def test_news_reminder_label_matches_content_and_has_stable_default(self):
    from rendering import choose_news_reminder_label
    cases = [
        ({"keywords": ["传闻", "辟谣"]}, "边界说明"),
        ({"category": "society", "keywords": ["强降雨", "交通"]}, "实用提醒"),
        ({"keywords": ["后续通报", "仍在发展"]}, "接下来关注"),
        ({"category": "society", "keywords": ["教育", "医疗"]}, "与你有关"),
        ({"category": "sports", "keywords": ["比赛"]}, "值得留意"),
    ]
    for item, expected in cases:
        self.assertEqual(choose_news_reminder_label(item), expected)
```

- [ ] **Step 2: Run the test and verify RED**

Run:

```powershell
python -m unittest wechat-content.tests.test_skill.WechatContentTests.test_news_reminder_label_matches_content_and_has_stable_default
```

Expected: `ImportError` because `choose_news_reminder_label` does not exist.

- [ ] **Step 3: Implement the minimal selector**

Add near the top of `rendering.py`:

```python
NEWS_REMINDER_RULES = (
    ("边界说明", ("争议", "传闻", "谣言", "辟谣", "数据存疑", "信息不完整", "尚未证实")),
    ("实用提醒", ("天气", "降雨", "暴雨", "台风", "灾害", "地震", "交通", "安全", "应急", "预警")),
    ("接下来关注", ("后续", "仍在", "持续", "进展", "通报", "待落地", "尚未公布")),
    ("与你有关", ("政策", "民生", "教育", "医疗", "消费", "就业", "社保", "公共服务")),
)


def choose_news_reminder_label(item: dict) -> str:
    fields = [item.get("category", ""), item.get("title", ""), item.get("summary", ""),
              item.get("what_happened", ""), item.get("why_it_matters", ""),
              item.get("reader_action", ""), *(item.get("keywords") or [])]
    haystack = " ".join(str(value) for value in fields).lower()
    for label, terms in NEWS_REMINDER_RULES:
        if any(term.lower() in haystack for term in terms):
            return label
    return "值得留意"
```

- [ ] **Step 4: Run the selector test and verify GREEN**

Run the command from Step 2.

Expected: one passing test.

- [ ] **Step 5: Commit**

```powershell
git add wechat-content/scripts/rendering.py wechat-content/tests/test_skill.py
git commit -m "feat: select news reminder labels by context"
```

### Task 2: Use the selected label without changing the note

**Files:**
- Modify: `wechat-content/tests/test_skill.py`
- Modify: `wechat-content/scripts/rendering.py`

- [ ] **Step 1: Write the failing rendering regression test**

```python
def test_news_render_uses_contextual_reminder_and_preserves_note(self):
    with tempfile.TemporaryDirectory() as temp:
        out = self.build("daily-news-content-package.json", temp)
        article = (out / "公众号成稿.md").read_text(encoding="utf-8")
        page = (out / "微信版.html").read_text(encoding="utf-8")
        self.assertIn("与你有关：", article)
        self.assertIn("先确认自己是否属于适用人群，再安排办理。", article)
        self.assertIn('data-role="editor-note"', page)
        self.assertNotIn("小清提醒", article + page)
```

- [ ] **Step 2: Run the regression test and verify RED**

Run:

```powershell
python -m unittest wechat-content.tests.test_skill.WechatContentTests.test_news_render_uses_contextual_reminder_and_preserves_note
```

Expected: FAIL because the article still contains “小清提醒”.

- [ ] **Step 3: Replace the fixed label in `build_article`**

Immediately before appending each daily-news item, calculate:

```python
reminder_label = choose_news_reminder_label(item)
```

Change the editor-note line to:

```python
f"> **{reminder_label}：** {item.get('editor_note') or '发布前请结合原文补充准确、克制的提醒。'}"
```

- [ ] **Step 4: Run targeted and full tests**

```powershell
python -m unittest wechat-content.tests.test_skill.WechatContentTests.test_news_render_uses_contextual_reminder_and_preserves_note
python -m unittest discover -s wechat-content/tests -p "test*.py"
```

Expected: both commands pass.

- [ ] **Step 5: Commit**

```powershell
git add wechat-content/scripts/rendering.py wechat-content/tests/test_skill.py
git commit -m "fix: replace fixed news reminder heading"
```

### Task 3: Update documentation and deliver the installed Skill

**Files:**
- Modify: `wechat-content/references/daily-news.md`
- Modify: `wechat-content/README.md`

- [ ] **Step 1: Update the Chinese rules**

Replace the fixed-name rule with the exact mapping and state that the `editor_note` body is preserved. Add a short README note explaining that repeated rendering of the same package is deterministic.

- [ ] **Step 2: Verify the obsolete label is absent from runtime files**

Run:

```powershell
Select-String -Path wechat-content/scripts/*.py,wechat-content/references/*.md,wechat-content/README.md -Pattern "小清提醒" -Encoding UTF8
```

Expected: no matches.

- [ ] **Step 3: Run all repository suites and Skill validation**

Run the six existing `unittest discover` suites and `quick_validate.py` with `PYTHONUTF8=1`.

Expected: all tests pass and validator prints `Skill is valid!`.

- [ ] **Step 4: Regenerate the real preview**

```powershell
python wechat-content/scripts/run.py all --input E:\mm\test-skill\news\outputs\daily-news\2026-07-21\content-package.json --output-root E:\mm\wxgzh\work\news-visual-preview-2026-07-21 --theme auto
```

Check that the HTML contains contextual titles, preserves source links, and contains no “小清提醒”.

- [ ] **Step 5: Sync the installed Skill without deleting files**

Copy the updated `SKILL.md`, `README.md`, `assets`, `references`, `scripts`, and `tests` into `E:\codex-config\skills\wechat-content`, then run its tests.

- [ ] **Step 6: Commit and push the existing feature branch**

```powershell
git add wechat-content/README.md wechat-content/references/daily-news.md
git commit -m "docs: explain contextual news reminders"
git push origin codex/modular-content-pipeline
```
